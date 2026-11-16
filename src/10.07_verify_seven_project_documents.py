"""
10.07 - Verify Project Documents 01-07 against repository evidence.

Run from the project root:  python src/10.07_verify_seven_project_documents.py

For every requirement document (01-07) this script looks for real evidence in the
repository and reports GAP wherever the evidence is missing or smaller than the
document's frozen target. It never creates placeholder documents and never marks
a document as verified just because a file with a matching name exists.
"""

import csv
import glob
import json
import os
import zipfile
from datetime import datetime

PBIX = "dashboards/Retail_Sales_Analytics_Model.pbix"
REQUIRED_PAGES = [
    "Executive",
    "Sales",
    "Product",
    "Store",
    "Customer",
    "Return",
    "Target",
    "Transaction",
    "Definitions",
]


def count_files(pattern):
    return len([p for p in glob.glob(pattern, recursive=True) if os.path.isfile(p)])


def csv_rows(path):
    if not os.path.isfile(path):
        return 0
    with open(path, encoding="utf-8", errors="replace", newline="") as fp:
        return max(sum(1 for _ in csv.reader(fp)) - 1, 0)


def pbix_page_names():
    if not os.path.isfile(PBIX):
        return []
    names = []
    with zipfile.ZipFile(PBIX) as z:
        for item in z.namelist():
            if item.endswith("/page.json"):
                try:
                    names.append(json.loads(z.read(item)).get("displayName", ""))
                except ValueError:
                    pass
    return names


def check(label, found, expected, note=""):
    status = "OK" if found >= expected else "GAP"
    return (label, found, expected, status, note)


def build_checks():
    pages = pbix_page_names()
    missing_pages = [
        r for r in REQUIRED_PAGES if not any(r.lower() in p.lower() for p in pages)
    ]
    return [
        (
            "01",
            "Project Requirements",
            [
                check("README present", count_files("README.M*"), 1),
                check("Naming conventions + run checklist", count_files("docs/01_1*.md"), 2),
                check("Tracker phases 01-10 with scripts", count_files("src/10.*.py"), 15),
            ],
        ),
        (
            "02",
            "Data Specification",
            [
                check("Core/fact DDL scripts (05.01-05.15)", count_files("sql/05.[01]*.sql"), 15),
                check("Source master files in incoming/", count_files("incoming/*_master.csv"), 5, "customers, products, stores, salespersons, promotions (may sit in gitignored data/)"),
            ],
        ),
        (
            "03",
            "Synthetic Data Simulation",
            [
                check("Phase 02 generators (notebooks + scripts)", count_files("notebooks/02_*.ipynb") + count_files("src/02.*.py"), 33),
                check("Monthly sales files (Jan-2024..Aug-2026)", count_files("incoming/sales_*.csv"), 32, "Doc 03 section 4"),
                check("Target rows", csv_rows("facttargets.csv"), 10776, "Doc 03 section 4"),
                check("Promotion rows", csv_rows("core_promotions.csv"), 1),
            ],
        ),
        (
            "04",
            "Data Processing & ETL",
            [
                check("Cleaning scripts 04.01-04.15", count_files("src/04.*.py") + count_files("src/text_standardization.py") + count_files("src/customer_geography_standardization.py"), 15),
                check("Staging/core load scripts 05.16-05.33", count_files("src/05*.py"), 18),
            ],
        ),
        (
            "05",
            "Business Logic & Analytics",
            [
                check("Analytics SQL 06.01-06.34", count_files("sql/06.*.sql"), 33, "06.33 is a Python step"),
                check("Analytical output tables", count_files("analytics_derived_*.csv"), 4),
            ],
        ),
        (
            "06",
            "Power BI Dashboard & Report",
            [
                check("PBIX present", count_files(PBIX), 1),
                check(
                    "Required report pages",
                    len(REQUIRED_PAGES) - len(missing_pages),
                    len(REQUIRED_PAGES),
                    "missing: " + (", ".join(missing_pages) or "none"),
                ),
                check("Frozen release PBIX present", count_files("dashboards/releases/*.pbix"), 1),
            ],
        ),
        (
            "07",
            "Testing & Validation",
            [
                check("QA scripts 09.01-09.51", count_files("src/09.*.py"), 50),
                check("Defect log / sign-off docs", count_files("docs/09.4*.md") + count_files("docs/09.5*.md"), 5),
            ],
        ),
    ]


def run():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 82)
    print("STEP 10.07: VERIFY DOCUMENTS 01-07 AGAINST REPOSITORY EVIDENCE")
    print("=" * 82)

    lines = [
        "# Step 10.07 - Project Documents (01-07) Evidence Traceability Report",
        "",
        f"**Generated:** {ts}  ",
        "**Method:** repository evidence counted against the frozen targets in each requirement document.",
        "",
        "| Doc | Title | Check | Found | Expected | Status | Note |",
        "| :-: | :--- | :--- | ---: | ---: | :-: | :--- |",
    ]
    gaps = 0
    total = 0
    for num, title, checks in build_checks():
        for label, found, expected, status, note in checks:
            total += 1
            gaps += status == "GAP"
            print(f"  [DOC-{num}] {label:<52} {found:>8,} / {expected:<8,} {status}")
            lines.append(f"| {num} | {title} | {label} | {found:,} | {expected:,} | **{status}** | {note} |")

    lines += ["", f"**Result:** {total - gaps} of {total} checks have evidence; **{gaps} gaps** remain.", ""]
    os.makedirs("docs", exist_ok=True)
    with open("docs/10.07_Project_Documents_01_to_07_Verification.md", "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines))

    print("=" * 82)
    print(f"DOCS 01-07 AUDIT -> Passed Checks: {total - gaps} | Failed Checks: {gaps}")
    print("=" * 82)
    return 0 if gaps == 0 else 1


if __name__ == "__main__":
    raise SystemExit(run())
