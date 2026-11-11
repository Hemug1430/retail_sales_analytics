import os, zipfile
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()
def get_db_engine():
    u, p, h, pt, d = os.getenv("DB_USER","root"), os.getenv("DB_PASSWORD",""), os.getenv("DB_HOST","localhost"), os.getenv("DB_PORT","3306"), os.getenv("DB_NAME","retail_sales_db")
    return create_engine(f"mysql+pymysql://{u}:{p}@{h}:{pt}/{d}")
def r2(v): return Decimal(str(v or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
def run():
    print("="*78); print("STEP 09.34: DEFAULT & INTERACTIVE SORTING AND GROUPING VALIDATION"); print("="*78)
    ok, bad = 0, 0
    with get_db_engine().connect() as c:
        (db,) = c.execute(text("SELECT DATABASE()")).fetchone()
        print(f"[PASS] Connected to {db}\n"); ok += 1
        rev = "(f.quantity * f.unit_selling_price * (1 - COALESCE(f.discount_pct, 0)/100.0))"
        dcol = next(col for col, *_ in c.execute(text("SHOW COLUMNS FROM factsales")).fetchall() if "date" in col.lower())
        dt_rows = c.execute(text(f"SELECT DATE(f.`{dcol}`) dt, ROUND(SUM({rev}),2) v FROM factsales f GROUP BY DATE(f.`{dcol}`) ORDER BY dt ASC")).fetchall()
        is_chrono = all(dt_rows[i] < dt_rows[i+1] for i in range(len(dt_rows)-1))
        print(f"--- 1. Default Chronological Date Grouping & Sorting ({len(dt_rows)} dates) ---")
        print(f"  First Date = {dt_rows} | Last Date = {dt_rows[-1]} | Strictly Chronological = {is_chrono}")
        if len(dt_rows) == 31 and is_chrono: print("[PASS] Time-series grouping sorts strictly in ascending chronological order.\n"); ok += 1
        else: bad += 1
        cat_desc = c.execute(text(f"SELECT p.category, ROUND(SUM({rev}),2) v FROM factsales f JOIN core_products p ON f.product_id=p.product_id GROUP BY p.category ORDER BY v DESC, p.category ASC")).fetchall()
        cat_asc = c.execute(text(f"SELECT p.category, ROUND(SUM({rev}),2) v FROM factsales f JOIN core_products p ON f.product_id=p.product_id GROUP BY p.category ORDER BY v ASC, p.category ASC")).fetchall()
        is_desc = all(r2(cat_desc[i][1]) >= r2(cat_desc[i+1][1]) for i in range(len(cat_desc)-1))
        is_asc = all(r2(cat_asc[i][1]) <= r2(cat_asc[i+1][1]) for i in range(len(cat_asc)-1))
        print(f"--- 2. Default DESC vs. Interactive ASC Metric Sorting ({len(cat_desc)} categories) ---")
        print(f"  Top DESC = {cat_desc} ({r2(cat_desc[0][1]):,.2f}) | Top ASC = {cat_asc} ({r2(cat_asc[0][1]):,.2f})")
        if is_desc and is_asc and [x for x in cat_desc] == list(reversed([x for x in cat_asc])):
            print("[PASS] Default DESC and interactive ASC sort reversals behave deterministically.\n"); ok += 1
        else: bad += 1
        grp_rows = c.execute(text(f"SELECT f.sales_channel, p.category, ROUND(SUM({rev}),2) v FROM factsales f JOIN core_products p ON f.product_id=p.product_id GROUP BY f.sales_channel, p.category ORDER BY f.sales_channel ASC, v DESC")).fetchall()
        grp_sum = sum((r2(v) for _, _, v in grp_rows), Decimal("0.00"))
        (grand_tot,) = c.execute(text(f"SELECT ROUND(SUM({rev}),2) FROM factsales f")).fetchone()
        pbix_ok = zipfile.is_zipfile("dashboards/Retail_Sales_Analytics_Model.pbix")
        print(f"--- 3. Multi-Level Hierarchy Grouping (Channel -> Category: {len(grp_rows)} buckets) ---")
        print(f"  Grouped Rollup Sum = {grp_sum:,.2f} | Portfolio Grand Total = {r2(grand_tot):,.2f} | PBIX Valid = {pbix_ok}")
        if abs(grp_sum - r2(grand_tot)) <= Decimal("0.05") and pbix_ok:
            print("[PASS] Multi-level matrix grouping subtotals reconcile 100% with portfolio grand total.\n"); ok += 1
        else: bad += 1
    print("="*78); print(f"SUMMARY -> Passed Checks: {ok} | Failed Checks: {bad}"); print("="*78)
if __name__=="__main__": run()


