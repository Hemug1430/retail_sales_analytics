# Document 06 - Power BI Dashboard & Security: Implementation Status

This file summarises how the repository implements the Power BI requirements in the source
requirements document (`06_PowerBI_Dashboard_Report_Requirements`). Status values are taken from
the repository contents (`dashboards/*.pbix`, `sql/07.*`, `sql/08.*`, `src/09.30-09.41`).
Items marked **To verify in Power BI Desktop** are stored inside the compressed data model and
must be checked by opening the `.pbix`.

## 1. Page inventory (requirements section 17)

| # | Required page | In `.pbix` | Notes |
| :-: | :--- | :-: | :--- |
| 01 | Executive Dashboard | **Missing** | Tracker 08.01; README lists it, the file does not contain it |
| 02 | Sales Performance | Present | Page "Sales Analysis" (drill-through type) |
| 03 | Product & Profitability | **Missing** | Tracker 08.03 |
| 04 | Store & Region Performance | Present | |
| 05 | Customer Analytics | Present | |
| 06 | Returns & Refunds | Present | |
| 07 | Target Performance | Present | |
| 08 | Transaction Detail | Present | Drill-through page |
| 09 | Definitions & Help | Present | |
| - | Tooltip page | Present | "Tooltip Card" |

## 2. Model and measures

| Area (requirements section) | Evidence | Status |
| :--- | :--- | :--- |
| Star schema and relationships (8-11) | `sql/07.04`-`07.13`, `src/09.30` | Scripted; **To verify in Power BI Desktop** |
| Date table and hierarchies (12-13) | `sql/06.01`, `07.11`, `07.14`-`07.16` | Scripted |
| DAX measure catalogue (14-15) | `sql/07.17`-`07.34` | Short descriptive scripts only; **export the final DAX into this repo** |
| KPI cards (16) | `sql/08.10` | 6 card visuals in the file |
| Filters, sorting, Top-N (27-28) | `sql/08.14`-`08.17`, `08.25` | 2 slicers in the file; review against requirements |
| Drill-down / drill-through (29-30) | `sql/08.18`-`08.19` | Drill-through pages exist |
| Tooltips (31) | `sql/08.20`, tooltip page | Page exists; no automated test (tracker 09.37) |
| Bookmarks, buttons, navigation (32) | `sql/08.21`-`08.23` | 2 bookmarks, 4 action buttons, 1 page navigator |
| Conditional formatting, dynamic titles (33) | `sql/08.24`, `08.26`, `07.34_07.35` | **To verify in Power BI Desktop** |

## 3. Row-Level Security (requirements section 34)

Required roles: Executive/Admin, Regional Manager, Store Manager, Analyst, preferably dynamic RLS with a
user-to-region/store mapping table.

- Roles and DAX filters live inside the data model; they are **not yet documented in this repository**.
- Action: list each role and its filter expression here, and record a "View as role" test result for each.
- RLS does not replace database security: the pipeline reads credentials from `.env` only (`src/config.py`).

## 4. Acceptance criteria (requirements section 38)

| Area | Status |
| :--- | :--- |
| Model | Scripted; verify in Desktop |
| Measures | Reconcile to MySQL after the full data load |
| Executive dashboard | **Open** - page missing |
| Reports | 5 of 7 analysis pages present (Product & Profitability missing) |
| Drill / filters | Present; verify against the specification |
| Returns, growth, security | Verify after full data load; document RLS roles |
| Refresh | `sql/07.37`; test against the full load |

Figures (row counts, revenue) are intentionally not repeated here; see `docs/10.02_Final_Reconciliation_Certificate.md`.
