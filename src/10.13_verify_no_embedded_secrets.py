import glob, os, re, zipfile
from datetime import datetime
from dotenv import dotenv_values
def run():
    print("="*82); print("STEP 10.13: SECURITY AUDIT - VERIFY NO EMBEDDED PASSWORDS OR SECRETS"); print("="*82)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    env_map = dotenv_values(".env") if os.path.exists(".env") else {}
    secret_vals = [v.strip() for k, v in env_map.items() if v and len(v.strip()) >= 4 and v.strip().lower() not in ("root","localhost","3306","retail_sales_db") and any(t in k.upper() for t in ("PASS", "SECRET", "TOKEN", "KEY", "PWD"))]
    gi_ok = False
    if os.path.exists(".gitignore"):
        with open(".gitignore", "r", encoding="utf-8", errors="ignore") as fp: gi_txt = fp.read()
        gi_ok = (".env" in gi_txt)
    scan_exts = (".py", ".sql", ".ipynb", ".md", ".json", ".yml", ".yaml", ".txt", ".ps1", ".bat")
    files = sorted(p for p in glob.glob("**/*", recursive=True) if os.path.isfile(p) and ".venv" not in p and "retail_venv" not in p.lower() and ".git" not in p and os.path.basename(p) != ".env" and not p.startswith("backups") and p.lower().endswith(scan_exts))
    q = "[" + chr(34) + chr(39) + "]"
    hardcoded_re = re.compile(r"(?:DB_PASSWORD|MYSQL_PWD|API_KEY|SECRET_KEY|ACCESS_TOKEN)\s*=\s*" + q + r"[A-Za-z0-9_@#$%^&*!.-]{4,}" + q, re.IGNORECASE)
    uri_pass_re = re.compile(r"mysql\+pymysql://[^:\s]+:[^@\s{]+@", re.IGNORECASE)
    findings = []
    for fp in files:
        with open(fp, "r", encoding="utf-8", errors="ignore") as f: txt = f.read()
        for sv in secret_vals:
            if sv in txt: findings.append((fp.replace(os.sep, "/"), "Literal .env secret value detected"))
        if hardcoded_re.search(txt): findings.append((fp.replace(os.sep, "/"), "Hardcoded credential assignment detected"))
        if uri_pass_re.search(txt): findings.append((fp.replace(os.sep, "/"), "Hardcoded DB URI password detected"))
    zip_leaks = []
    for zp in sorted(glob.glob("archive/*.zip")):
        with zipfile.ZipFile(zp, "r") as zf:
            for entry in zf.namelist():
                if os.path.basename(entry) == ".env": zip_leaks.append(f"{zp} -> {entry}")
    c1, c2, c3 = gi_ok, (len(findings) == 0), (len(zip_leaks) == 0)
    s1 = "PASS" if c1 else "FAIL"
    s2 = "PASS" if c2 else "FAIL"
    s3 = "PASS" if c3 else "FAIL"
    os.makedirs("docs", exist_ok=True)
    cert_path = "docs/10.13_Secrets_Security_Audit_Certificate.md"
    md = ["# Step 10.13 - Secrets & Credential Hygiene Security Audit Certificate", "", f"**Audit Timestamp:** {ts}  ", "**Release Version:** `v1.0.0-PROD`  ", f"**Files Scanned:** **{len(files)}** (Python, SQL, Notebooks, PBIX Docs, JSON/YAML manifests)  ", f"**`.gitignore` `.env` Protection:** **{s1}**  ", f"**Embedded Credential Findings:** **{len(findings)}** (`0` required)  ", f"**Archive Bundle `.env` Leaks:** **{len(zip_leaks)}** (`0` required)", "", "| Security Control | Scope Audited | Result |", "| :--- | :--- | :---: |", f"| `.gitignore` Secret Exclusion | `.env` excluded from version control | **{s1}** |", f"| Source, SQL, Notebook & Docs Scan | {len(files)} repository files checked for literal/hardcoded secrets | **{s2}** |", f"| Release Archive & Shared Artifacts | `archive/*.zip` bundles checked for accidental `.env` inclusion | **{s3}** |"]
    if findings:
        md += ["", "## Findings Requiring Remediation"] + [f"- `{p}`: {msg}" for p, msg in findings]
    with open(cert_path, "w", encoding="utf-8") as fp: fp.write("\n".join(md) + "\n")
    ok = sum([c1, c2, c3])
    bad = 3 - ok
    print(f"  [SEC-01] .gitignore .env Exclusion   : {s1}")
    print(f"  [SEC-02] Code/SQL/Notebook/Docs Scan : {len(files)} files scanned | Findings={len(findings)}")
    print(f"  [SEC-03] Shared Archive Bundles      : {len(glob.glob('archive/*.zip'))} ZIPs scanned | Leaks={len(zip_leaks)}")
    print("\n" + "="*82); print(f"SECRETS AUDIT SUMMARY -> Passed Checks: {ok} | Failed Checks: {bad} | Cert: {cert_path}"); print("="*82)
if __name__=="__main__": run()



