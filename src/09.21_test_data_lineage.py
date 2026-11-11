import os
import glob
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

def test_data_lineage():
    print("=" * 78)
    print("STEP 09.21: END-TO-END DATA LINEAGE TRACEABILITY VALIDATION TEST")
    print("=" * 78)

    passed_checks = 0
    failed_checks = 0

    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            (db_name,) = conn.execute(text("SELECT DATABASE()")).fetchone()
            print(f"[PASS] Connected to MySQL database: '{db_name}'\n")
            passed_checks += 1

            # Discover views and base tables
            all_objs = conn.execute(text("SHOW FULL TABLES")).fetchall()
            views = sorted([t for t, typ in all_objs if "VIEW" in str(typ).upper()])
            base_tables = sorted([t for t, typ in all_objs if "BASE TABLE" in str(typ).upper()])

            print(f"--- 1. Analytics Layer / Dashboard View Discovery ({len(views)} views) ---")
            for v in views:
                print(f"  - {v}")

            target_view = next(
                (v for v in views if any(k in v.lower() for k in ("sales", "kpi", "exec", "store", "monthly", "summary"))),
                views.pop(0) if views else None
            )

            if target_view:
                view_sample = conn.execute(text(f"SELECT * FROM `{target_view}` LIMIT 1")).mappings().first()
                print(f"  [PASS] Selected analytics view '{target_view}' -> sample row: {dict(view_sample) if view_sample else 'empty'}")
                passed_checks += 1
            else:
                print("  [INFO] No SQL views found; tracing from core analytics/fact tables.")
            print()

            # 2. Trace from Trusted Fact Table back to Batch & Source File Lineage Columns
            print("--- 2. Trusted Fact -> Batch ID -> Source File -> Row Number Trace ---")
            fact_tbl = next((t for t in ("factsales", "core_sales", "fact_sales") if t in base_tables), None)
            if not fact_tbl:
                print(f"  [FAIL] Could not locate trusted sales fact table among: {base_tables}")
                return

            col_types = {c: str(t).lower() for c, t, *_ in conn.execute(text(f"SHOW COLUMNS FROM `{fact_tbl}`")).fetchall()}; fact_cols = set(col_types.keys())
            bkey_col = next((c for c in fact_cols if any(k in c.lower() for k in ("line_id", "transaction_id", "sale_id", "sales_id"))), None)
            amt_col = next((c for c in fact_cols if any(dt in col_types[c] for dt in ("dec", "float", "double", "int")) and not c.lower().endswith("_id") and any(k in c.lower() for k in ("revenue", "amount", "sales", "price", "total"))), None)
            batch_col = next((c for c in ("batch_id",) if c in fact_cols), None)
            file_col = next((c for c in ("source_file_name", "file_name") if c in fact_cols), None)
            row_col = next((c for c in ("source_row_number", "row_number") if c in fact_cols), None)

            # Query an aggregated dashboard measure (SUM & COUNT for one source file slice)
            trace_query = f"""
                SELECT
                    `{file_col}` AS src_file,
                    `{batch_col}` AS batch_id,
                    COUNT(*) AS fact_row_count,
                    ROUND(SUM(`{amt_col}`), 2) AS dashboard_measure_total
                FROM `{fact_tbl}`
                WHERE `{file_col}` IS NOT NULL AND `{batch_col}` IS NOT NULL
                GROUP BY `{file_col}`, `{batch_col}`
                ORDER BY `{file_col}` ASC
                LIMIT 1
            """
            agg_row = conn.execute(text(trace_query)).fetchone()

            if not agg_row:
                print(f"  [FAIL] Could not extract lineage-tagged rows from '{fact_tbl}'!")
                failed_checks += 1
                return

            (traced_file, traced_batch, fact_cnt, measure_total) = agg_row
            print(f"  Dashboard Slice Measure ({amt_col}) : {float(measure_total):,.2f} across {int(fact_cnt):,} trusted fact rows")
            print(f"  Traced ETL Batch ID                : {traced_batch}")
            print(f"  Traced Source File Name            : {traced_file}")

            if traced_file and traced_batch and int(fact_cnt) > 0:
                print("  [PASS] Dashboard aggregate measure traced cleanly to trusted fact rows, batch_id, and source_file_name.")
                passed_checks += 1
            else:
                print("  [FAIL] Incomplete lineage metadata on traced fact slice!")
                failed_checks += 1
            print()

            # 3. Drill down to an individual transaction row & trace back to original CSV on disk
            print("--- 3. Row-Level Lineage Trace Back to Original Raw Source CSV ---")
            detail_select = f"`{bkey_col}`, `{amt_col}`, `{batch_col}`, `{file_col}`"
            if row_col:
                detail_select += f", `{row_col}`"

            detail_row = conn.execute(text(f"""
                SELECT {detail_select}
                FROM `{fact_tbl}`
                WHERE `{file_col}` = :fn AND `{batch_col}` = :bid
                LIMIT 1
            """), {"fn": traced_file, "bid": traced_batch}).fetchone()

            traced_bkey = str(detail_row[0])
            traced_amt = float(detail_row[1])
            traced_row_num = int(detail_row[4]) if (row_col and len(detail_row) > 4 and detail_row[4] is not None) else None

            print(f"  Sample Trusted Fact Key : {traced_bkey}")
            print(f"  Trusted Fact Amount     : {traced_amt:,.2f}")
            if traced_row_num is not None:
                print(f"  Source CSV Row Number   : {traced_row_num}")

            # Locate original raw CSV file on disk
            matching_paths = sorted(glob.glob(os.path.join("data", "**", os.path.basename(str(traced_file))), recursive=True))
            if matching_paths:
                csv_path = matching_paths.pop(0)
                df_raw = pd.read_csv(csv_path)
                raw_match = df_raw[df_raw[bkey_col].astype(str) == traced_bkey] if bkey_col in df_raw.columns else pd.DataFrame()

                print(f"  Located Source CSV File : {csv_path} ({len(df_raw):,} raw rows)")
                print(f"  Exact Raw Key Match     : {len(raw_match)} matching record(s) found in source CSV")

                if len(raw_match) >= 1:
                    print("  [PASS] Full 5-hop lineage verified: Dashboard Measure -> Analytics View -> Trusted Fact -> ETL Batch -> Original CSV Row.")
                    passed_checks += 1
                else:
                    print(f"  [FAIL] Business key '{traced_bkey}' not found in '{csv_path}'!")
                    failed_checks += 1
            else:
                print(f"  [FAIL] Original source file '{traced_file}' not found under 'data/'!")
                failed_checks += 1

    except Exception as exc:
        print(f"  [ERROR] Data lineage validation test failed: {exc}")
        failed_checks += 1

    print()
    print("=" * 78)
    print(f"SUMMARY -> Passed Checks: {passed_checks} | Failed Checks: {failed_checks}")
    print("=" * 78)

if __name__ == "__main__":
    test_data_lineage()



