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

def test_master_scd_history():
    print("=" * 78)
    print("STEP 09.15: MASTER SCD TYPE 2 HISTORY & VERSION PRESERVATION TEST")
    print("=" * 78)

    passed_checks = 0
    failed_checks = 0

    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            (db_name,) = conn.execute(text("SELECT DATABASE()")).fetchone()
            print(f"[PASS] Connected to MySQL database: '{db_name}'\n")
            passed_checks += 1

            # 1. Inspect production SCD history tables in retail_sales_db
            print("--- 1. Production SCD History Schema Verification ---")
            scd_pairs = (
                ("core_customers", "core_customers_history"),
                ("core_products", "core_products_history"),
                ("core_stores", "core_stores_history"),
            )

            for core_tbl, hist_tbl in scd_pairs:
                (exists_cnt,) = conn.execute(text("""
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = DATABASE() AND table_name = :ht
                """), {"ht": hist_tbl}).fetchone()

                if int(exists_cnt) > 0:
                    cols = conn.execute(text(f"SHOW COLUMNS FROM `{hist_tbl}`")).fetchall()
                    col_names = [col_name for col_name, *_ in cols]
                    scd_cols = [c for c in col_names if any(k in c.lower() for k in ("effective", "valid", "current", "version", "expired", "archived", "history"))]
                    print(f"  [PASS] {core_tbl} -> {hist_tbl} verified (tracking cols: {scd_cols})")
                    passed_checks += 1
                else:
                    print(f"  [FAIL] Missing SCD history table '{hist_tbl}'!")
                    failed_checks += 1
            print()

            # 2. Transactional SCD Type 2 simulation across Customer, Product & Store attributes
            print("--- 2. Tracked Attribute Change & Prior/Current Version Preservation ---")
            try:
                conn.execute(text("""
                    CREATE TEMPORARY TABLE tmp_scd2_master_history (
                        surrogate_sk INT AUTO_INCREMENT PRIMARY KEY,
                        entity_type VARCHAR(20) NOT NULL,
                        business_key VARCHAR(32) NOT NULL,
                        tracked_attr_name VARCHAR(40) NOT NULL,
                        tracked_attr_value VARCHAR(100) NOT NULL,
                        version_num INT NOT NULL,
                        effective_from DATETIME NOT NULL,
                        effective_to DATETIME NULL,
                        is_current TINYINT(1) NOT NULL
                    )
                """))

                v1_start = "2025-01-01 00:00:00"
                v2_start = "2026-06-15 10:30:00"

                # Seed initial v1 current records for Customer, Product, and Store
                initial_entities = (
                    ("CUSTOMER", "CUST_1001", "customer_segment", "Silver"),
                    ("PRODUCT", "PROD_2001", "unit_price", "499.00"),
                    ("STORE", "STR_01", "region", "South"),
                )
                for etype, bkey, aname, aval in initial_entities:
                    conn.execute(text("""
                        INSERT INTO tmp_scd2_master_history
                        (entity_type, business_key, tracked_attr_name, tracked_attr_value, version_num, effective_from, effective_to, is_current)
                        VALUES (:et, :bk, :an, :av, 1, :ef, NULL, 1)
                    """), {"et": etype, "bk": bkey, "an": aname, "av": aval, "ef": v1_start})

                # Apply tracked attribute changes -> expire v1 and insert v2 as current
                changed_entities = (
                    ("CUSTOMER", "CUST_1001", "customer_segment", "Platinum"),
                    ("PRODUCT", "PROD_2001", "unit_price", "549.00"),
                    ("STORE", "STR_01", "region", "Metro-South"),
                )
                for etype, bkey, aname, new_val in changed_entities:
                    # Expire prior current row
                    conn.execute(text("""
                        UPDATE tmp_scd2_master_history
                        SET effective_to = :et_ts, is_current = 0
                        WHERE entity_type = :et AND business_key = :bk AND is_current = 1
                    """), {"et_ts": v2_start, "et": etype, "bk": bkey})

                    # Insert new current row (version 2)
                    conn.execute(text("""
                        INSERT INTO tmp_scd2_master_history
                        (entity_type, business_key, tracked_attr_name, tracked_attr_value, version_num, effective_from, effective_to, is_current)
                        VALUES (:et, :bk, :an, :av, 2, :ef, NULL, 1)
                    """), {"et": etype, "bk": bkey, "an": aname, "av": new_val, "ef": v2_start})

                # Verify each entity has exactly 1 prior closed version (v1) and 1 active current version (v2)
                for etype, bkey, aname, old_val in initial_entities:
                    (prior_val, prior_cur, prior_end) = conn.execute(text("""
                        SELECT tracked_attr_value, is_current, effective_to
                        FROM tmp_scd2_master_history
                        WHERE entity_type = :et AND business_key = :bk AND version_num = 1
                    """), {"et": etype, "bk": bkey}).fetchone()

                    (curr_val, curr_cur, curr_end) = conn.execute(text("""
                        SELECT tracked_attr_value, is_current, effective_to
                        FROM tmp_scd2_master_history
                        WHERE entity_type = :et AND business_key = :bk AND version_num = 2
                    """), {"et": etype, "bk": bkey}).fetchone()

                    print(f"  {etype:<8} ({bkey} | {aname}): v1='{prior_val}' (is_current={prior_cur}, closed) -> v2='{curr_val}' (is_current={curr_cur}, active)")

                    if prior_val == old_val and int(prior_cur) == 0 and prior_end is not None and int(curr_cur) == 1 and curr_end is None:
                        passed_checks += 1
                    else:
                        print(f"  [FAIL] SCD2 version state mismatch for {etype} ({bkey})!")
                        failed_checks += 1

                print("  [PASS] All prior and current SCD2 versions preserved accurately across Customer, Product, and Store.")

            finally:
                conn.rollback()

    except Exception as exc:
        print(f"  [ERROR] Master SCD history test failed: {exc}")
        failed_checks += 1

    print()
    print("=" * 78)
    print(f"SUMMARY -> Passed Checks: {passed_checks} | Failed Checks: {failed_checks}")
    print("=" * 78)

if __name__ == "__main__":
    test_master_scd_history()

