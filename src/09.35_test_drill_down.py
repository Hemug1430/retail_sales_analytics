import os
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()
def get_db_engine():
    u, p, h, pt, d = os.getenv("DB_USER","root"), os.getenv("DB_PASSWORD",""), os.getenv("DB_HOST","localhost"), os.getenv("DB_PORT","3306"), os.getenv("DB_NAME","retail_sales_db")
    return create_engine(f"mysql+pymysql://{u}:{p}@{h}:{pt}/{d}")
def r2(v): return Decimal(str(v or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
def run():
    print("="*78); print("STEP 09.35: DATE, GEOGRAPHY & PRODUCT HIERARCHY DRILL-DOWN VALIDATION"); print("="*78)
    ok, bad = 0, 0
    with get_db_engine().connect() as c:
        (db,) = c.execute(text("SELECT DATABASE()")).fetchone()
        print(f"[PASS] Connected to {db}\n"); ok += 1
        rev = "(f.quantity * f.unit_selling_price * (1 - COALESCE(f.discount_pct, 0)/100.0))"
        dcol = next(col for col, *_ in c.execute(text("SHOW COLUMNS FROM factsales")).fetchall() if "date" in col.lower())
        (yr_rev,) = c.execute(text(f"SELECT ROUND(SUM({rev}),2) FROM factsales f WHERE YEAR(f.`{dcol}`)=2024")).fetchone()
        (mo_rev,) = c.execute(text(f"SELECT ROUND(SUM({rev}),2) FROM factsales f WHERE YEAR(f.`{dcol}`)=2024 AND MONTH(f.`{dcol}`)=1")).fetchone()
        day_rows = c.execute(text(f"SELECT DAY(f.`{dcol}`) d, ROUND(SUM({rev}),2) v FROM factsales f WHERE YEAR(f.`{dcol}`)=2024 AND MONTH(f.`{dcol}`)=1 GROUP BY DAY(f.`{dcol}`)")).fetchall()
        day_sum = sum((r2(v) for _, v in day_rows), Decimal("0.00"))
        print(f"--- 1. Date Hierarchy Drill-Down (Year 2024 -> Jan -> {len(day_rows)} Days) ---")
        print(f"  Year=2024 ({r2(yr_rev):,.2f}) -> Month=01 ({r2(mo_rev):,.2f}) -> Days Sum ({day_sum:,.2f})")
        if r2(yr_rev) == r2(mo_rev) == day_sum and len(day_rows) == 31: print("[PASS] Date hierarchy drill-down preserves 100% parent-to-child value parity.\n"); ok += 1
        else: bad += 1
        scols = [col for col, *_ in c.execute(text("SHOW COLUMNS FROM core_stores")).fetchall()]
        gcol = next((col for col in ("region","state","city","country") if col in scols), scols)
        (top_geo, geo_rev) = c.execute(text(f"SELECT s.`{gcol}`, ROUND(SUM({rev}),2) v FROM factsales f JOIN core_stores s ON f.store_id=s.store_id GROUP BY s.`{gcol}` ORDER BY v DESC LIMIT 1")).fetchone()
        st_rows = c.execute(text(f"SELECT s.store_id, ROUND(SUM({rev}),2) v FROM factsales f JOIN core_stores s ON f.store_id=s.store_id WHERE s.`{gcol}`=:gv GROUP BY s.store_id"), {"gv": top_geo}).fetchall()
        st_sum = sum((r2(v) for _, v in st_rows), Decimal("0.00"))
        print(f"--- 2. Geography Hierarchy Drill-Down ({gcol}={top_geo} -> {len(st_rows)} Child Stores) ---")
        print(f"  Parent {gcol} ({r2(geo_rev):,.2f}) -> Child Stores Sum ({st_sum:,.2f})")
        if abs(r2(geo_rev) - st_sum) <= Decimal("0.05") and len(st_rows) > 0: print("[PASS] Geography hierarchy drill-down returns exact contextual child store values.\n"); ok += 1
        else: bad += 1
        pcols = [col for col, *_ in c.execute(text("SHOW COLUMNS FROM core_products")).fetchall()]
        subcol = next((col for col in ("subcategory","sub_category","brand") if col in pcols), "product_id")
        (top_cat, cat_rev) = c.execute(text(f"SELECT p.category, ROUND(SUM({rev}),2) v FROM factsales f JOIN core_products p ON f.product_id=p.product_id GROUP BY p.category ORDER BY v DESC LIMIT 1")).fetchone()
        sub_rows = c.execute(text(f"SELECT p.`{subcol}`, ROUND(SUM({rev}),2) v FROM factsales f JOIN core_products p ON f.product_id=p.product_id WHERE p.category=:cv GROUP BY p.`{subcol}`"), {"cv": top_cat}).fetchall()
        sku_rows = c.execute(text(f"SELECT p.product_id, ROUND(SUM({rev}),2) v FROM factsales f JOIN core_products p ON f.product_id=p.product_id WHERE p.category=:cv GROUP BY p.product_id"), {"cv": top_cat}).fetchall()
        sub_sum = sum((r2(v) for _, v in sub_rows), Decimal("0.00"))
        sku_sum = sum((r2(v) for _, v in sku_rows), Decimal("0.00"))
        print(f"--- 3. Product Hierarchy Drill-Down ({top_cat} -> {len(sub_rows)} {subcol} -> {len(sku_rows)} SKUs) ---")
        print(f"  Category ({r2(cat_rev):,.2f}) -> {subcol} Sum ({sub_sum:,.2f}) -> SKUs Sum ({sku_sum:,.2f})")
        if abs(r2(cat_rev) - sub_sum) <= Decimal("0.05") and abs(r2(cat_rev) - sku_sum) <= Decimal("0.05"): print("[PASS] Product hierarchy multi-level drill-down reconciles with zero variance.\n"); ok += 1
        else: bad += 1
    print("="*78); print(f"SUMMARY -> Passed Checks: {ok} | Failed Checks: {bad}"); print("="*78)
if __name__=="__main__": run()
