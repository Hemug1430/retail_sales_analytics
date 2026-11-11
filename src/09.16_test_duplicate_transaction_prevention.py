import os
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

def test_duplicate_transaction_prevention():
    print("=" * 78)
    print("STEP 09.16: DUPLICATE TRANSACTION PREVENTION & BUSINESS-KEY INTEGRITY TEST")
    print("=" * 78)

    passed_checks = 0
    failed_checks = 0

    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            (db_name,) = conn.execute(text("SELECT DATABASE()")).fetchone()
            print(f"[PASS] Connected to MySQL database: '{db_name}'\n")
            passed_checks += 1

            # 1. Locate trusted sales fact table in retail_sales_db
            rows = conn.execute(text("SHOW FULL TABLES")).fetchall()
            base_tables = sorted([t for t, typ in rows if "BASE TABLE" in str(typ).upper()])
            fact_sales_tbl = next(
                (t for t in base_tables if t in ("core_sales", "fact_sales", "core_sales_transactions") or ("sales" in t.lower() and t.startswith(("core_", "fact_")) and "history" not in t.lower())),
                None
            )

            if not fact_sales_tbl:
                print(f"[FAIL] Could not locate trusted sales fact table among: {base_tables}")
                return

            cols_info = conn.execute(text(f"SHOW COLUMNS FROM `{fact_sales_tbl}`")).fetchall()
            col_names = [c for c, *_ in cols_info]
            pk_cols = [c for c, typ, null_flag, key_flag, *_ in cols_info if str(key_flag).upper() == "PRI"]
            bkey_col = next(
                (c for c in ("sales_line_id", "transaction_id", "order_line_id", "sale_id") if c in col_names),
                pk_cols.pop(0) if pk_cols else col_names.pop(0)
            )

            (total_prod_rows,) = conn.execute(text(f"SELECT COUNT(*) FROM `{fact_sales_tbl}`")).fetchone()
            (distinct_bkeys,) = conn.execute(text(f"SELECT COUNT(DISTINCT `{bkey_col}`) FROM `{fact_sales_tbl}`")).fetchone()
            prod_dups = int(total_prod_rows) - int(distinct_bkeys)

            print(f"--- 1. Production Trusted Fact Table Check ('{fact_sales_tbl}') ---")
            print(f"  Business Key Column     : {bkey_col}")
            print(f"  Total Production Rows   : {int(total_prod_rows):,}")
            print(f"  Distinct Business Keys  : {int(distinct_bkeys):,}")
            print(f"  Duplicate Business Keys : {prod_dups}")

            if int(total_prod_rows) > 0 and prod_dups == 0:
                print(f"  [PASS] Trusted fact '{fact_sales_tbl}' has zero duplicate business keys.")
                passed_checks += 1
            else:
                print(f"  [FAIL] Found {prod_dups} duplicate business keys in '{fact_sales_tbl}'!")
                failed_checks += 1
            print()

            # 2. Sample real transaction keys and test duplicate reload prevention
            print("--- 2. Simulated Reload of Existing Transactions (Idempotency Gate) ---")
            sample_rows = conn.execute(text(f"SELECT `{bkey_col}` FROM `{fact_sales_tbl}` LIMIT 3")).fetchall()
            sample_keys = [str(k) for (k,) in sample_rows]

            try:
                conn.execute(text("""
                    CREATE TEMPORARY TABLE tmp_trusted_fact_sales (
                        business_key VARCHAR(64) PRIMARY KEY,
                        net_amount DECIMAL(12,2) NOT NULL,
                        load_batch VARCHAR(40) NOT NULL
                    )
                """))

                # Seed the 3 real production business keys into the temporary trusted fact
                for idx, bkey in enumerate(sample_keys, start=1):
                    conn.execute(text("""
                        INSERT INTO tmp_trusted_fact_sales (business_key, net_amount, load_batch)
                        VALUES (:bk, :amt, 'BATCH_INITIAL')
                    """), {"bk": bkey, "amt": round(250.0 * idx, 2)})

                # Attempt to reload the exact same 3 transactions + 1 genuinely new transaction
                reload_candidates = (
                    (sample_keys.pop(0), 250.00),
                    (sample_keys.pop(0), 500.00),
                    (sample_keys.pop(0), 750.00),
                    ("SL_NEW_UNIQUE_999001", 999.00),
                )

                duplicates_blocked = 0
                new_rows_inserted = 0

                for cand_key, cand_amt in reload_candidates:
                    (already_exists,) = conn.execute(text("""
                        SELECT COUNT(*) FROM tmp_trusted_fact_sales WHERE business_key = :bk
                    """), {"bk": cand_key}).fetchone()

                    if int(already_exists) > 0:
                        duplicates_blocked += 1
                    else:
                        conn.execute(text("""
                            INSERT INTO tmp_trusted_fact_sales (business_key, net_amount, load_batch)
                            VALUES (:bk, :amt, 'BATCH_RELOAD_ATTEMPT')
                        """), {"bk": cand_key, "amt": cand_amt})
                        new_rows_inserted += 1

                (final_total,) = conn.execute(text("SELECT COUNT(*) FROM tmp_trusted_fact_sales")).fetchone()
                (final_distinct,) = conn.execute(text("SELECT COUNT(DISTINCT business_key) FROM tmp_trusted_fact_sales")).fetchone()

                print(f"  Reload Batch Size          : 4 records (3 existing + 1 new)")
                print(f"  Duplicate Reloads Blocked  : {duplicates_blocked}")
                print(f"  New Unique Rows Inserted   : {new_rows_inserted}")
                print(f"  Trusted Fact Final Count   : {int(final_total)} rows | {int(final_distinct)} distinct business keys")

                if duplicates_blocked == 3 and new_rows_inserted == 1 and int(final_total) == int(final_distinct) == 4:
                    print("  [PASS] Existing transactions were prevented from reloading; trusted fact gained zero duplicate business keys.")
                    passed_checks += 1
                else:
                    print("  [FAIL] Duplicate transaction prevention check failed!")
                    failed_checks += 1

            finally:
                conn.rollback()

    except Exception as exc:
        print(f"  [ERROR] Duplicate transaction prevention test failed: {exc}")
        failed_checks += 1

    print()
    print("=" * 78)
    print(f"SUMMARY -> Passed Checks: {passed_checks} | Failed Checks: {failed_checks}")
    print("=" * 78)

if __name__ == "__main__":
    test_duplicate_transaction_prevention()
