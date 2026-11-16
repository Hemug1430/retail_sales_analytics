# Document 07 - QA Test Plan, Operations & Release Runbook: Implementation Status

Maps the test plan in the source requirements document (`07_Testing_Validation`) to the QA scripts in `src/09.*`.
A module listed here has an automated script. Whether a script passes against the full 32-month dataset has not
been shown yet because only January 2024 is loaded.

## 1. Test coverage map

| Requirements section | Area | Scripts |
| :--- | :--- | :--- |
| 5, 6-8 | Source files, schema, record volumes | `09.01`, `09.02`, `09.07` |
| 9-13 | Types, mandatory, domain, uniqueness, referential | `09.04`, `09.05` |
| 14-16 | Business rules, unit tests, cleaning | `09.06`-`09.09` |
| 17-24 | ETL, structure, incremental, correction, SCD, reject, logging | `09.10`-`09.18`, `09.20`, `09.42` |
| 25-26 | Row-count and financial reconciliation | `09.19`, `09.21`, `09.22`, `09.23` |
| 27-30 | Analytics, SQL, KPI, EDA | `09.24`-`09.29` |
| 31-36 | Power BI model, visuals, interactions, RLS, refresh | `09.30`-`09.41` |
| 36 | Performance | `09.43`-`09.45` |
| 37 | Regression, UAT, defects, sign-off | `09.46`-`09.51` |

Known gaps: no tooltip test script (tracker 09.37 has no matching file); `09.15` covers customer history only
until `05.27` is extended to products and stores.

## 2. Exit gates (requirements section 38)

| Gate | Condition | Status |
| :--- | :--- | :-: |
| Requirements traceability | Evidence for each requirement | `docs/10.07_Project_Documents_01_to_07_Verification.md` lists gaps |
| Source / data quality | All planted scenarios behave as designed | **Open** - only January 2024 loaded |
| ETL | Historical, incremental, duplicate-file, correction, schema-change | **Open** - needs full test files |
| Database | Keys, history, trusted grains, audit | Scripted |
| Reconciliation | No unexplained mismatch | **Open** - returns figures differ across documents; about 16,500 January rows unexplained |
| Analytics | KPIs validated independently | **Open** - margin, segments and tiers show no variation |
| Power BI | Model, pages, RLS, refresh | **Open** - two pages missing; RLS undocumented |
| Defects | No open Critical or High | See `docs/09.48_Defect_Log_and_Retest_Ledger.md` |
| UAT | Business reviewer approval | `docs/09.47_UAT_SignOff_Report.md` |
| Release package | Documents, scripts, PBIX, evidence versioned together | Source requirement documents should be added to `docs/requirements/` |

## 3. Operations

Run order, environment setup and the reconciliation gate are in `README.Md` and `docs/10.08_Operational_Runbook_SOP_v1.0.0.md`.
