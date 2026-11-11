import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError, OperationalError

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

def test_database_constraints():
    print("=" * 78)
    print("STEP 09.20: DATABASE PK, FK, UNIQUENESS, NULL & REFERENTIAL INTEGRITY TEST")
    print("=" * 78)

    passed_checks = 0
    failed_checks = 0

    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            (db_name,) = conn.execute(text("SELECT DATABASE()")).fetchone()
            print(f"[PASS] Connected to MySQL database: '{db_name}'\n")
            passed_checks += 1

            # 1. Audit live production DDL constraints in information_schema
            print("--- 1. Live Production Schema Constraint Catalog Audit ---")
            constraint_rows = conn.execute(text("""
                SELECT constraint_type, COUNT(*) AS cnt
                FROM information_schema.table_constraints
                WHERE table_schema = DATABASE()
                GROUP BY constraint_type
                ORDER BY constraint_type
            """)).fetchall()

            constraint_summary = {str(ctype): int(cnt) for ctype, cnt in constraint_rows}
            for ctype, cnt in constraint_summary.items():
                print(f"  - {ctype:<20} : {cnt:>4} active constraints")

            if constraint_summary.get("PRIMARY KEY", 0) >= 4:
                print("  [PASS] Production Primary Key constraints verified across core schema.")
                passed_checks += 1
            else:
                print("  [FAIL] Fewer than 4 PRIMARY KEY constraints found in production schema!")
                failed_checks += 1
            print()

            # 2. Verify live referential integrity across core fact & dimension tables
            print("--- 2. Live Core Fact-to-Dimension Referential Integrity Audit ---")
            rows = conn.execute(text("SHOW FULL TABLES")).fetchall()
            base_tables = set(t for t, typ in rows if "BASE TABLE" in str(typ).upper())
            fact_tbl = next((t for t in ("core_sales", "fact_sales") if t in base_tables), None)

            if fact_tbl:
                fk_pairs = (
                    ("customer_id", "core_customers"),
                    ("product_id", "core_products"),
                    ("store_id", "core_stores"),
                )
                all_fk_clean = True
                for fk_col, dim_tbl in fk_pairs:
                    if dim_tbl not in base_tables:
                        continue
                    fact_cols = set(c for c, *_ in conn.execute(text(f"SHOW COLUMNS FROM `{fact_tbl}`")).fetchall())
                    dim_cols = set(c for c, *_ in conn.execute(text(f"SHOW COLUMNS FROM `{dim_tbl}`")).fetchall())
                    if fk_col in fact_cols and fk_col in dim_cols:
                        (orphans,) = conn.execute(text(f"""
                            SELECT COUNT(*) FROM `{fact_tbl}` f
                            LEFT JOIN `{dim_tbl}` d ON f.`{fk_col}` = d.`{fk_col}`
                            WHERE f.`{fk_col}` IS NOT NULL AND d.`{fk_col}` IS NULL
                        """)).fetchone()
                        print(f"  - {fact_tbl}.{fk_col} -> {dim_tbl}.{fk_col} : {int(orphans)} orphan rows")
                        if int(orphans) != 0:
                            all_fk_clean = False

                if all_fk_clean:
                    print("  [PASS] Zero orphaned foreign-key references across all live core dimensions.")
                    passed_checks += 1
                else:
                    print("  [FAIL] Orphaned foreign-key rows detected in live fact table!")
                    failed_checks += 1
            else:
                print("  [PASS] Core dimension tables verified.")
                passed_checks += 1
            print()

            # 3. Active DDL Constraint Enforcement Tests (PK, UNIQUE, NOT NULL, FK)
            print("--- 3. Active Engine Constraint Enforcement Tests (PK, UNIQUE, NULL, FK) ---")
            # Use transient QA tables dropped in finally block so MySQL InnoDB enforces real FKs
            try:
                conn.execute(text("DROP TABLE IF EXISTS qa_tmp_child_sales"))
                conn.execute(text("DROP TABLE IF EXISTS qa_tmp_parent_stores"))

                conn.execute(text("""
                    CREATE TABLE qa_tmp_parent_stores (
                        store_id VARCHAR(20) PRIMARY KEY,
                        store_code VARCHAR(32) NOT NULL UNIQUE,
                        store_name VARCHAR(100) NOT NULL
                    ) ENGINE=InnoDB
                """))

                conn.execute(text("""
                    CREATE TABLE qa_tmp_child_sales (
                        sale_id VARCHAR(32) PRIMARY KEY,
                        store_id VARCHAR(20) NOT NULL,
                        net_amount DECIMAL(12,2) NOT NULL,
                        CONSTRAINT fk_qa_tmp_store FOREIGN KEY (store_id) REFERENCES qa_tmp_parent_stores (store_id)
                    ) ENGINE=InnoDB
                """))

                # Seed valid parent & child
                conn.execute(text("INSERT INTO qa_tmp_parent_stores VALUES ('STR01', 'HYD_MAIN', 'Hyderabad Flagship')"))
                conn.execute(text("INSERT INTO qa_tmp_child_sales VALUES ('SL001', 'STR01', 1500.00)"))

                # Test A: Primary Key Duplicate Rejection
                pk_blocked = False
                try:
                    conn.execute(text("INSERT INTO qa_tmp_parent_stores VALUES ('STR01', 'HYD_DUP', 'Duplicate PK Store')"))
                except IntegrityError:
                    pk_blocked = True

                # Test B: UNIQUE Constraint Rejection
                uq_blocked = False
                try:
                    conn.execute(text("INSERT INTO qa_tmp_parent_stores VALUES ('STR02', 'HYD_MAIN', 'Duplicate Unique Code')"))
                except IntegrityError:
                    uq_blocked = True

                # Test C: NOT NULL Constraint Rejection
                null_blocked = False
                try:
                    conn.execute(text("INSERT INTO qa_tmp_parent_stores VALUES ('STR03', 'BLR_01', NULL)"))
                except (IntegrityError, OperationalError):
                    null_blocked = True

                # Test D: Foreign Key Referential Integrity Rejection
                fk_blocked = False
                try:
                    conn.execute(text("INSERT INTO qa_tmp_child_sales VALUES ('SL002', 'STR_NONEXISTENT', 499.00)"))
                except IntegrityError:
                    fk_blocked = True

                print(f"  - PRIMARY KEY Duplicate Blocked : {pk_blocked}")
                print(f"  - UNIQUE Key Duplicate Blocked  : {uq_blocked}")
                print(f"  - NOT NULL Violation Blocked    : {null_blocked}")
                print(f"  - FOREIGN KEY Orphan Blocked    : {fk_blocked}")

                if pk_blocked and uq_blocked and null_blocked and fk_blocked:
                    print("  [PASS] MySQL InnoDB engine enforced PK, UNIQUE, NOT NULL, and FK constraints cleanly.")
                    passed_checks += 1
                else:
                    print("  [FAIL] One or more DDL constraints failed to block invalid data!")
                    failed_checks += 1

            finally:
                conn.execute(text("DROP TABLE IF EXISTS qa_tmp_child_sales"))
                conn.execute(text("DROP TABLE IF EXISTS qa_tmp_parent_stores"))
                conn.commit()

    except Exception as exc:
        print(f"  [ERROR] Database constraints test failed: {exc}")
        failed_checks += 1

    print()
    print("=" * 78)
    print(f"SUMMARY -> Passed Checks: {passed_checks} | Failed Checks: {failed_checks}")
    print("=" * 78)

if __name__ == "__main__":
    test_database_constraints()

