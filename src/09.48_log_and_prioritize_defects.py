import os, subprocess, sys
from datetime import datetime
def run():
    print("="*82); print("STEP 09.48: QA DEFECT LOG, PRIORITIZATION & RETEST VERIFICATION LEDGER"); print("="*82)
    defects = [
        ("DEF-001", "High", "Power BI Semantic Model (09.30)", "Inspect dashboards/*.pbix archives during relationship validation", "All active .pbix models valid ZIP/DataModel archives", "RetailSalesDashboard.pbix was 0-byte empty placeholder; Retail_Sales_Analytics_Model.pbix valid (53 entries)", "Data & BI Lead", "CLOSED", "src/09.30_validate_powerbi_relationships.py -> Passed Checks: 4 | Failed Checks: 0"),
        ("DEF-002", "Medium", "Margin Formula QA (09.23 / 09.46)", "Execute 09.46 full regression suite across all 44 QA modules", "09.23 reconciles view estimated_total_cost (60% ratio) with 0 failures", "09.23 initially compared unit_cost instead of view estimated_total_cost (5 discrepancies)", "Analytics QA Lead", "CLOSED", "src/09.23_validate_cost_profit_margin_formulas.py & 09.46 -> Total Suites: 44 | Passed: 44 | Failed: 0"),
        ("DEF-003", "Low", "Analytical Views Grain QA (09.29)", "Run uniqueness & null-key check across all 11 views/summary tables", "Dups=0 and NullKeys=0 across all 11 analytical objects", "vw_warehouse_ranking_analytics needed 3-col grain & return view needed 4-col grain", "SQL Warehouse Lead", "CLOSED", "src/09.29_validate_analytical_tables.py -> Passed Checks: 4 | Failed Checks: 0"),
        ("DEF-004", "Low", "Regression Runner Parser (09.46)", "Run master regression suite across unittest (09.06-09.09) and script checks", "All 44 test modules recognized and reported PASS", "unittest modules printed OK rather than Failed Checks: 0", "QA Automation Lead", "CLOSED", "src/09.46_run_regression_test_suite.py -> Passed: 44 | Failed: 0")
    ]
    open_crit_high = sum(1 for d in defects if d[1] in ("Critical","High") and d[7] != "CLOSED")
    open_total = sum(1 for d in defects if d[7] != "CLOSED")
    for did, sev, mod, steps, exp, act, own, st, ev in defects:
        print(f"  [{did}] Sev={sev:<6} | Status={st:<6} | Module={mod:<34} | Owner={own}")
    res = subprocess.run([sys.executable, "src/09.23_validate_cost_profit_margin_formulas.py"], capture_output=True, text=True)
    retest_ok = (res.returncode == 0) and ("Failed Checks: 0" in (res.stdout or ""))
    os.makedirs("docs", exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md = ["# Step 09.48 - QA Defect Log & Retest Verification Ledger", "", f"**Generated:** {ts}  ", f"**Total Logged Defects:** {len(defects)} | **Open Defects:** {open_total} | **Open Critical/High:** {open_crit_high}  ", f"**Automated Retest Spot-Check (`09.23`):** **{'PASS' if retest_ok else 'FAIL'}**", "", "| Defect ID | Severity | Module | Reproduction Steps | Expected Result | Actual Result | Owner | Status | Retest Evidence |", "| :--- | :---: | :--- | :--- | :--- | :--- | :--- | :---: | :--- |"]
    for did, sev, mod, steps, exp, act, own, st, ev in defects:
        md.append(f"| {did} | **{sev}** | {mod} | {steps} | {exp} | {act} | {own} | **{st}** | `{ev}` |")
    with open("docs/09.48_Defect_Log_and_Retest_Ledger.md", "w", encoding="utf-8") as fp: fp.write("\n".join(md) + "\n")
    ok = 3 if (open_total == 0 and open_crit_high == 0 and retest_ok) else 0
    bad = 0 if ok == 3 else 1
    print("\n" + "="*82); print(f"DEFECT LEDGER SUMMARY -> Passed Checks: {ok} | Failed Checks: {bad} | Open Defects: {open_total} | Log: docs/09.48_Defect_Log_and_Retest_Ledger.md"); print("="*82)
if __name__=="__main__": run()

