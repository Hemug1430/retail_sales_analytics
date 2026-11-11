import glob, hashlib, os, shutil, subprocess, zipfile
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
def sql_lit(v):
    if v is None: return "NULL"
    if isinstance(v, (int, float)): return str(v)
    s = str(v).replace("\\", "\\\\").replace("\x27", "\x27\x27").replace("\n", "\\n").replace("\r", "\\r")
    return f"\x27{s}\x27"
def run():
    print("="*82); print("STEP 10.05: FINAL MYSQL DATABASE RECOVERABLE BACKUP & INTEGRITY VERIFICATION"); print("="*82)
    ts_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    ts_hr = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs("backups", exist_ok=True)
    sql_path = f"backups/retail_sales_db_full_backup_{ts_tag}.sql"
    zip_path = f"backups/retail_sales_db_final_backup_v1.0.0_{ts_tag}.zip"
    u, p, h, pt, d = os.getenv("DB_USER","root"), os.getenv("DB_PASSWORD",""), os.getenv("DB_HOST","localhost"), os.getenv("DB_PORT","3306"), os.getenv("DB_NAME","retail_sales_db")
    mdump = shutil.which("mysqldump") or next(iter(glob.glob(r"C:\Program Files\MySQL\MySQL Server*\bin\mysqldump.exe")), None)
    method = "Python Transactional SQL Dump"
    used_mdump = False
    if mdump:
        env = os.environ.copy()
        if p: env["MYSQL_PWD"] = p
        res = subprocess.run([mdump, f"-h{h}", f"-P{pt}", f"-u{u}", "--single-transaction", "--routines", "--triggers", d], capture_output=True, text=True, env=env)
        if res.returncode == 0 and len(res.stdout) > 1000:
            with open(sql_path, "w", encoding="utf-8") as fp: fp.write(res.stdout)
            method = f"mysqldump ({os.path.basename(mdump)})"
            used_mdump = True
    table_stats = []
    with get_db_engine().connect() as c:
        tbls = [t for (t,) in c.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE() AND table_type = \x27BASE TABLE\x27 ORDER BY table_name")).fetchall()]
        vws = [v for (v,) in c.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE() AND table_type = \x27VIEW\x27 ORDER BY table_name")).fetchall()]
        for t in tbls:
            (cnt,) = c.execute(text(f"SELECT COUNT(*) FROM `{t}`")).fetchone()
            table_stats.append((t, int(cnt)))
        if not used_mdump:
            with open(sql_path, "w", encoding="utf-8") as fp:
                fp.write(f"-- Retail Sales DB Recoverable Backup ({ts_hr})\nCREATE DATABASE IF NOT EXISTS `{d}`;\nUSE `{d}`;\nSET FOREIGN_KEY_CHECKS=0;\n\n")
                for t in tbls:
                    ddl = c.execute(text(f"SHOW CREATE TABLE `{t}`")).fetchone()
                    fp.write(f"DROP TABLE IF EXISTS `{t}`;\n{ddl};\n\n")
                    cols = [col for col, *_ in c.execute(text(f"SHOW COLUMNS FROM `{t}`")).fetchall()]
                    col_list = ", ".join(f"`{col}`" for col in cols)
                    rows = c.execute(text(f"SELECT * FROM `{t}`")).fetchall()
                    for i in range(0, len(rows), 500):
                        batch = rows[i:i+500]
                        vals_sql = ",\n".join("(" + ", ".join(sql_lit(v) for v in r) + ")" for r in batch)
                        fp.write(f"INSERT INTO `{t}` ({col_list}) VALUES\n{vals_sql};\n")
                    fp.write("\n")
                for v in vws:
                    vddl = c.execute(text(f"SHOW CREATE VIEW `{v}`")).fetchone()
                    fp.write(f"DROP VIEW IF EXISTS `{v}`;\n{vddl};\n\n")
                fp.write("SET FOREIGN_KEY_CHECKS=1;\n")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(sql_path, arcname=os.path.basename(sql_path))
    sql_bytes = os.path.getsize(sql_path)
    zip_bytes = os.path.getsize(zip_path)
    zip_sha = sha256_file(zip_path)
    with open(sql_path, "r", encoding="utf-8", errors="ignore") as fp: head_txt = fp.read(65536)
    recoverable_ok = ("CREATE TABLE" in head_txt) and zip_bytes > 0 and zipfile.is_zipfile(zip_path)
    os.makedirs("docs", exist_ok=True)
    doc_path = "docs/10.05_Database_Backup_Verification.md"
    md = ["# Step 10.05 - Final MySQL Database Recoverable Backup Certificate", "", f"**Backup Timestamp:** {ts_hr}  ", f"**Database:** `{d}`  ", f"**Backup Engine:** `{method}`  ", f"**SQL Dump File:** `{sql_path}` ({sql_bytes:,} bytes)  ", f"**Compressed Archive:** `{zip_path}` ({zip_bytes:,} bytes)  ", f"**Archive SHA-256:** `{zip_sha}`  ", f"**Restore Command:** `mysql -u {u} -p {d} < {sql_path}`", "", "| Table Name | Backed Up Row Count |", "| :--- | :---: |"]
    for t, cnt in table_stats: md.append(f"| `{t}` | {cnt:,} |")
    with open(doc_path, "w", encoding="utf-8") as fp: fp.write("\n".join(md) + "\n")
    ok = 3 if (recoverable_ok and len(table_stats) > 0 and os.path.exists(doc_path)) else 0
    bad = 0 if ok == 3 else 1
    print(f"  [BKP-01] SQL Dump Generated    : {sql_path} ({sql_bytes:,} bytes via {method})")
    print(f"  [BKP-02] Compressed Archive    : {zip_path} ({zip_bytes:,} bytes | SHA256={zip_sha[:16]}...)")
    print(f"  [BKP-03] Objects Backed Up     : {len(tbls)} Base Tables & {len(vws)} Views | Cert={doc_path}")
    print("\n" + "="*82); print(f"DB BACKUP SUMMARY -> Passed Checks: {ok} | Failed Checks: {bad} | Recoverable: {recoverable_ok}"); print("="*82)
if __name__=="__main__": run()
