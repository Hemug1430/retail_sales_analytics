import os
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()
def get_db_engine():
    u, p, h, pt, d = os.getenv("DB_USER","root"), os.getenv("DB_PASSWORD",""), os.getenv("DB_HOST","localhost"), os.getenv("DB_PORT","3306"), os.getenv("DB_NAME","retail_sales_db")
    return create_engine(f"mysql+pymysql://{u}:{p}@{h}:{pt}/{d}")
def round2(v): return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
def dax_rankx(items):
    s = sorted(items, key=lambda x: x[1], reverse=True)
    r, rk, prev = {}, 0, None
    for k, v in s:
        if prev is None or v < prev: rk += 1; prev = v
        r[k] = rk
    return r
def run():
    print("="*78); print("STEP 09.28: SQL WINDOW RANKINGS VS. POWER BI DYNAMIC RANKX VALIDATION"); print("="*78)
    ok, bad = 0, 0
    with get_db_engine().connect() as c:
        (db,) = c.execute(text("SELECT DATABASE()")).fetchone()
        print(f"[PASS] Connected to {db}"); ok += 1
        rev = "(f.quantity * f.unit_selling_price * (1 - COALESCE(f.discount_pct, 0)/100.0))"
        st = c.execute(text(f"SELECT f.store_id, ROUND(SUM({rev}),2) r, DENSE_RANK() OVER (ORDER BY ROUND(SUM({rev}),2) DESC) rk FROM factsales f GROUP BY f.store_id ORDER BY rk")).fetchall()
        dr = dax_rankx([(str(a), round2(b)) for a,b,_ in st])
        m1 = sum(1 for a,_,rk in st if int(rk) != dr[str(a)])
        print(f"Context A (Unfiltered Stores): {len(st)} ranked, mismatches={m1}")
        if st and m1==0: print("[PASS] Unfiltered Store SQL DENSE_RANK == DAX RANKX"); ok += 1
        else: bad += 1
        (cat,) = c.execute(text(f"SELECT p.category FROM factsales f JOIN core_products p ON f.product_id=p.product_id GROUP BY p.category ORDER BY SUM({rev}) DESC LIMIT 1")).fetchone()
        pr = c.execute(text(f"SELECT f.product_id, ROUND(SUM({rev}),2) r, DENSE_RANK() OVER (ORDER BY ROUND(SUM({rev}),2) DESC) rk FROM factsales f JOIN core_products p ON f.product_id=p.product_id WHERE p.category=:cat GROUP BY f.product_id ORDER BY rk"), {"cat": cat}).fetchall()
        dpr = dax_rankx([(str(a), round2(b)) for a,b,_ in pr])
        m2 = sum(1 for a,_,rk in pr if int(rk) != dpr[str(a)])
        print(f"Context B (Category={cat}): {len(pr)} products ranked, mismatches={m2}")
        if pr and int(pr[0][2])==1 and m2==0: print("[PASS] Filtered Category SQL DENSE_RANK == DAX RANKX(ALLSELECTED)"); ok += 1
        else: bad += 1
        (ch,) = c.execute(text("SELECT sales_channel FROM factsales WHERE sales_channel IS NOT NULL GROUP BY sales_channel ORDER BY COUNT(*) DESC LIMIT 1")).fetchone()
        cs = c.execute(text(f"SELECT f.store_id, ROUND(SUM({rev}),2) r, DENSE_RANK() OVER (ORDER BY ROUND(SUM({rev}),2) DESC) rk FROM factsales f WHERE f.sales_channel=:ch GROUP BY f.store_id ORDER BY rk"), {"ch": ch}).fetchall()
        dcr = dax_rankx([(str(a), round2(b)) for a,b,_ in cs])
        m3 = sum(1 for a,_,rk in cs if int(rk) != dcr[str(a)])
        print(f"Context C (Channel={ch}): {len(cs)} stores ranked, mismatches={m3}")
        if cs and m3==0: print("[PASS] Channel-Sliced SQL DENSE_RANK == DAX RANKX"); ok += 1
        else: bad += 1
    print("="*78); print(f"SUMMARY -> Passed Checks: {ok} | Failed Checks: {bad}"); print("="*78)
if __name__=="__main__": run()
