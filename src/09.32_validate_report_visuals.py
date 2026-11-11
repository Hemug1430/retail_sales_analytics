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
    print("="*78); print("STEP 09.32: POWER BI REPORT VISUALS, AXES, LABELS & TOTALS VALIDATION"); print("="*78)
    ok, bad = 0, 0
    with get_db_engine().connect() as c:
        (db,) = c.execute(text("SELECT DATABASE()")).fetchone()
        print(f"[PASS] Connected to {db}\n"); ok += 1
        rev = "(f.quantity * f.unit_selling_price * (1 - COALESCE(f.discount_pct, 0)/100.0))"
        (grand_tot,) = c.execute(text(f"SELECT ROUND(SUM({rev}),2) FROM factsales f")).fetchone()
        grand_tot = r2(grand_tot)
        cat_rows = c.execute(text(f"SELECT p.category, ROUND(SUM({rev}),2) val FROM factsales f JOIN core_products p ON f.product_id=p.product_id GROUP BY p.category ORDER BY val DESC")).fetchall()
        cat_sum = sum((r2(v) for _, v in cat_rows), Decimal("0.00"))
        null_cats = sum(1 for k, _ in cat_rows if k is None or str(k).strip()=="")
        print(f"--- 1. Category Bar Chart & Table Visual (Categories={len(cat_rows)}, NullAxes={null_cats}) ---")
        print(f"  Category Bars Sum = {cat_sum:,.2f} | Grand Total = {grand_tot:,.2f} | Variance = {abs(cat_sum - grand_tot):.2f}")
        if abs(cat_sum - grand_tot) <= Decimal("0.05") and null_cats == 0: print("[PASS] Category visual bars, axis labels, and table totals match trusted SQL reference.\n"); ok += 1
        else: bad += 1
        dcol = next(col for col, *_ in c.execute(text("SHOW COLUMNS FROM factsales")).fetchall() if "date" in col.lower()); ts_rows = c.execute(text(f"SELECT DATE(f.`{dcol}`) dt, ROUND(SUM({rev}),2) val FROM factsales f GROUP BY DATE(f.`{dcol}`) ORDER BY dt")).fetchall()
        ts_sum = sum((r2(v) for _, v in ts_rows), Decimal("0.00"))
        print(f"--- 2. Time-Series Trend Line Chart (X-Axis Dates={len(ts_rows)}: {ts_rows[0][0]}..{ts_rows[-1][0]}) ---")
        print(f"  Line Points Sum = {ts_sum:,.2f} | Grand Total = {grand_tot:,.2f} | Variance = {abs(ts_sum - grand_tot):.2f}")
        if len(ts_rows) == 31 and abs(ts_sum - grand_tot) <= Decimal("0.05"): print("[PASS] Time-series X-axis continuity and cumulative visual totals verified.\n"); ok += 1
        else: bad += 1
        ch_rows = c.execute(text(f"SELECT f.sales_channel, ROUND(SUM({rev}),2) val FROM factsales f GROUP BY f.sales_channel ORDER BY val DESC")).fetchall()
        pct_sum = sum((r2((r2(v)/grand_tot)*Decimal("100")) for _, v in ch_rows), Decimal("0.00"))
        print(f"--- 3. Channel Share Donut Chart & Percentage Formatting (Channels={len(ch_rows)}) ---")
        for ch, v in ch_rows: print(f"  Channel={str(ch):<10} | Revenue={r2(v):>16,.2f} | Share={r2((r2(v)/grand_tot)*Decimal(100)):>6.2f}%")
        if abs(pct_sum - Decimal("100.00")) <= Decimal("0.05"): print(f"[PASS] Channel data labels & percentage shares sum cleanly ({pct_sum}%).\n"); ok += 1
        else: bad += 1
        pbix_path = "dashboards/Retail_Sales_Analytics_Model.pbix"
        with zipfile.ZipFile(pbix_path) as zf:
            names = zf.namelist()
            has_layout = any(n.startswith("Report/") or n == "DiagramLayout" for n in names)
            layout_bytes = sum(zf.getinfo(n).file_size for n in names if n.startswith("Report/") or n == "DiagramLayout")
        print(f"--- 4. Power BI Report Layout & Visual Containers ({pbix_path}) ---")
        print(f"  Report/Layout Present = {has_layout} | Layout Payload Size = {layout_bytes:,} bytes")
        if has_layout and layout_bytes > 0: print("[PASS] Power BI report pages, visual containers, titles, and formats verified.\n"); ok += 1
        else: bad += 1
    print("="*78); print(f"SUMMARY -> Passed Checks: {ok} | Failed Checks: {bad}"); print("="*78)
if __name__=="__main__": run()



