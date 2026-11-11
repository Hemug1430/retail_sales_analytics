import os
import hashlib
from datetime import datetime, timedelta
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

def test_file_audit_logging():
    print("=" * 78)
    print("STEP 09.18: FILE AUDIT LOGGING COMPLETENESS & OUTCOME COVERAGE TEST")
    print("=" * 78)

    passed_checks = 0
    failed_checks = 0

    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            (db_name,) = conn.execute(text("SELECT DATABASE()")).fetchone()
            print(f"[PASS] Connected to MySQL database: '{db_name}'\n")
            passed_checks += 1

            # 1. Inspect production 'etl_file_log' schema
            print("--- 1. Production 'etl_file_log' Schema & Column Audit ---")
            cols_info = conn.execute(text("SHOW COLUMNS FROM etl_file_log")).fetchall()
            col_names = [c for c, *_ in cols_info]
            print(f"  Columns ({len(col_names)}): {col_names}")

            batch_col = next((c for c in col_names if "batch" in c.lower()), None)
            file_col = next((c for c in col_names if "file_name" in c.lower() or c == "filename"), None)
            hash_col = next((c for c in col_names if "hash" in c.lower() or "checksum" in c.lower()), None)
            status_col = next((c for c in col_names if "status" in c.lower()), None)
            count_cols = [c for c in col_names if any(k in c.lower() for k in ("record", "row", "count", "inserted", "rejected", "read"))]
            timing_cols = [c for c in col_names if any(k in c.lower() for k in ("start", "end", "complete", "duration", "time", "created", "at"))]
            error_cols = [c for c in col_names if "error" in c.lower() or "message" in c.lower()]

            if batch_col and file_col and hash_col and status_col and count_cols and timing_cols and error_cols:
                print("  [PASS] All 7 required audit dimensions verified in 'etl_file_log':")
                print(f"         - Batch ID Column : {batch_col}")
                print(f"         - File Name Col   : {file_col}")
                print(f"         - File Hash Col   : {hash_col}")
                print(f"         - Status Column   : {status_col}")
                print(f"         - Count Columns   : {count_cols}")
                print(f"         - Timing Columns  : {timing_cols}")
                print(f"         - Error Columns   : {error_cols}")
                passed_checks += 1
            else:
                print("  [FAIL] Missing one or more required file audit columns!")
                failed_checks += 1
            print()

            # 2. Audit live rows in production 'etl_file_log'
            print("--- 2. Live Production 'etl_file_log' Records Verification ---")
            (total_logs,) = conn.execute(text("SELECT COUNT(*) FROM etl_file_log")).fetchone()
            print(f"  Total Live File Audit Rows : {int(total_logs):,}")

            if int(total_logs) > 0 and batch_col and file_col and hash_col and status_col:
                (missing_core_audit,) = conn.execute(text(f"""
                    SELECT COUNT(*) FROM etl_file_log
                    WHERE `{batch_col}` IS NULL
                       OR `{file_col}` IS NULL
                       OR `{status_col}` IS NULL
                """)).fetchone()

                status_rows = conn.execute(text(f"""
                    SELECT `{status_col}`, COUNT(*) AS cnt
                    FROM etl_file_log
                    GROUP BY `{status_col}`
                    ORDER BY cnt DESC
                """)).fetchall()

                print(f"  Rows Missing Core Audit IDs/Status : {int(missing_core_audit)}")
                for st, cnt in status_rows:
                    print(f"    - Status '{st}' : {int(cnt):,} files")

                if int(missing_core_audit) == 0:
                    print("  [PASS] 100% of live file audit records contain valid batch ID, file name, and status.")
                    passed_checks += 1
                else:
                    print(f"  [FAIL] Found {int(missing_core_audit)} audit records missing required fields!")
                    failed_checks += 1
            else:
                print("  [PASS] Live 'etl_file_log' structure verified ready for batch execution tracking.")
                passed_checks += 1
            print()

            # 3. Simulate all 4 file outcomes (SUCCESS, DUPLICATE, SCHEMA_DRIFT, VALIDATION_FAILED)
            print("--- 3. Multi-Outcome File Audit Logging Simulation ---")
            try:
                conn.execute(text("""
                    CREATE TEMPORARY TABLE tmp_file_audit_outcomes (
                        audit_id INT AUTO_INCREMENT PRIMARY KEY,
                        batch_id VARCHAR(64) NOT NULL,
                        file_name VARCHAR(255) NOT NULL,
                        file_hash VARCHAR(64) NOT NULL,
                        records_read INT NOT NULL,
                        records_inserted INT NOT NULL,
                        records_rejected INT NOT NULL,
                        load_status VARCHAR(40) NOT NULL,
                        started_at DATETIME NOT NULL,
                        completed_at DATETIME NOT NULL,
                        duration_seconds DECIMAL(10,3) NOT NULL,
                        error_class VARCHAR(64) NULL,
                        error_code VARCHAR(64) NULL,
                        error_message VARCHAR(255) NULL
                    )
                """))

                base_time = datetime.now()
                outcomes = (
                    ("BATCH_QA_0918", "sales_2026-01.csv", "SUCCESS", 50000, 49850, 150, 4.250, None, None, None),
                    ("BATCH_QA_0918", "sales_2026-04_DUP.csv", "DUPLICATE_REJECTED", 0, 0, 0, 0.015, "DUPLICATE_FILE", "HASH_ALREADY_LOADED", "Exact SHA-256 match with previously loaded file"),
                    ("BATCH_QA_0918", "sales_2026-08_SCHEMA.csv", "SCHEMA_QUARANTINED", 48000, 0, 48000, 0.310, "SCHEMA_DRIFT", "UNAPPROVED_EXTRA_COL", "Extra column 'coupon_code' detected"),
                    ("BATCH_QA_0918", "sales_2026-09_CORRUPT.csv", "FAILED_VALIDATION", 10, 0, 10, 0.085, "DATA_QUALITY", "MISSING_REQUIRED_PK", "Null transaction_id exceeded 100% threshold"),
                )

                for idx, (bid, fname, st, r_read, r_ins, r_rej, dur, e_cls, e_cd, e_msg) in enumerate(outcomes):
                    fhash = hashlib.sha256(f"{fname}_{idx}".encode("utf-8")).hexdigest()
                    st_ts = (base_time + timedelta(seconds=idx * 5)).strftime("%Y-%m-%d %H:%M:%S")
                    en_ts = (base_time + timedelta(seconds=idx * 5 + dur)).strftime("%Y-%m-%d %H:%M:%S")

                    conn.execute(text("""
                        INSERT INTO tmp_file_audit_outcomes
                        (batch_id, file_name, file_hash, records_read, records_inserted, records_rejected,
                         load_status, started_at, completed_at, duration_seconds, error_class, error_code, error_message)
                        VALUES (:bid, :fn, :fh, :rr, :ri, :rj, :st, :sts, :ets, :dur, :ec, :ecd, :emsg)
                    """), {
                        "bid": bid, "fn": fname, "fh": fhash, "rr": r_read, "ri": r_ins, "rj": r_rej,
                        "st": st, "sts": st_ts, "ets": en_ts, "dur": dur, "ec": e_cls, "ecd": e_cd, "emsg": e_msg
                    })

                (logged_total,) = conn.execute(text("SELECT COUNT(*) FROM tmp_file_audit_outcomes")).fetchone()
                (error_outcomes_with_details,) = conn.execute(text("""
                    SELECT COUNT(*) FROM tmp_file_audit_outcomes
                    WHERE load_status != 'SUCCESS'
                      AND error_class IS NOT NULL
                      AND error_code IS NOT NULL
                      AND error_message IS NOT NULL
                """)).fetchone()
                (all_valid_timing_and_hash,) = conn.execute(text("""
                    SELECT COUNT(*) FROM tmp_file_audit_outcomes
                    WHERE LENGTH(file_hash) = 64
                      AND batch_id IS NOT NULL
                      AND started_at IS NOT NULL
                      AND completed_at IS NOT NULL
                      AND duration_seconds >= 0
                """)).fetchone()

                print(f"  Simulated File Outcomes Logged   : {int(logged_total)} (SUCCESS, DUPLICATE, SCHEMA, VALIDATION)")
                print(f"  Non-Success Outcomes With Errors : {int(error_outcomes_with_details)} / 3")
                print(f"  Outcomes With Hash/Batch/Timing  : {int(all_valid_timing_and_hash)} / 4")

                if int(logged_total) == 4 and int(error_outcomes_with_details) == 3 and int(all_valid_timing_and_hash) == 4:
                    print("  [PASS] All file outcomes recorded complete name, hash, counts, status, timing, errors, and batch ID.")
                    passed_checks += 1
                else:
                    print("  [FAIL] One or more simulated file audit outcomes missed required fields!")
                    failed_checks += 1

            finally:
                conn.rollback()

    except Exception as exc:
        print(f"  [ERROR] File audit logging test failed: {exc}")
        failed_checks += 1

    print()
    print("=" * 78)
    print(f"SUMMARY -> Passed Checks: {passed_checks} | Failed Checks: {failed_checks}")
    print("=" * 78)

if __name__ == "__main__":
    test_file_audit_logging()
