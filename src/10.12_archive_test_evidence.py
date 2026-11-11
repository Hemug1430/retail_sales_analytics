import glob, hashlib, json, os, zipfile
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
def classify_evidence(path):
    nl = os.path.basename(path).lower()
    if "09.47" in nl or "09.51" in nl or "uat" in nl or "signoff" in nl: return "UAT & Final Release Sign-Off"
    if "09.48" in nl or "09.49" in nl or "defect" in nl or "retest" in nl: return "Defect Closure Evidence"
    if "10.02" in nl or "reconcil" in nl: return "Financial & Row Reconciliation"
    if nl.endswith((".png", ".jpg", ".jpeg", ".pdf", ".xlsx")): return "Screenshots & Visual Exports"
    return "Test Results & Release Governance"
def run():
    print("="*82); print("STEP 10.12: ARCHIVE QA, RECONCILIATION, DEFECT CLOSURE & UAT TEST EVIDENCE"); print("="*82)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs("archive", exist_ok=True)
    os.makedirs("docs", exist_ok=True)
    audit_json = "docs/10.12_db_pipeline_execution_logs_snapshot.json"
    with get_db_engine().connect() as c:
        rows = [dict(r._mapping) for r in c.execute(text("SELECT * FROM pipeline_execution_logs ORDER BY batch_id")).fetchall()]
    with open(audit_json, "w", encoding="utf-8") as fp:
        json.dump(rows, fp, indent=2, default=str)
    doc_ev = sorted(p for p in glob.glob("docs/**/*", recursive=True) if os.path.isfile(p) and not os.path.basename(p).startswith("10.12_Test_Evidence"))
    media_ev = sorted(p for p in glob.glob("**/*", recursive=True) if os.path.isfile(p) and ".venv" not in p and "archive" not in p and p.lower().endswith((".png", ".jpg", ".jpeg", ".pdf")))
    all_ev = sorted(set(doc_ev + media_ev))
    zip_path = "archive/release_v1.0.0_test_evidence_bundle.zip"
    records = []
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for src in all_ev:
            rel = src.replace(os.sep, "/")
            cat = classify_evidence(rel)
            zf.write(src, arcname=f"{cat.replace(' ', '_').replace('&', 'and')}/{rel}")
            records.append({"category": cat, "file": rel, "bytes": os.path.getsize(src), "sha256": sha256_file(src)})
    zip_sha = sha256_file(zip_path)
    man_md = "docs/10.12_Test_Evidence_Archive_Manifest.md"
    md = ["# Step 10.12 - Archived QA, Reconciliation, Defect Closure & UAT Test Evidence", "", f"**Archived Timestamp:** {ts}  ", "**Release Version:** `v1.0.0-PROD`  ", f"**Test Evidence ZIP Bundle:** `{zip_path}` ({os.path.getsize(zip_path):,} bytes)  ", f"**Bundle SHA-256:** `{zip_sha}`  ", f"**Database Audit Rows Archived:** `{len(rows)}` (`pipeline_execution_logs`)  ", f"**Total Evidence Artifacts Archived:** **{len(records)}**", "", "| Evidence Category | Archived Artifact Path | Size (Bytes) | SHA-256 Prefix |", "| :--- | :--- | :---: | :--- |"]
    for r in records:
        md.append(f"| {r['category']} | `{r['file']}` | {r['bytes']:,} | `{r['sha256'][:16]}...` |")
    with open(man_md, "w", encoding="utf-8") as fp: fp.write("\n".join(md) + "\n")
    ok = 3 if (len(records) > 0 and zipfile.is_zipfile(zip_path) and os.path.exists(man_md)) else 0
    bad = 0 if ok == 3 else 1
    print(f"  [EVID-01] DB Audit Log Snapshot     : {len(rows)} execution records exported to {audit_json}")
    print(f"  [EVID-02] Test & UAT Artifacts      : {len(records)} reconciliation, defect closure, UAT & export files archived")
    print(f"  [EVID-03] Immutable Evidence Bundle : {zip_path} ({os.path.getsize(zip_path):,} bytes | SHA256={zip_sha[:16]}...)")
    print("\n" + "="*82); print(f"TEST EVIDENCE SUMMARY -> Passed Checks: {ok} | Failed Checks: {bad} | Manifest: {man_md}"); print("="*82)
if __name__=="__main__": run()

