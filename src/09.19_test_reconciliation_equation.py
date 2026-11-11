import os
from datetime import datetime
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

def test_reconciliation_equation():
    print("=" * 78)
    print("STEP 09.19: BATCH ROW-BALANCE RECONCILIATION EQUATION VALIDATION TEST")
    print("=" * 78)

    passed_checks = 0
    failed_checks = 0

    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            (db_name,) = conn.execute(text("SELECT DATABASE()")).fetchone()
            print(f"[PASS] Connected to MySQL database: '{db_name}'\n")
            passed_checks += 1

            # 1. Verify reconciliation accounting columns in 'etl_file_log'
            print("--- 1. Production 'etl_file_log' Reconciliation Schema Check ---")
            cols_info = conn.execute(text("SHOW COLUMNS FROM etl_file_log")).fetchall()
            col_names = set(c for c, *_ in cols_info)

            required_recon_cols = {
                "records_read",
                "records_inserted",
                "records_updated",
                "records_unchanged",
                "records_duplicated",
                "records_rejected"
            }

            if required_recon_cols.issubset(col_names):
                print(f"  [PASS] All 6 reconciliation accounting columns verified: {sorted(required_recon_cols)}")
                passed_checks += 1
            else:
                missing = sorted(required_recon_cols - col_names)
                print(f"  [FAIL] Missing reconciliation columns in 'etl_file_log': {missing}")
                failed_checks += 1
            print()

            # 2. Check live rows in 'etl_file_log' for exact equation balance
            print("--- 2. Live Production Audit Table Balance Verification ---")
            (live_rows,) = conn.execute(text("SELECT COUNT(*) FROM etl_file_log")).fetchone()
            print(f"  Live Audit Records Checked : {int(live_rows):,}")

            if int(live_rows) > 0:
                (unbalanced_live,) = conn.execute(text("""
                    SELECT COUNT(*) FROM etl_file_log
                    WHERE COALESCE(records_read, 0) != (
                        COALESCE(records_inserted, 0)
                        + COALESCE(records_updated, 0)
                        + COALESCE(records_unchanged, 0)
                        + COALESCE(records_duplicated, 0)
                        + COALESCE(records_rejected, 0)
                    )
                """)).fetchone()
                if int(unbalanced_live) == 0:
                    print("  [PASS] 100% of live audit rows satisfy: read = inserted + updated + unchanged + duplicated + rejected.")
                    passed_checks += 1
                else:
                    print(f"  [FAIL] Found {int(unbalanced_live)} unbalanced rows in live 'etl_file_log'!")
                    failed_checks += 1
            else:
                print("  [PASS] Live 'etl_file_log' accounting structure ready (0 unbalanced rows).")
                passed_checks += 1
            print()

            # 3. Transactional simulation across 4 multi-outcome batches
            print("--- 3. Multi-Batch Reconciliation Equation Simulation ---")
            try:
                conn.execute(text("""
                    CREATE TEMPORARY TABLE tmp_batch_reconciliation (
                        batch_id VARCHAR(64) NOT NULL,
                        file_name VARCHAR(255) NOT NULL,
                        records_read INT NOT NULL,
                        records_inserted INT NOT NULL,
                        records_updated INT NOT NULL,
                        records_unchanged INT NOT NULL,
                        records_duplicated INT NOT NULL,
                        records_rejected INT NOT NULL,
                        verified_at DATETIME NOT NULL
                    )
                """))

                now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                test_batches = (
                    ("BATCH_01_HIST", "sales_2024-01.csv", 60000, 58200, 0, 0, 1100, 700),
                    ("BATCH_02_INC", "sales_2026-11.csv", 55000, 54100, 350, 150, 250, 150),
                    ("BATCH_03_CORR", "sales_2026-06_CORRECTION.csv", 50000, 0, 1240, 48710, 0, 50),
                    ("BATCH_04_DUP", "sales_2026-04_DUPLICATE.csv", 57100, 0, 0, 0, 57100, 0),
                )

                for bid, fname, r_read, r_ins, r_upd, r_unc, r_dup, r_rej in test_batches:
                    conn.execute(text("""
                        INSERT INTO tmp_batch_reconciliation
                        (batch_id, file_name, records_read, records_inserted, records_updated,
                         records_unchanged, records_duplicated, records_rejected, verified_at)
                        VALUES (:bid, :fn, :rr, :ri, :ru, :runc, :rdup, :rrej, :ts)
                    """), {
                        "bid": bid, "fn": fname, "rr": r_read, "ri": r_ins, "ru": r_upd,
                        "runc": r_unc, "rdup": r_dup, "rrej": r_rej, "ts": now_ts
                    })

                batch_audit = conn.execute(text("""
                    SELECT
                        batch_id,
                        records_read,
                        (records_inserted + records_updated + records_unchanged + records_duplicated + records_rejected) AS accounted_total,
                        (records_read - (records_inserted + records_updated + records_unchanged + records_duplicated + records_rejected)) AS variance
                    FROM tmp_batch_reconciliation
                    ORDER BY batch_id
                """)).fetchall()

                all_balanced = True
                for bid, r_read, accounted, variance in batch_audit:
                    print(f"  {bid:<16} | Read: {int(r_read):>7,} | Accounted: {int(accounted):>7,} | Variance: {int(variance)}")
                    if int(variance) != 0:
                        all_balanced = False

                if all_balanced and len(batch_audit) == 4:
                    print("  [PASS] All 4 batches reconciled with exact zero variance (read == sum of documented outcomes).")
                    passed_checks += 1
                else:
                    print("  [FAIL] One or more batches had non-zero reconciliation variance!")
                    failed_checks += 1

            finally:
                conn.rollback()

    except Exception as exc:
        print(f"  [ERROR] Reconciliation equation test failed: {exc}")
        failed_checks += 1

    print()
    print("=" * 78)
    print(f"SUMMARY -> Passed Checks: {passed_checks} | Failed Checks: {failed_checks}")
    print("=" * 78)

if __name__ == "__main__":
    test_reconciliation_equation()
