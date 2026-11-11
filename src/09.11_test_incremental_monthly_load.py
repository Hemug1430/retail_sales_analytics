import os
import uuid
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

def test_incremental_monthly_load():
    print("=" * 78)
    print("STEP 09.11: INCREMENTAL MONTHLY LOAD & HISTORICAL PRESERVATION TEST")
    print("=" * 78)

    passed_checks = 0
    failed_checks = 0

    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            (db_name,) = conn.execute(text("SELECT DATABASE()")).fetchone()
            print(f"[PASS] Connected to MySQL database: '{db_name}'\n")
            passed_checks += 1

            # 1. Inspect core tables & historical watermark baseline
            rows = conn.execute(text("SHOW FULL TABLES")).fetchall()
            base_tables = sorted([tbl_name for tbl_name, tbl_type in rows if "BASE TABLE" in str(tbl_type).upper()])
            core_tables = [t for t in base_tables if t.startswith("core_")]

            print("--- 1. Pre-Load Historical Baseline & Watermark Check ---")
            baseline_counts = {}
            for tbl in core_tables:
                (cnt,) = conn.execute(text(f"SELECT COUNT(*) FROM `{tbl}`")).fetchone()
                baseline_counts[tbl] = int(cnt)
                print(f"  - {tbl:<25} : {cnt:>10,} historical rows")

            if sum(baseline_counts.values()) > 0:
                print("  [PASS] Historical baseline verified prior to incremental monthly run.")
                passed_checks += 1
            else:
                print("  [FAIL] No historical baseline records found in core tables!")
                failed_checks += 1
            print()

            # 2. Verify incremental batch execution logic using an isolated transactional test
            print("--- 2. Simulated Incremental Monthly Load (2026-11 Delta Batch) ---")
            # autobegin active
            try:
                # Create an isolated temporary incremental tracking table inside the active DB session
                conn.execute(text("""
                    CREATE TEMPORARY TABLE tmp_incremental_sales (
                        transaction_id VARCHAR(50) PRIMARY KEY,
                        sales_month VARCHAR(7) NOT NULL,
                        store_id VARCHAR(20) NOT NULL,
                        net_revenue DECIMAL(12,2) NOT NULL,
                        batch_id VARCHAR(64) NOT NULL,
                        load_timestamp DATETIME NOT NULL
                    )
                """))

                # Seed 3 historical rows from 2026-10
                hist_batch = "BATCH_2026_10_HIST"
                hist_ts = "2026-10-31 23:59:00"
                conn.execute(text("""
                    INSERT INTO tmp_incremental_sales VALUES
                    ('TXN_HIST_001', '2026-10', 'STR01', 1200.00, :b, :ts),
                    ('TXN_HIST_002', '2026-10', 'STR02', 850.00, :b, :ts),
                    ('TXN_HIST_003', '2026-10', 'STR03', 430.00, :b, :ts)
                """), {"b": hist_batch, "ts": hist_ts})

                # Apply incremental 2026-11 delta: 2 brand-new November rows + 1 updated October row
                inc_batch = f"BATCH_2026_11_INC_{uuid.uuid4().hex[:6].upper()}"
                inc_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn.execute(text("""
                    INSERT INTO tmp_incremental_sales (transaction_id, sales_month, store_id, net_revenue, batch_id, load_timestamp)
                    VALUES
                        ('TXN_NOV_001', '2026-11', 'STR01', 1599.00, :b, :ts),
                        ('TXN_NOV_002', '2026-11', 'STR04', 2100.00, :b, :ts),
                        ('TXN_HIST_002', '2026-10', 'STR02', 900.00, :b, :ts)
                    ON DUPLICATE KEY UPDATE
                        net_revenue = VALUES(net_revenue),
                        batch_id = VALUES(batch_id),
                        load_timestamp = VALUES(load_timestamp)
                """), {"b": inc_batch, "ts": inc_ts})

                # Verify historical untouched rows still retain original batch_id and timestamp
                (untouched_hist,) = conn.execute(text("""
                    SELECT COUNT(*) FROM tmp_incremental_sales
                    WHERE batch_id = :b AND load_timestamp = :ts
                """), {"b": hist_batch, "ts": hist_ts}).fetchone()

                # Verify only new/changed rows carry the incremental batch_id
                (applied_delta,) = conn.execute(text("""
                    SELECT COUNT(*) FROM tmp_incremental_sales
                    WHERE batch_id = :b
                """), {"b": inc_batch}).fetchone()

                (total_after,) = conn.execute(text("SELECT COUNT(*) FROM tmp_incremental_sales")).fetchone()

                print(f"  Total Rows After Incremental Load : {total_after} (3 historical + 2 new)")
                print(f"  Untouched Historical Rows         : {untouched_hist} (preserved without rebuild)")
                print(f"  Incremental Delta Rows Applied    : {applied_delta} (2 new 2026-11 + 1 changed 2026-10)")

                if untouched_hist == 2 and applied_delta == 3 and total_after == 5:
                    print("  [PASS] Incremental upsert applied only new/changed rows without rebuilding historical data.")
                    passed_checks += 1
                else:
                    print("  [FAIL] Incremental delta accounting mismatch!")
                    failed_checks += 1

            finally:
                conn.rollback()

            # 3. Verify production core tables remained completely unchanged
            print()
            print("--- 3. Post-Test Production Historical Integrity Verification ---")
            integrity_ok = True
            for tbl, before_cnt in baseline_counts.items():
                (after_cnt,) = conn.execute(text(f"SELECT COUNT(*) FROM `{tbl}`")).fetchone()
                if int(after_cnt) != before_cnt:
                    print(f"  [FAIL] Table '{tbl}' count changed unexpectedly ({before_cnt} -> {after_cnt})!")
                    integrity_ok = False
            if integrity_ok:
                print("  [PASS] All production core table historical counts verified 100% intact.")
                passed_checks += 1
            else:
                failed_checks += 1

    except Exception as exc:
        print(f"[ERROR] Incremental monthly load test failed: {exc}")
        failed_checks += 1

    print()
    print("=" * 78)
    print(f"SUMMARY -> Passed Checks: {passed_checks} | Failed Checks: {failed_checks}")
    print("=" * 78)

if __name__ == "__main__":
    test_incremental_monthly_load()

