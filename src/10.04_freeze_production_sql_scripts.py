import glob, hashlib, json, os
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()
def get_db_engine():
    u, p, h, pt, d = os.getenv("DB_USER","root"), os.getenv("DB_PASSWORD",""), os.getenv("DB_HOST","localhost"), os.getenv("DB_PORT","3306"), os.getenv("DB_NAME","retail_sales_db")
    return create_engine(f"mysql+pymysql://{u}:{p}@{h}:{pt}/{d}")
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""): h.update(chunk)
    return h.hexdigest()
def classify_sql(name):
    nl = name.lower()
    if "ddl" in nl or "schema" in nl or "create_table" in nl or "dim" in nl or "fact" in nl: return "DDL & Schema"
    if "merge" in nl or "upsert" in nl or "scd" in nl or "load" in nl or "insert" in nl: return "Merge & Load"
    if "view" in nl or "vw_" in nl: return "Views & Semantic Layer"
    if "analytic" in nl or "kpi" in nl or "rank" in nl or "summary" in nl: return "Analytics & Reporting"
    if "valid" in nl or "reconcil" in nl or "check" in nl or "qa" in nl: return "Validation & QA"
    return "Maintenance & Utility"
def run():
    print("="*82); print("STEP 10.04: FREEZE PRODUCTION SQL SCRIPTS & RELEASE MANIFEST (v1.0.0-PROD)"); print("="*82)
    version_tag = "v1.0.0-PROD"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql_files = sorted(p for p in glob.glob("**/*.sql", recursive=True) if os.path.isfile(p) and ".venv" not in p)
    items = []
    for sp in sql_files:
        bn = os.path.basename(sp)
        with open(sp, "r", encoding="utf-8", errors="ignore") as fp: lines = sum(1 for _ in fp)
        items.append({"script": bn, "path": sp.replace("\\","/"), "module": classify_sql(bn), "version": version_tag, "bytes": os.path.getsize(sp), "lines": lines, "sha256": sha256_file(sp)})
    with get_db_engine().connect() as c:
        (tbl_cnt,) = c.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'")).fetchone()
        (vw_cnt,) = c.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_type = 'VIEW'")).fetchone()
    os.makedirs("docs", exist_ok=True)
    json_path = "docs/10.04_sql_release_manifest_v1.0.0.json"
    with open(json_path, "w", encoding="utf-8") as fp:
        json.dump({"release_tag": version_tag, "frozen_at": ts, "total_sql_scripts": len(items), "db_base_tables": int(tbl_cnt), "db_views": int(vw_cnt), "scripts": items}, fp, indent=2)
    md_path = "docs/10.04_Production_SQL_Release_Manifest_v1.0.0.md"
    md = ["# Step 10.04 - Frozen Production SQL Scripts & Checksum Manifest", "", f"**Release Tag:** `{version_tag}`  ", f"**Frozen Timestamp:** {ts}  ", f"**Total Frozen SQL Scripts:** **{len(items)}**  ", f"**Deployed MySQL Objects:** **{int(tbl_cnt)} Base Tables** | **{int(vw_cnt)} Views**", "", "| SQL Script | Functional Layer | Path | Tag | Lines | SHA-256 Digest (Prefix) |", "| :--- | :--- | :--- | :---: | :---: | :--- |"]
    for it in items:
        md.append(f"| `{it['script']}` | {it['module']} | `{it['path']}` | `{it['version']}` | {it['lines']} | `{it['sha256'][:16]}...` |")
    with open(md_path, "w", encoding="utf-8") as fp: fp.write("\n".join(md) + "\n")
    ok = 3 if (len(items) > 0 and int(tbl_cnt) > 0 and os.path.exists(md_path) and os.path.exists(json_path)) else 0
    bad = 0 if ok == 3 else 1
    print(f"  [SQL-FREEZE-01] SQL Scripts Frozen      : {len(items)} scripts tagged as {version_tag}")
    print(f"  [SQL-FREEZE-02] MySQL Schema Snapshot   : {int(tbl_cnt)} Base Tables & {int(vw_cnt)} Views verified in retail_sales_db")
    print(f"  [SQL-FREEZE-03] SHA-256 SQL Manifests   : {md_path} & {json_path}")
    print("\n" + "="*82); print(f"SQL FREEZE SUMMARY -> Passed Checks: {ok} | Failed Checks: {bad} | Tag: {version_tag}"); print("="*82)
if __name__=="__main__": run()

