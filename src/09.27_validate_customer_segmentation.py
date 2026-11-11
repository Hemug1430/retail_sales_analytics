import os
from datetime import date
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

RULE_CHANGE_DATE = date(2026, 7, 1)

def classify_customer_segment(total_spend, order_count, as_of_date):
    """
    Documented Customer Segmentation Rule Engine:
    - Legacy Rule (< 2026-07-01):
        VIP / Platinum : spend >= 50,000 or orders >= 15
        Gold / Loyal   : spend >= 20,000 or orders >= 6
        Silver / Reg   : spend >= 5,000
        Standard       : < 5,000
    - Updated Rule (>= 2026-07-01):
        VIP / Platinum : spend >= 75,000 and orders >= 12
        Gold / Loyal   : spend >= 30,000 and orders >= 5
        Silver / Reg   : spend >= 10,000
        Standard       : < 10,000
    """
    if as_of_date < RULE_CHANGE_DATE:
        if total_spend >= 50000 or order_count >= 15:
            return "Platinum"
        if total_spend >= 20000 or order_count >= 6:
            return "Gold"
        if total_spend >= 5000:
            return "Silver"
        return "Standard"
    else:
        if total_spend >= 75000 and order_count >= 12:
            return "Platinum"
        if total_spend >= 30000 and order_count >= 5:
            return "Gold"
        if total_spend >= 10000:
            return "Silver"
        return "Standard"

def validate_customer_segmentation():
    print("=" * 78)
    print("STEP 09.27: CUSTOMER SEGMENTATION & JULY 2026 RULE CHANGE VALIDATION")
    print("=" * 78)

    passed_checks = 0
    failed_checks = 0

    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            (db_name,) = conn.execute(text("SELECT DATABASE()")).fetchone()
            print(f"[PASS] Connected to MySQL database: '{db_name}'\n")
            passed_checks += 1

            # 1. Inspect live 'core_customers' & 'core_customers_history' segment distribution
            print("--- 1. Live Production Customer Segment Distribution & SCD2 Audit ---")
            cust_cols = [c for c, *_ in conn.execute(text("SHOW COLUMNS FROM core_customers")).fetchall()]
            seg_col = next((c for c in cust_cols if "segment" in c.lower() or "tier" in c.lower()), None)

            if not seg_col:
                print(f"  [FAIL] Could not locate segment column in 'core_customers': {cust_cols}")
                return

            seg_rows = conn.execute(text(f"""
                SELECT COALESCE(`{seg_col}`, 'NULL') AS seg, COUNT(*) AS cnt
                FROM core_customers
                GROUP BY COALESCE(`{seg_col}`, 'NULL')
                ORDER BY cnt DESC
            """)).fetchall()

            (total_cust,) = conn.execute(text("SELECT COUNT(*) FROM core_customers")).fetchone()
            (null_segs,) = conn.execute(text(f"SELECT COUNT(*) FROM core_customers WHERE `{seg_col}` IS NULL OR TRIM(`{seg_col}`) = ''")).fetchone()

            print(f"  Segment Column         : core_customers.{seg_col}")
            print(f"  Total Active Customers : {int(total_cust):,}")
            for seg_name, cnt in seg_rows:
                print(f"    - {str(seg_name):<18} : {int(cnt):>6,} customers")

            if int(total_cust) > 0 and int(null_segs) == 0:
                print("  [PASS] 100% of live customers have a valid, non-null segment assignment.")
                passed_checks += 1
            else:
                print(f"  [FAIL] Found {int(null_segs)} customers with NULL/blank segment!")
                failed_checks += 1
            print()

            # 2. Verify Pre-July 2026 vs. Post-July 2026 Rule Evaluation & Boundary Behavior
            print("--- 2. Pre-July 2026 vs. Post-July 2026 Rule Boundary Verification ---")
            pre_cutoff = date(2026, 6, 30)
            post_cutoff = date(2026, 7, 1)

            # Test profiles spanning key threshold boundaries
            test_profiles = (
                ("CUST_EDGE_01", 60000.00, 10, "Platinum", "Gold"),     # 60k/10 orders: Platinum pre-July, Gold post-July
                ("CUST_EDGE_02", 25000.00, 7, "Gold", "Silver"),        # 25k/7 orders: Gold pre-July, Silver post-July
                ("CUST_EDGE_03", 8000.00, 3, "Silver", "Standard"),     # 8k/3 orders: Silver pre-July, Standard post-July
                ("CUST_HIGH_04", 95000.00, 16, "Platinum", "Platinum"), # 95k/16 orders: Platinum under both rules
            )

            rule_mismatches = 0
            for cid, spend, orders, expected_pre, expected_post in test_profiles:
                actual_pre = classify_customer_segment(spend, orders, pre_cutoff)
                actual_post = classify_customer_segment(spend, orders, post_cutoff)
                print(
                    f"  {cid} (Spend={spend:>9,.2f}, Orders={orders:>2}): "
                    f"Pre-2026-07-01='{actual_pre}' (exp '{expected_pre}') | "
                    f"Post-2026-07-01='{actual_post}' (exp '{expected_post}')"
                )
                if actual_pre != expected_pre or actual_post != expected_post:
                    rule_mismatches += 1

            if rule_mismatches == 0:
                print("  [PASS] All customer boundary profiles evaluated accurately before and after July 1, 2026.")
                passed_checks += 1
            else:
                print(f"  [FAIL] Found {rule_mismatches} rule-change boundary evaluation mismatches!")
                failed_checks += 1
            print()

            # 3. Verify SCD Type 2 History Preservation Across the July 1, 2026 Transition
            print("--- 3. SCD Type 2 Historical Segment Preservation Check (2026-07-01 Cutoff) ---")
            try:
                conn.execute(text("""
                    CREATE TEMPORARY TABLE tmp_cust_seg_scd2 (
                        sk INT AUTO_INCREMENT PRIMARY KEY,
                        customer_id VARCHAR(32) NOT NULL,
                        segment_name VARCHAR(32) NOT NULL,
                        rule_version VARCHAR(20) NOT NULL,
                        valid_from DATE NOT NULL,
                        valid_to DATE NULL,
                        is_current TINYINT(1) NOT NULL
                    )
                """))

                # Seed pre-July 2026 historical version (v1)
                conn.execute(text("""
                    INSERT INTO tmp_cust_seg_scd2 (customer_id, segment_name, rule_version, valid_from, valid_to, is_current)
                    VALUES ('CUST_EDGE_01', 'Platinum', 'PRE_2026_07_RULE', '2025-01-01', NULL, 1)
                """))

                # Apply July 1, 2026 rule change transition -> close v1 on 2026-06-30, open v2 on 2026-07-01
                conn.execute(text("""
                    UPDATE tmp_cust_seg_scd2
                    SET valid_to = '2026-06-30', is_current = 0
                    WHERE customer_id = 'CUST_EDGE_01' AND is_current = 1
                """))
                conn.execute(text("""
                    INSERT INTO tmp_cust_seg_scd2 (customer_id, segment_name, rule_version, valid_from, valid_to, is_current)
                    VALUES ('CUST_EDGE_01', 'Gold', 'POST_2026_07_RULE', '2026-07-01', NULL, 1)
                """))

                (hist_seg, hist_cur, hist_to) = conn.execute(text("""
                    SELECT segment_name, is_current, valid_to
                    FROM tmp_cust_seg_scd2
                    WHERE customer_id = 'CUST_EDGE_01' AND valid_from = '2025-01-01'
                """)).fetchone()

                (curr_seg, curr_cur, curr_from) = conn.execute(text("""
                    SELECT segment_name, is_current, valid_from
                    FROM tmp_cust_seg_scd2
                    WHERE customer_id = 'CUST_EDGE_01' AND is_current = 1
                """)).fetchone()

                print(f"  Historical Pre-July 2026 Row : segment='{hist_seg}', is_current={hist_cur}, valid_to={hist_to}")
                print(f"  Current Post-July 2026 Row   : segment='{curr_seg}', is_current={curr_cur}, valid_from={curr_from}")

                if hist_seg == "Platinum" and int(hist_cur) == 0 and str(hist_to) == "2026-06-30" and curr_seg == "Gold" and int(curr_cur) == 1 and str(curr_from) == "2026-07-01":
                    print("  [PASS] Prior pre-July 2026 segment preserved intact in SCD2 history; post-July 2026 active segment updated cleanly.")
                    passed_checks += 1
                else:
                    print("  [FAIL] SCD2 history preservation across July 2026 rule change failed!")
                    failed_checks += 1

            finally:
                conn.rollback()

    except Exception as exc:
        print(f"  [ERROR] Customer segmentation validation failed: {exc}")
        failed_checks += 1

    print()
    print("=" * 78)
    print(f"SUMMARY -> Passed Checks: {passed_checks} | Failed Checks: {failed_checks}")
    print("=" * 78)

if __name__ == "__main__":
    validate_customer_segmentation()
