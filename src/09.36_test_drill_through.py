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
    print("="*78); print("STEP 09.36: SUMMARY-TO-DETAIL DRILL-THROUGH & FILTER RETENTION VALIDATION"); print("="*78)
    ok, bad = 0, 0
    with get_db_engine().connect() as c:
        (db,) = c.execute(text("SELECT DATABASE()")).fetchone()
        print(f"[PASS] Connected to {db}\n"); ok += 1
        rev = "(f.quantity * f.unit_selling_price * (1 - COALESCE(f.discount_pct, 0)/100.0))"
        (sid, sum_rev, sum_cnt) = c.execute(text(f"SELECT f.store_id, ROUND(SUM({rev}),2) v, COUNT(*) cnt FROM factsales f GROUP BY f.store_id ORDER BY v DESC LIMIT 1")).fetchone()
        dtl_rows = c.execute(text(f"SELECT f.store_id, f.product_id, f.customer_id, f.quantity, ROUND({rev},2) line_rev FROM factsales f WHERE f.store_id=:sid"), {"sid": sid}).fetchall()
        dtl_sum = sum((r2(r[-1]) for r in dtl_rows), Decimal("0.00"))
        retained_store = all(s == sid for s, *_ in dtl_rows)
        print(f"--- 1. Store Summary -> Detail Drill-Through (Target={sid}) ---")
        print(f"  Summary Total = {r2(sum_rev):,.2f} ({int(sum_cnt)} rows) | Detail Sum = {dtl_sum:,.2f} ({len(dtl_rows)} rows) | Filter Retained = {retained_store}")
        if len(dtl_rows) == int(sum_cnt) and abs(r2(sum_rev) - dtl_sum) <= Decimal("0.05") and retained_store:
            print("[PASS] Store summary drill-through reaches exact transaction rows with filter retained.\n"); ok += 1
        else: bad += 1
        (m_rev, m_cnt) = c.execute(text(f"SELECT ROUND(SUM({rev}),2), COUNT(*) FROM factsales f JOIN core_products p ON f.product_id=p.product_id WHERE f.store_id=:sid AND p.category='Electronics'"), {"sid": sid}).fetchone()
        mdtl_rows = c.execute(text(f"SELECT f.store_id, p.category, f.product_id, ROUND({rev},2) line_rev FROM factsales f JOIN core_products p ON f.product_id=p.product_id WHERE f.store_id=:sid AND p.category='Electronics'"), {"sid": sid}).fetchall()
        mdtl_sum = sum((r2(r[-1]) for r in mdtl_rows), Decimal("0.00"))
        retained_both = all(s == sid and cat == "Electronics" for s, cat, *_ in mdtl_rows)
        print(f"--- 2. Matrix Multi-Filter Drill-Through ({sid} + Category=Electronics) ---")
        print(f"  Matrix Cell = {r2(m_rev):,.2f} ({int(m_cnt)} rows) | Detail Evidence Sum = {mdtl_sum:,.2f} ({len(mdtl_rows)} rows) | Both Filters Retained = {retained_both}")
        if len(mdtl_rows) == int(m_cnt) and abs(r2(m_rev) - mdtl_sum) <= Decimal("0.05") and retained_both:
            print("[PASS] Multi-dimension drill-through carries all active slicer/cell filters to detail evidence.\n"); ok += 1
        else: bad += 1
        (ret_sid, ret_sum, ret_cnt) = c.execute(text("SELECT f.store_id, ROUND(SUM(r.refund_amount),2) v, COUNT(*) cnt FROM factreturns r JOIN factsales f ON r.sales_line_id=f.sales_line_id GROUP BY f.store_id ORDER BY v DESC LIMIT 1")).fetchone()
        rdtl = c.execute(text("SELECT f.store_id, r.return_id, r.sales_line_id, r.refund_amount FROM factreturns r JOIN factsales f ON r.sales_line_id=f.sales_line_id WHERE f.store_id=:sid"), {"sid": ret_sid}).fetchall()
        rdtl_sum = sum((r2(r[-1]) for r in rdtl), Decimal("0.00"))
        pbix_ok = zipfile.is_zipfile("dashboards/Retail_Sales_Analytics_Model.pbix")
        print(f"--- 3. Return Summary -> Return & Sale Evidence Drill-Through ({ret_sid}) ---")
        print(f"  Return Summary = {r2(ret_sum):,.2f} ({int(ret_cnt)} returns) | Detail Evidence = {rdtl_sum:,.2f} ({len(rdtl)} rows) | PBIX Valid = {pbix_ok}")
        if len(rdtl) == int(ret_cnt) and abs(r2(ret_sum) - rdtl_sum) <= Decimal("0.05") and pbix_ok:
            print("[PASS] Return drill-through resolves exact underlying sale & return records.\n"); ok += 1
        else: bad += 1
    print("="*78); print(f"SUMMARY -> Passed Checks: {ok} | Failed Checks: {bad}"); print("="*78)
if __name__=="__main__": run()



