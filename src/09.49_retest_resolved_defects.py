import glob, os, subprocess, sys, time
from datetime import datetime
def run():
    print("="*82); print("STEP 09.49: LIVE RETEST EXECUTION OF RESOLVED DEFECTS (DEF-001 TO DEF-004)"); print("="*82)
    cases = [
        ("DEF-001", "Power BI Semantic Model Archive", "src/09.30_validate_powerbi_relationships.py", "Failed Checks: 0"),
        ("DEF-002", "Cost & Profit Margin Formula Alignment", "src/09.23_validate_cost_profit_margin_formulas.py", "Failed Checks: 0"),
        ("DEF-003", "Analytical Views Composite Grain", "src/09.29_validate_analytical_tables.py", "Failed Checks: 0"),
        ("DEF-004", "Unittest Validation Rule Runner", next(iter(glob.glob("src/09.06_*.py"))), "OK")
    ]
    passed, failed = 0, 0
    rows = []
    for did, title, script, token in cases:
        t0 = time.perf_counter()
        res = subprocess.run([sys.executable, script], capture_output=True, text=True)
        dt = time.perf_counter() - t0
        out = (res.stdout or "") + "\n" + (res.stderr or "")
        ok = (res.returncode == 0) and (token in out)
        status = "VERIFIED CLOSED" if ok else "REOPENED"
        if ok: passed += 1
        else: failed += 1
        print(f"  [{did}] {title:<38} | Script={os.path.basename(script):<42} | {status} ({dt:.2f}s)")
        rows.append((did, title, script, dt, status))
    os.makedirs("docs", exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md = ["# Step 09.49 - Resolved Defect Live Retest Evidence", "", f"**Retest Execution Timestamp:** {ts}  ", f"**Retest Result:** **{passed}/{len(cases)} Verified Closed ({failed} Reopened)**", "", "| Defect ID | Defect Summary | Executed Retest Script | Duration | Final Closure Status |", "| :--- | :--- | :--- | :---: | :---: |"]
    for did, title, script, dt, status in rows:
        md.append(f"| {did} | {title} | `{script}` | {dt:.2f}s | **{status}** |")
    with open("docs/09.49_Defect_Retest_Verification.md", "w", encoding="utf-8") as fp: fp.write("\n".join(md) + "\n")
    print("\n" + "="*82); print(f"RETEST SUMMARY -> Passed Checks: {passed} | Failed Checks: {failed} | Evidence: docs/09.49_Defect_Retest_Verification.md"); print("="*82)
if __name__=="__main__": run()


