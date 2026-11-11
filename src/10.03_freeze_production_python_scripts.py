import glob, hashlib, json, os, subprocess, sys
from datetime import datetime
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""): h.update(chunk)
    return h.hexdigest()
def classify_script(name):
    nl = name.lower()
    if nl.startswith("09.") or "test" in nl or "validate" in nl: return "QA & Validation"
    if nl.startswith("10.") or "release" in nl or "freeze" in nl: return "Release & Governance"
    if "clean" in nl or "standardiz" in nl or "dedup" in nl or "duplicate" in nl: return "Cleaning & Standardization"
    if "ingest" in nl or "archive" in nl or "batch" in nl or "hash" in nl or "profil" in nl: return "Ingestion & Staging"
    if "analytic" in nl or "kpi" in nl or "metric" in nl or "rank" in nl: return "Analytics & Metrics"
    return "Core ETL & Utility"
def run():
    print("="*82); print("STEP 10.03: FREEZE PRODUCTION PYTHON SCRIPTS & RELEASE MANIFEST (v1.0.0-PROD)"); print("="*82)
    version_tag = "v1.0.0-PROD"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scripts = sorted(p for p in glob.glob("src/**/*.py", recursive=True) if os.path.isfile(p))
    manifest_items = []
    for sp in scripts:
        bn = os.path.basename(sp)
        with open(sp, "r", encoding="utf-8", errors="ignore") as fp: lines = sum(1 for _ in fp)
        manifest_items.append({"script": bn, "path": sp.replace("\\","/"), "module": classify_script(bn), "version": version_tag, "bytes": os.path.getsize(sp), "lines": lines, "sha256": sha256_file(sp)})
    req_res = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True)
    with open("requirements.txt", "w", encoding="utf-8") as fp: fp.write(req_res.stdout)
    pkg_cnt = len([l for l in req_res.stdout.splitlines() if l.strip()])
    os.makedirs("docs", exist_ok=True)
    json_path = "docs/10.03_python_release_manifest_v1.0.0.json"
    with open(json_path, "w", encoding="utf-8") as fp:
        json.dump({"release_tag": version_tag, "frozen_at": ts, "python_version": sys.version.split(), "total_scripts": len(manifest_items), "pinned_packages": pkg_cnt, "scripts": manifest_items}, fp, indent=2)
    md_path = "docs/10.03_Production_Python_Release_Manifest_v1.0.0.md"
    md = ["# Step 10.03 - Frozen Production Python Scripts & Checksum Manifest", "", f"**Release Tag:** `{version_tag}`  ", f"**Frozen Timestamp:** {ts}  ", f"**Total Frozen Scripts:** **{len(manifest_items)}** (`src/*.py`)  ", f"**Pinned Dependencies (`requirements.txt`):** **{pkg_cnt} packages**", "", "| Script Name | Functional Module | Tag | Lines | Size (Bytes) | SHA-256 Digest (Prefix) |", "| :--- | :--- | :---: | :---: | :---: | :--- |"]
    for it in manifest_items:
        md.append(f"| `{it['script']}` | {it['module']} | `{it['version']}` | {it['lines']} | {it['bytes']:,} | `{it['sha256'][:16]}...` |")
    with open(md_path, "w", encoding="utf-8") as fp: fp.write("\n".join(md) + "\n")
    ok = 3 if (len(manifest_items) > 0 and pkg_cnt > 0 and os.path.exists(json_path) and os.path.exists(md_path)) else 0
    bad = 0 if ok == 3 else 1
    print(f"  [FREEZE-01] Production Scripts Frozen : {len(manifest_items)} scripts tagged as {version_tag}")
    print(f"  [FREEZE-02] Environment Lockfile      : requirements.txt updated ({pkg_cnt} pinned packages)")
    print(f"  [FREEZE-03] SHA-256 Release Manifests : {md_path} & {json_path}")
    print("\n" + "="*82); print(f"PYTHON FREEZE SUMMARY -> Passed Checks: {ok} | Failed Checks: {bad} | Tag: {version_tag}"); print("="*82)
if __name__=="__main__": run()


