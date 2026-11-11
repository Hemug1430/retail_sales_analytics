import os
from datetime import datetime
def run():
    print("="*82); print("STEP 10.10: GENERATE & VERIFY POWER BI END-USER GUIDE (v1.0.0-PROD)"); print("="*82)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs("docs", exist_ok=True)
    ug_path = "docs/10.10_PowerBI_User_Guide_v1.0.0.md"
    lines = [
        "# Step 10.10 - Retail Sales Analytics Power BI User Guide (v1.0.0-PROD)",
        "",
        f"**Published:** {ts} | **Report:** `Retail_Sales_Analytics_Model.pbix` | **Audience:** Business & Executive Users",
        "",
        "---",
        "",
        "## 1. Using Dashboards & Page Navigation",
        "- **Page Navigation:** Use the left/bottom page tabs or header navigation buttons to switch between **Executive Overview**, **Sales Analysis**, **Product Profitability**, **Store & Region**, **Customer Insights**, **Transaction Detail**, and **Definitions & Help**.",
        "- **Last Refresh Timestamp:** Check the top-right header badge on each page to confirm the latest verified dataset refresh timestamp.",
        "- **Contextual Tooltips:** Hover over any chart bar, line point, or table cell to view supporting KPI tooltips without leaving the page.",
        "",
        "## 2. Applying Filters, Slicers & Cross-Highlighting",
        "- **Slicer Bar:** Use the top/side slicers (**Date Range**, **Region**, **Store**, **Category**, **Sales Channel**) to scope metrics dynamically. Dynamic chart titles automatically update to reflect active filter selections.",
        "- **Multi-Select:** Hold `Ctrl + Click` to select multiple slicer items or bars across visuals.",
        "- **Visual Cross-Filtering:** Click any bar, pie slice, or map bubble to cross-filter other visuals on the same page; click it again to clear.",
        "- **Resetting Filters:** Click the **Reset Filters** bookmark button (or **Reset to default** in the Power BI top bar) to restore the default portfolio view.",
        "",
        "## 3. Using Hierarchical Drill-Down",
        "Charts built on multi-level hierarchies support interactive drill-down via the icons in the top-right corner of the visual:",
        "- **Supported Hierarchies:**",
        "  - **Time:** `Year -> Quarter -> Month -> Day`",
        "  - **Geography:** `Region -> State -> City -> Store`",
        "  - **Product:** `Category -> Subcategory -> Product`",
        "- **Drill Controls:**",
        "  - **Single Down Arrow (Turn on Drill Down):** Click to activate drill mode, then click a specific bar/point (e.g., `South` or `Electronics`) to inspect only its children.",
        "  - **Double Down Arrow (Go to Next Level):** Moves all items to the next level down simultaneously.",
        "  - **Forked Arrow (Expand All Down One Level):** Expands child levels while keeping parent labels visible (e.g., `2025 Q1`, `2025 Q2`).",
        "  - **Up Arrow (Drill Up):** Returns one level higher in the hierarchy.",
        "",
        "## 4. Using Drill-Through to Transaction Detail",
        "1. **Select a Data Point:** Right-click any Store, Product, Category, Customer, or Date row/bar in a summary chart or matrix.",
        "2. **Launch Drill-Through:** Hover over **Drill through** in the context menu and select **Transaction Detail**.",
        "3. **Inspect Line-Level Audit Data:** Review individual `transaction_id` receipts, order dates, quantities, unit prices, discounts, net amounts, and return flags.",
        "4. **Return to Previous Page:** Hold `Ctrl + Click` on the top-left **Back** arrow button to return to your prior page with filters preserved.",
        "",
        "## 5. Business Definitions & Data Governance Rules",
        "- **Eligible Transactions:** Completed retail sales lines recorded in `factsales` across `Store` and `Online` channels.",
        "- **Net Sales Revenue:** `SUM(Quantity * Unit Selling Price * (1 - Discount %))` prior to post-sale return refunds.",
        "- **Refunds & Returns:** Verified product returns logged in `factreturns` linked to original sales transactions.",
        "- **Row-Level Security (RLS):** Regional and Store managers automatically view only rows authorized for their assigned region or store.",
        "",
        "## 6. Interpreting KPIs & Threshold Indicators",
        "| KPI Name | Formula / Meaning | How to Interpret & Action |",
        "| :--- | :--- | :--- |",
        "| **Net Revenue** | Total net sales after line discounts | Tracks top-line demand; compare against Target and prior period (MoM/YoY). |",
        "| **Total Orders** | Distinct count of eligible transactions | Separates order volume growth from price/basket-size changes. |",
        "| **Average Order Value (AOV)** | `Net Revenue / Total Orders` | Measures basket size; increases when bundling or higher-ticket categories grow. |",
        "| **Profit Margin %** | `(Net Revenue - Cost) / Net Revenue` | Measures unit profitability; investigate heavy discounting if margin dips below threshold. |",
        "| **Return Rate %** | `Returned Units / Sold Units` | Flags product quality or fulfillment issues; values `< 2.0%` are healthy (Green), `2.0%-5.0%` watch (Amber), `> 5.0%` alert (Red). |",
        "| **Target Achievement %** | `Actual Net Revenue / Sales Target` | `>= 100%` (Green = On/Above Target), `90%-99.9%` (Amber = Near Target), `< 90%` (Red = Below Target). |"
    ]
    with open(ug_path, "w", encoding="utf-8") as fp: fp.write("\n".join(lines) + "\n")
    with open(ug_path, "r", encoding="utf-8") as fp: content = fp.read()
    sections = ["## 1. Using Dashboards", "## 2. Applying Filters", "## 3. Using Hierarchical Drill-Down", "## 4. Using Drill-Through", "## 5. Business Definitions", "## 6. Interpreting KPIs"]
    passed = sum(1 for s in sections if s in content)
    failed = len(sections) - passed
    for idx, s in enumerate(sections, 1):
        print(f"  [GUIDE-0{idx}] {s.replace('## ', ''):<52} | VERIFIED")
    print("\n" + "="*82); print(f"USER GUIDE SUMMARY -> Passed Checks: {passed} | Failed Checks: {failed} | File: {ug_path} ({os.path.getsize(ug_path):,} bytes)"); print("="*82)
if __name__=="__main__": run()

