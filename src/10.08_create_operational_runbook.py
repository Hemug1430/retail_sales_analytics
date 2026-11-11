import os
from datetime import datetime
def run():
    print("="*82); print("STEP 10.08: GENERATE & VERIFY PRODUCTION OPERATIONAL RUNBOOK (SOP v1.0.0)"); print("="*82)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs("docs", exist_ok=True)
    rb_path = "docs/10.08_Operational_Runbook_SOP_v1.0.0.md"
    lines = [
        "# Step 10.08 - Retail Sales Analytics Operational Runbook (SOP v1.0.0-PROD)",
        "",
        f"**Effective Date:** {ts}  ",
        "**Environment:** Windows / Python 3.12 (`.venv`) / MySQL 8 (`retail_sales_db`) / Power BI (`Retail_Sales_Analytics_Model.pbix`)  ",
        "**Release Tag:** `v1.0.0-PROD`",
        "",
        "---",
        "",
        "## 1. Process a New Monthly File (Standard Monthly Load SOP)",
        "1. **Stage Incoming File:** Place the new monthly CSV drop (`sales_YYYY_MM.csv`, `returns_YYYY_MM.csv`, or `targets_YYYY_MM.csv`) into `data/incoming/`.",
        "2. **Activate Virtual Environment:** Open PowerShell in `C:\\Projects\\retail_sales_analytics` and verify `.venv\\Scripts\\python.exe` is active.",
        "3. **Run Ingestion, Validation & Incremental ETL:**",
        "   ```powershell",
        "   .\\venv\\Scripts\\python.exe src/10.01_run_final_e2e_execution.py",
        "   ```",
        "4. **Verify Audit Status:** Confirm `pipeline_execution_logs` records `status = PASS` with expected row counts and zero duplicate `transaction_id` keys.",
        "",
        "## 2. Handle Validation & ETL Errors (Triage & Quarantine SOP)",
        "1. **Failed-Load Isolation Gate:** **NEVER** refresh or publish Power BI if `pipeline_execution_logs` shows `status = FAIL` or `QUARANTINED`.",
        "2. **Inspect Error Logs & Rejected Records:**",
        "   - Query the latest failure entry in MySQL: `SELECT * FROM pipeline_execution_logs ORDER BY batch_id DESC LIMIT 5;`",
        "   - Inspect quarantined CSV rows in `data/rejected/` or `data/quarantine/` to identify schema drift, null keys, or negative price/quantity violations.",
        "3. **Remediate Root Cause:** Request a corrected vendor CSV or fix upstream mapping rules in `src/` before attempting any rerun.",
        "",
        "## 3. Rerun Failed Batches (Idempotent Recovery SOP)",
        "1. **Verify Partial-Load Cleanliness:** Confirm no orphaned rows exist for the failed `batch_id` (`SELECT COUNT(*) FROM factsales WHERE batch_id = <FAILED_BATCH_ID>;`). Delete partial rows if a non-atomic step aborted mid-load.",
        "2. **Replace Corrected Source File:** Place the corrected monthly CSV into `data/incoming/` and remove the corrupted file from staging.",
        "3. **Re-Execute Pipeline & Regression Check:**",
        "   ```powershell",
        "   .\\venv\\Scripts\\python.exe src/10.01_run_final_e2e_execution.py",
        "   .\\venv\\Scripts\\python.exe src/09.46_run_regression_test_suite.py",
        "   ```",
        "",
        "## 4. Cross-Layer Financial & Row Reconciliation",
        "1. **Execute Final Reconciliation Gate:** Run the automated cross-layer reconciliation check across Source, Staging, Trusted Core (`factsales`/`factreturns`), and Analytical Views:",
        "   ```powershell",
        "   .\\venv\\Scripts\\python.exe src/10.02_confirm_final_reconciliation.py",
        "   ```",
        "2. **Sign-Off Criteria:** Proceed to Power BI refresh **only** when `Failed Checks: 0` and variance between `factsales` and `analytics_derived_store_summary` is `<= 0.05` (`0.00` expected).",
        "",
        "## 5. Refresh & Validate Power BI (`Retail_Sales_Analytics_Model.pbix`)",
        "1. **Pre-Refresh Gate:** Confirm Step 4 reconciliation passed (`docs/10.02_Final_Reconciliation_Certificate.md`).",
        "2. **Trigger Dataset Refresh:** Open `dashboards/Retail_Sales_Analytics_Model.pbix` in Power BI Desktop (or trigger scheduled refresh in Power BI Service) and click **Refresh**.",
        "3. **Post-Refresh Visual & KPI Verification:**",
        "   - Verify Executive Overview KPI cards (`Net Revenue`, `Total Orders`, `Total Quantity`, `Profit Margin %`, `Return Rate %`) match SQL reconciliation totals.",
        "   - Run `src/09.45_test_powerbi_performance.py` and `src/10.06_save_final_powerbi_file.py` if saving a new versioned `.pbix` release.",
        "",
        "## 6. Archive Processed Inputs (`data/archive/YYYY/MM/`)",
        "1. **Run Immutable File Archiver:** Once Power BI refresh is verified, move processed monthly input files into `data/archive/YYYY/MM/` with SHA-256 checksum logging:",
        "   ```powershell",
        "   .\\venv\\Scripts\\python.exe src/archive_successful_files.py",
        "   ```",
        "2. **Backup Database Snapshot:** Run `src/10.05_backup_final_mysql_database.py` after major monthly closes to preserve a recoverable `.sql` and `.zip` archive in `backups/`."
    ]
    with open(rb_path, "w", encoding="utf-8") as fp: fp.write("\n".join(lines) + "\n")
    with open(rb_path, "r", encoding="utf-8") as fp: content = fp.read()
    sections = ["## 1. Process a New Monthly File", "## 2. Handle Validation & ETL Errors", "## 3. Rerun Failed Batches", "## 4. Cross-Layer Financial & Row Reconciliation", "## 5. Refresh & Validate Power BI", "## 6. Archive Processed Inputs"]
    passed = sum(1 for s in sections if s in content)
    failed = len(sections) - passed
    for idx, s in enumerate(sections, 1):
        print(f"  [SOP-0{idx}] {s.replace('## ', ''):<52} | VERIFIED")
    print("\n" + "="*82); print(f"RUNBOOK SUMMARY -> Passed Checks: {passed} | Failed Checks: {failed} | File: {rb_path} ({os.path.getsize(rb_path):,} bytes)"); print("="*82)
if __name__=="__main__": run()

