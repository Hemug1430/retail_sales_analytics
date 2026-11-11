# Retail Sales Analytics Platform (`v1.0.0-PROD`)

An end-to-end **Enterprise Retail Data Engineering, MySQL Star-Schema Warehouse, Automated QA Suite, and Power BI Executive Analytics** solution built with **Python 3.12**, **MySQL 8**, **SQLAlchemy**, and **Power BI**.

---

## Executive Production Metrics (`v1.0.0-PROD`)

| Metric | Verified Production Baseline | Reconciliation Status |
| :--- | :---: | :---: |
| **Eligible Sales Transactions (`factsales`)** | `34,581` orders | `0.00` variance across Source, Staging, Core & BI |
| **Gross / Net Sales Revenue** | `1,701,953,364.69` | Verified across Python, MySQL & DAX (`10.02`) |
| **Verified Returns & Refunds (`factreturns`)** | `14,795,682.85` | Reconciled across `factreturns` & Power BI |
| **Net Revenue After Returns** | `1,687,157,681.84` | Audited & certified (`docs/10.02_Final_Reconciliation_Certificate.md`) |
| **Automated QA & Regression Coverage** | `50` QA modules (`44/44` suites passing) | `0` open defects (`docs/09.48_Defect_Log_and_Retest_Ledger.md`) |
| **Security & Reproducibility Audits** | `0` embedded secrets / `3/3` rebuild gates | Certified (`10.13` & `10.14`) |

---

## Architecture & Pipeline Workflow

1. **Automated Ingestion & File Routing (`src/`):** Discovers incoming CSV drops (`data/incoming/`), computes SHA-256 file hashes to block duplicate file reloads, validates schemas against evolution rules, and quarantines malformed rows into `data/rejected/`.
2. **Standardization & Idempotent ETL (`src/` & `sql/`):** Cleans text, dates, currencies, nulls, and category mappings; enforces Slowly Changing Dimension (SCD) history on master dimensions (`core_customers`, `core_products`, `core_stores`); and upserts incremental batches into `retail_sales_db` with full audit logging in `pipeline_execution_logs`.
3. **Analytical Layer & Star Schema (`sql/`):** Exposes reconciled dimensional views (`analytics_derived_store_summary`, `analytics_derived_product_summary`, `vw_monthly_targets_realization`) supporting MTD/QTD/YTD time intelligence, customer segmentation, and target variance tracking.
4. **Power BI Executive Reporting (`dashboards/`):** Interactive multi-page Power BI model (`Retail_Sales_Analytics_Model_v1.0.0-PROD.pbix`) featuring Executive Overview, Sales & Channel Analysis, Product Profitability, Store & Region Performance, Customer Insights, Actual vs. Target tracking, Drill-Through Transaction Detail, Report-Page Tooltips, Bookmarks, and Row-Level Security (RLS).

---

## Repository Structure

```text
retail_sales_analytics/
├── src/                  # Ingestion, cleaning, ETL, QA (09.01-09.51) & Release scripts (10.01-10.15)
├── sql/                  # MySQL DDL schemas, merge procedures, analytical views & QA queries
├── dashboards/           # Active & frozen release Power BI files (Retail_Sales_Analytics_Model_v1.0.0-PROD.pbix)
├── docs/                 # SOP Runbook, Handover Checklist, User Guide, Manifests & Sign-Off Certificates
├── tests/                # Unit and integration test suites
├── requirements.txt      # Pinned Python runtime dependencies
└── README.Md             # Project overview and quickstart guide
```

---

## Quickstart & Operations

1. **Configure Environment:** Create a local `.env` file with `DB_HOST`, `DB_PORT`, `DB_NAME=retail_sales_db`, `DB_USER`, and `DB_PASSWORD` (excluded from Git via `.gitignore`).
2. **Install Dependencies:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
3. **Run End-to-End Pipeline & Reconciliation Gate:**
   ```powershell
   .\.venv\Scripts\python.exe src/10.01_run_final_e2e_execution.py
   .\.venv\Scripts\python.exe src/10.02_confirm_final_reconciliation.py
   ```
4. **Operational Documentation (`docs/`):**
   - **Operational Runbook (SOP):** `docs/10.08_Operational_Runbook_SOP_v1.0.0.md`
   - **Production Handover Checklist:** `docs/10.09_Production_Handover_Checklist_v1.0.0.md`
   - **Power BI End-User Guide:** `docs/10.10_PowerBI_User_Guide_v1.0.0.md`
   - **Project Closure Sign-Off:** `docs/10.15_Project_Closure_Report_v1.0.0.md`
