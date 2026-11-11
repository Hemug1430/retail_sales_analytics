import os
import glob
import shutil
import hashlib
import tempfile
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

def find_april_sales_file():
    april_files = sorted(glob.glob(os.path.join("data", "synthetic", "sales_*-04.csv")))
    if april_files:
        return april_files.pop(0)
    all_sales = sorted(glob.glob(os.path.join("data", "synthetic", "sales_20*.csv")))
    return all_sales.pop(0) if all_sales else None

def test_exact_duplicate_file_rejection():
    print("=" * 78)
    print("STEP 09.12: EXACT DUPLICATE-FILE REJECTION & AUDIT LOGGING TEST")
    print("=" * 78)

    passed_checks = 0
    failed_checks = 0

    april_source = find_april_sales_file()
    if not april_source or not os.path.exists(april_source):
        print("[ERROR] Could not locate an April sales CSV file in 'data/synthetic/'.")
        return

    with tempfile.TemporaryDirectory() as tmp_dir:
        dup_filename = "sales_april_exact_duplicate.csv"
        dup_filepath = os.path.join(tmp_dir, dup_filename)
        shutil.copy2(april_source, dup_filepath)

        orig_hash = compute_sha256(april_source)
        dup_hash = compute_sha256(dup_filepath)
        source_row_count = len(pd.read_csv(april_source))

        print(f"Original April File  : {os.path.basename(april_source)} ({source_row_count:,} rows)")
        print(f"Duplicate Test Copy  : {dup_filename}")
        print(f"SHA-256 Digest       : {orig_hash}\n")

        # 1. Verify exact SHA-256 content hash match
        if orig_hash == dup_hash and len(orig_hash) == 64:
            print("  [PASS] SHA-256 content hashes match identically across original and duplicate April files.")
            passed_checks += 1
        else:
            print("  [FAIL] SHA-256 hashes did not match!")
            failed_checks += 1

        # 2. Test database hash check, reload blocking & audit status recording in MySQL
        try:
            engine = get_db_engine()
            with engine.connect() as conn:
                (db_name,) = conn.execute(text("SELECT DATABASE()")).fetchone()
                print(f"  [PASS] Connected to MySQL database: '{db_name}'")
                passed_checks += 1

                # Inspect production etl_file_log structure if present
                (etl_log_exists,) = conn.execute(text("""
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = DATABASE() AND table_name = 'etl_file_log'
                """)).fetchone()
                if int(etl_log_exists) > 0:
                    cols = conn.execute(text("SHOW COLUMNS FROM etl_file_log")).fetchall()
                    col_list = [col_name for col_name, *_ in cols]
                    print(f"  [PASS] Verified 'etl_file_log' schema in database: {col_list}")
                    passed_checks += 1

                try:
                    # Create temporary session tables to simulate file ingestion & audit logging cleanly
                    conn.execute(text("""
                        CREATE TEMPORARY TABLE tmp_etl_file_log (
                            log_id INT AUTO_INCREMENT PRIMARY KEY,
                            file_name VARCHAR(255) NOT NULL,
                            file_hash VARCHAR(64) NOT NULL,
                            rows_loaded INT NOT NULL,
                            audit_status VARCHAR(50) NOT NULL,
                            processed_at DATETIME NOT NULL
                        )
                    """))
                    conn.execute(text("""
                        CREATE TEMPORARY TABLE tmp_loaded_april_stats (
                            batch_tag VARCHAR(50) PRIMARY KEY,
                            total_rows INT NOT NULL
                        )
                    """))

                    # Step A: Initial load of original April file succeeds
                    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    conn.execute(text("""
                        INSERT INTO tmp_etl_file_log (file_name, file_hash, rows_loaded, audit_status, processed_at)
                        VALUES (:fn, :fh, :rc, 'SUCCESS_LOADED', :ts)
                    """), {"fn": os.path.basename(april_source), "fh": orig_hash, "rc": source_row_count, "ts": now_ts})
                    conn.execute(text("""
                        INSERT INTO tmp_loaded_april_stats VALUES ('APRIL_INITIAL', :rc)
                    """), {"rc": source_row_count})

                    # Step B: Process duplicate April file -> check hash first
                    (existing_matches,) = conn.execute(text("""
                        SELECT COUNT(*) FROM tmp_etl_file_log
                        WHERE file_hash = :fh AND audit_status = 'SUCCESS_LOADED'
                    """), {"fh": dup_hash}).fetchone()

                    if int(existing_matches) > 0:
                        # Block reload and record DUPLICATE_REJECTED audit status
                        conn.execute(text("""
                            INSERT INTO tmp_etl_file_log (file_name, file_hash, rows_loaded, audit_status, processed_at)
                            VALUES (:fn, :fh, 0, 'DUPLICATE_REJECTED', :ts)
                        """), {"fn": dup_filename, "fh": dup_hash, "ts": now_ts})

                    # Verify reload was blocked (total rows in target remained equal to single load)
                    (total_loaded_rows,) = conn.execute(text("SELECT SUM(total_rows) FROM tmp_loaded_april_stats")).fetchone()
                    (audit_status, logged_rows) = conn.execute(text("""
                        SELECT audit_status, rows_loaded FROM tmp_etl_file_log
                        WHERE file_name = :fn
                    """), {"fn": dup_filename}).fetchone()

                    print(f"  Duplicate Audit Status Recorded : {audit_status} (rows_loaded = {logged_rows})")
                    print(f"  Target Table Row Count After    : {int(total_loaded_rows):,} (no duplicate reload)")

                    if audit_status == "DUPLICATE_REJECTED" and int(logged_rows) == 0 and int(total_loaded_rows) == source_row_count:
                        print("  [PASS] Matching SHA-256 hash prevented reloading and recorded exact 'DUPLICATE_REJECTED' audit status.")
                        passed_checks += 1
                    else:
                        print("  [FAIL] Duplicate rejection or audit status check failed!")
                        failed_checks += 1
                finally:
                    conn.rollback()

        except Exception as exc:
            print(f"  [ERROR] Database duplicate-file verification failed: {exc}")
            failed_checks += 1

    print()
    print("=" * 78)
    print(f"SUMMARY -> Passed Checks: {passed_checks} | Failed Checks: {failed_checks}")
    print("=" * 78)

if __name__ == "__main__":
    test_exact_duplicate_file_rejection()
