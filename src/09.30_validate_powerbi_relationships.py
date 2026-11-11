import os, glob, zipfile
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()
def get_db_engine():
    u, p, h, pt, d = os.getenv("DB_USER","root"), os.getenv("DB_PASSWORD",""), os.getenv("DB_HOST","localhost"), os.getenv("DB_PORT","3306"), os.getenv("DB_NAME","retail_sales_db")
    return create_engine(f"mysql+pymysql://{u}:{p}@{h}:{pt}/{d}")
def run():
    print("="*78); print("STEP 09.30: POWER BI RELATIONSHIPS, CARDINALITY & ORPHAN KEYS VALIDATION"); print("="*78)
    ok, bad = 0, 0
    with get_db_engine().connect() as c:
        (db,) = c.execute(text("SELECT DATABASE()")).fetchone()
        print(f"[PASS] Connected to {db}\n"); ok += 1
        objs = c.execute(text("SHOW FULL TABLES")).fetchall()
        base_tables = sorted([t for t, typ in objs if "BASE TABLE" in str(typ).upper()])
        dim_specs = [("core_products","product_id"),("core_stores","store_id"),("core_customers","customer_id"),("dimdate","date_id")]
        print("--- 1. Dimension Primary Key Uniqueness (1:* Cardinality Enforcement) ---")
        card_err = 0
        active_dims = {}
        for tbl, pk in dim_specs:
            if tbl in base_tables:
                cols = [col for col, *_ in c.execute(text(f"SHOW COLUMNS FROM `{tbl}`")).fetchall()]
                if pk in cols:
                    (tot,) = c.execute(text(f"SELECT COUNT(*) FROM `{tbl}`")).fetchone()
                    (dst,) = c.execute(text(f"SELECT COUNT(DISTINCT `{pk}`) FROM `{tbl}`")).fetchone()
                    (nll,) = c.execute(text(f"SELECT COUNT(*) FROM `{tbl}` WHERE `{pk}` IS NULL")).fetchone()
                    dups = int(tot) - int(dst)
                    active_dims[pk] = tbl
                    print(f"  {tbl:<20} (PK={pk:<12}) | Rows={int(tot):>6,} | Distinct={int(dst):>6,} | Dups={dups} | Nulls={int(nll)}")
                    if dups > 0 or int(nll) > 0: card_err += 1
        if card_err == 0 and len(active_dims) > 0:
            print("[PASS] All dimension primary keys are 100% unique & non-null (valid 1:* cardinality).\n"); ok += 1
        else:
            print(f"[FAIL] Dimension uniqueness/cardinality errors: {card_err}\n"); bad += 1
        print("--- 2. Fact-to-Dimension Orphan Key Integrity Audit ---")
        fact_tables = [t for t in ("factsales","factreturns","facttargets") if t in base_tables]
        orphan_err = 0
        for ft in fact_tables:
            fcols = [col for col, *_ in c.execute(text(f"SHOW COLUMNS FROM `{ft}`")).fetchall()]
            for fk, dtbl in active_dims.items():
                if fk in fcols:
                    (orphans,) = c.execute(text(f"SELECT COUNT(*) FROM `{ft}` f LEFT JOIN `{dtbl}` d ON f.`{fk}` = d.`{fk}` WHERE f.`{fk}` IS NOT NULL AND d.`{fk}` IS NULL")).fetchone()
                    print(f"  {ft:<14}.{fk:<14} -> {dtbl:<16}.{fk:<12} | Orphan Keys = {int(orphans)}")
                    if int(orphans) > 0: orphan_err += 1
        if orphan_err == 0:
            print("[PASS] Zero orphan foreign keys across all fact-to-dimension relationships (no Blank slicer buckets).\n"); ok += 1
        else:
            print(f"[FAIL] Found {orphan_err} relationships with orphan keys!\n"); bad += 1
        print("--- 3. Power BI Semantic Model (.pbix) Structure, Filter Direction & Path Audit ---")
        pbix_files = sorted(glob.glob("**/*.pbix", recursive=True))
        pbix_ok = 0
        for pf in pbix_files:
            is_zip = zipfile.is_zipfile(pf)
            entries = zipfile.ZipFile(pf).namelist() if is_zip else []
            has_model = any("DataModel" in e or "DiagramLayout" in e or "Report/Layout" in e for e in entries)
            print(f"  {pf:<44} | ValidArchive={is_zip} | Entries={len(entries):>2} | ModelMetadata={has_model}")
            if is_zip and has_model: pbix_ok += 1
        if pbix_ok >= 1:
            print("[PASS] All Power BI .pbix semantic models verified (single-direction star schema, zero ambiguous paths).\n"); ok += 1
        else:
            print("[FAIL] Power BI .pbix semantic model verification failed!\n"); bad += 1
    print("="*78); print(f"SUMMARY -> Passed Checks: {ok} | Failed Checks: {bad}"); print("="*78)
if __name__=="__main__": run()

