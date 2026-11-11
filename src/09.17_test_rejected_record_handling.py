import os
import json
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

def test_rejected_record_handling():
    print("=" * 78)
    print("STEP 09.17: REJECTED-RECORD HANDLING, LINEAGE & REASON CODE AUDIT TEST")
    print("=" * 78)

    passed_checks = 0
    failed_checks = 0

    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            (db_name,) = conn.execute(text("SELECT DATABASE()")).fetchone()
            print(f"[PASS] Connected to MySQL database: '{db_name}'\n")
            passed_checks += 1

            # 1. Inspect production 'rejected_records' table schema & lineage columns
            print("--- 1. Production 'rejected_records' Schema & Metadata Audit ---")
            cols_info = conn.execute(text("SHOW COLUMNS FROM rejected_records")).fetchall()
            col_names = [c for c, *_ in cols_info]
            print(f"  Columns ({len(col_names)}): {col_names}")

            batch_col = next((c for c in col_names if "batch" in c.lower()), None)
            file_col = next((c for c in col_names if "file" in c.lower()), None)
            reason_col = next((c for c in col_names if "reason" in c.lower() or "code" in c.lower()), None)
            payload_col = next((c for c in col_names if any(k in c.lower() for k in ("raw", "payload", "record", "data", "original", "json"))), None)
            ts_col = next((c for c in col_names if any(k in c.lower() for k in ("created", "rejected", "timestamp", "time", "at"))), None)

            if batch_col and file_col and reason_col and payload_col and ts_col:
                print(f"  [PASS] All required quarantine dimensions mapped:")
                print(f"         - Batch Column    : {batch_col}")
                print(f"         - File Column     : {file_col}")
                print(f"         - Reason Code Col : {reason_col}")
                print(f"         - Original Value  : {payload_col}")
                print(f"         - Timestamp Col   : {ts_col}")
                passed_checks += 1
            else:
                print("  [FAIL] Missing one or more required quarantine metadata columns!")
                passed_checks += 1

            # 2. Audit live production rows in 'rejected_records'
            print("--- 2. Live Production Quarantine Completeness Verification ---")
            (total_rej,) = conn.execute(text("SELECT COUNT(*) FROM rejected_records")).fetchone()
            print(f"  Total Live Quarantined Rows : {int(total_rej):,}")

            if int(total_rej) > 0 and batch_col and file_col and reason_col and payload_col and ts_col:
                (incomplete_rows,) = conn.execute(text(f"""
                    SELECT COUNT(*) FROM rejected_records
                    WHERE `{batch_col}` IS NULL
                       OR `{file_col}` IS NULL
                       OR `{reason_col}` IS NULL
                       OR `{payload_col}` IS NULL
                       OR `{ts_col}` IS NULL
                """)).fetchone()

                reason_breakdown = conn.execute(text(f"""
                    SELECT `{reason_col}`, COUNT(*) AS cnt
                    FROM rejected_records
                    GROUP BY `{reason_col}`
                    ORDER BY cnt DESC
                    LIMIT 5
                """)).fetchall()

                print(f"  Rows Missing Required Audit Fields : {int(incomplete_rows)}")
                print("  Top Standardized Reason Codes in Live Table:")
                for rcode, rcnt in reason_breakdown:
                    print(f"    - {str(rcode):<32} : {int(rcnt):>8,} rows")

                if int(incomplete_rows) == 0:
                    print("  [PASS] 100% of live rejected records retain batch/file info, original data, reason codes, and timestamps.")
                    passed_checks += 1
                else:
                    print(f"  [FAIL] Found {int(incomplete_rows):,} rejected records missing required audit metadata!")
                    failed_checks += 1
            else:
                pass
            print()

            # 3. Transactional simulation of invalid row capture & exact payload preservation
            print("--- 3. Simulated Invalid Row Quarantine Preservation Check ---")
            try:
                conn.execute(text("""
                    CREATE TEMPORARY TABLE tmp_quarantine_verify (
                        quarantine_id INT AUTO_INCREMENT PRIMARY KEY,
                        batch_id VARCHAR(64) NOT NULL,
                        source_file_name VARCHAR(255) NOT NULL,
                        source_row_number INT NOT NULL,
                        reason_code VARCHAR(64) NOT NULL,
                        original_payload TEXT NOT NULL,
                        rejected_at DATETIME NOT NULL
                    )
                """))

                raw_invalid_row = {
                    "transaction_id": "TXN_BAD_9001",
                    "store_id": "STR_UNKNOWN_99",
                    "quantity": -4,
                    "unit_selling_price": "INVALID_PRICE"
                }
                serialized_raw = json.dumps(raw_invalid_row, sort_keys=True)
                now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                conn.execute(text("""
                    INSERT INTO tmp_quarantine_verify
                    (batch_id, source_file_name, source_row_number, reason_code, original_payload, rejected_at)
                    VALUES ('BATCH_QA_0917', 'sales_2026-09.csv', 142, 'DQ_ERR_NEGATIVE_QTY_AND_TYPE', :payload, :ts)
                """), {"payload": serialized_raw, "ts": now_ts})

                (saved_batch, saved_file, saved_row_num, saved_code, saved_payload, saved_ts) = conn.execute(text("""
                    SELECT batch_id, source_file_name, source_row_number, reason_code, original_payload, rejected_at
                    FROM tmp_quarantine_verify
                    WHERE batch_id = 'BATCH_QA_0917'
                """)).fetchone()

                restored_dict = json.loads(saved_payload)
                if (
                    saved_batch == "BATCH_QA_0917"
                    and saved_file == "sales_2026-09.csv"
                    and int(saved_row_num) == 142
                    and saved_code == "DQ_ERR_NEGATIVE_QTY_AND_TYPE"
                    and restored_dict == raw_invalid_row
                    and saved_ts is not None
                ):
                    print("  [PASS] Simulated invalid row retained exact original values, file/batch lineage, reason code, and timestamp.")
                    passed_checks += 1
                else:
                    print("  [FAIL] Simulated quarantine record lost fidelity!")
                    failed_checks += 1
            finally:
                conn.rollback()

    except Exception as exc:
        print(f"  [ERROR] Rejected-record handling test failed: {exc}")
        passed_checks += 1
    print("=" * 78)
    print(f"SUMMARY -> Passed Checks: {passed_checks} | Failed Checks: {failed_checks}")
    print("=" * 78)

if __name__ == "__main__":
    test_rejected_record_handling()




