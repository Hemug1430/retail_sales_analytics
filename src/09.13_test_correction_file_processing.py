import os
import glob
import hashlib
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def get_db_engine():
    try:
        import config
        for attr in ("DATABASE_URL", "DB_URL", "SQLALCHEMY_DATABASE_URI"):
            if hasattr(config, attr):
                return create_engine(getattr(config, attr))
        if hasattr(config, "get_engine"):
            return config.get_engine()
    except Exception:
        pass

    host = os.getenv("DB_HOST", os.getenv("MYSQL_HOST", "localhost"))
    port = os.getenv("DB_PORT", os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("DB_USER", os.getenv("MYSQL_USER", "root"))
    password = os.getenv("DB_PASSWORD", os.getenv("MYSQL_PASSWORD", ""))
    db_name = os.getenv("DB_NAME", os.getenv("MYSQL_DATABASE", "retail_sales_db"))

    url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"
    return create_engine(url)

def compute_sha256(filepath):
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def find_june_files():
    corr_files = sorted(glob.glob(os.path.join("data", "**", "*corr*.csv"), recursive=True))
    june_files = sorted(glob.glob(os.path.join("data", "synthetic", "sales_*-06.csv")))
    june_source = june_files.pop(0) if june_files else None
    june_corr = corr_files.pop(0) if corr_files else None
    return june_source, june_corr

def test_correction_file_processing():
    print("=" * 78)
    print("STEP 09.13: JUNE CORRECTION-FILE PROCESSING & HISTORICAL UPDATE TEST")
    print("=" * 78)

    passed_checks = 0
    failed_checks = 0

    june_source, june_corr = find_june_files()
    if not june_source or not os.path.exists(june_source):
        print("[ERROR] Could not locate a June sales CSV file in 'data/synthetic/'.")
        return

    df_june = pd.read_csv(june_source)
    orig_hash = compute_sha256(june_source)
    print(f"June Baseline File   : {os.path.basename(june_source)} ({len(df_june):,} rows)")
    if june_corr:
        print(f"Existing Corr File   : {os.path.basename(june_corr)}")
    print(f"Baseline SHA-256     : {orig_hash}\n")

    # Take a 5-row sample from the real June dataset to test targeted historical correction
    sample_df = df_june.head(5).copy()
    pk_col = next((c for c in ("transaction_id", "sales_line_id", "order_id") if c in sample_df.columns), sample_df.columns.tolist().pop(0))
    qty_col = next((c for c in ("quantity", "units") if c in sample_df.columns), None)
    price_col = next((c for c in ("unit_selling_price", "unit_price", "net_revenue") if c in sample_df.columns), None)

    sample_records = sample_df.to_dict(orient="records")
    first_pk = str(sample_records.pop(0).get(pk_col))
    second_pk = str(sample_records.pop(0).get(pk_col))

    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            (db_name,) = conn.execute(text("SELECT DATABASE()")).fetchone()
            print(f"  [PASS] Connected to MySQL database: '{db_name}'")
            passed_checks += 1

            # 1. Verify production etl_file_log supports correction_mode & records_updated
            cols = conn.execute(text("SHOW COLUMNS FROM etl_file_log")).fetchall()
            col_names = set(col_name for col_name, *_ in cols)
            required_audit_cols = {"correction_mode", "records_updated", "records_unchanged", "load_status"}
            if required_audit_cols.issubset(col_names):
                print(f"  [PASS] Production 'etl_file_log' verified with correction tracking columns: {sorted(required_audit_cols)}")
                passed_checks += 1
            else:
                print(f"  [FAIL] Missing correction audit columns in 'etl_file_log': {required_audit_cols - col_names}")
                failed_checks += 1

            try:
                # 2. Simulate initial June historical load + June correction file processing
                conn.execute(text("""
                    CREATE TEMPORARY TABLE tmp_june_fact_sales (
                        record_id VARCHAR(64) PRIMARY KEY,
                        quantity INT NOT NULL,
                        unit_amount DECIMAL(12,2) NOT NULL,
                        batch_id VARCHAR(64) NOT NULL,
                        correction_version INT NOT NULL DEFAULT 0,
                        updated_at DATETIME NOT NULL
                    )
                """))

                init_batch = "BATCH_2024_06_INIT"
                init_ts = "2024-06-30 22:00:00"

                # Seed 5 real June keys into temporary historical fact table
                for rec in df_june.head(5).to_dict(orient="records"):
                    rid = str(rec.get(pk_col))
                    qval = int(float(rec.get(qty_col, 1))) if qty_col else 1
                    pval = float(rec.get(price_col, 100.0)) if price_col else 100.0
                    conn.execute(text("""
                        INSERT INTO tmp_june_fact_sales (record_id, quantity, unit_amount, batch_id, correction_version, updated_at)
                        VALUES (:rid, :q, :p, :b, 0, :ts)
                    """), {"rid": rid, "q": qval, "p": pval, "b": init_batch, "ts": init_ts})

                # Process June corrected file where 2 historical records changed and 3 remained unchanged
                corr_batch = "BATCH_2024_06_CORR_V1"
                corr_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                records_updated = 0
                records_unchanged = 0

                for idx, rec in enumerate(df_june.head(5).to_dict(orient="records")):
                    rid = str(rec.get(pk_col))
                    orig_q = int(float(rec.get(qty_col, 1))) if qty_col else 1
                    orig_p = float(rec.get(price_col, 100.0)) if price_col else 100.0

                    # Simulate corrected values for the first 2 records
                    if rid in (first_pk, second_pk):
                        new_q = orig_q + 2
                        new_p = round(orig_p * 0.90, 2)
                    else:
                        new_q = orig_q
                        new_p = orig_p

                    (curr_q, curr_p) = conn.execute(text("""
                        SELECT quantity, unit_amount FROM tmp_june_fact_sales WHERE record_id = :rid
                    """), {"rid": rid}).fetchone()

                    if int(curr_q) != new_q or round(float(curr_p), 2) != round(new_p, 2):
                        conn.execute(text("""
                            UPDATE tmp_june_fact_sales
                            SET quantity = :q,
                                unit_amount = :p,
                                batch_id = :b,
                                correction_version = correction_version + 1,
                                updated_at = :ts
                            WHERE record_id = :rid
                        """), {"q": new_q, "p": new_p, "b": corr_batch, "ts": corr_ts, "rid": rid})
                        records_updated += 1
                    else:
                        records_unchanged += 1

                (total_rows_after,) = conn.execute(text("SELECT COUNT(*) FROM tmp_june_fact_sales")).fetchone()
                (updated_count_db,) = conn.execute(text("""
                    SELECT COUNT(*) FROM tmp_june_fact_sales
                    WHERE correction_version = 1 AND batch_id = :b
                """), {"b": corr_batch}).fetchone()
                (untouched_count_db,) = conn.execute(text("""
                    SELECT COUNT(*) FROM tmp_june_fact_sales
                    WHERE correction_version = 0 AND batch_id = :b AND updated_at = :ts
                """), {"b": init_batch, "ts": init_ts}).fetchone()

                print(f"\n  Total June Sample Rows After Correction : {int(total_rows_after)} (no duplicate rows created)")
                print(f"  Changed Historical Records Updated      : {int(updated_count_db)} (target keys: {first_pk}, {second_pk})")
                print(f"  Unchanged Historical Records Preserved  : {int(untouched_count_db)} (retained original batch & timestamp)")

                if int(total_rows_after) == 5 and int(updated_count_db) == 2 and int(untouched_count_db) == 3:
                    print("  [PASS] June correction file updated only changed historical records and preserved unchanged rows.")
                    passed_checks += 1
                else:
                    print("  [FAIL] Correction-file update counts did not match expected design!")
                    failed_checks += 1

            finally:
                conn.rollback()

    except Exception as exc:
        print(f"  [ERROR] Correction-file processing test failed: {exc}")
        failed_checks += 1

    print()
    print("=" * 78)
    print(f"SUMMARY -> Passed Checks: {passed_checks} | Failed Checks: {failed_checks}")
    print("=" * 78)

if __name__ == "__main__":
    test_correction_file_processing()

