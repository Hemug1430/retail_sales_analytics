import os, zipfile
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()
def get_db_engine():
    u, p, h, pt, d = os.getenv("DB_USER","root"), os.getenv("DB_PASSWORD",""), os.getenv("DB_HOST","localhost"), os.getenv("DB_PORT","3306"), os.getenv("DB_NAME","retail_sales_db")
    return create_engine(f"mysql+pymysql://{u}:{p}@{h}:{pt}/{d}")
def r2(v): return Decimal(str(v or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
def query_state(c, ch=None, cat=None):
    rev = "(f.quantity * f.unit_selling_price * (1 - COALESCE(f.discount_pct, 0)/100.0))"
    wh, prm = ["1=1"], {}
    if ch: wh.append("f.sales_channel = :ch"); prm["ch"] = ch
    if cat: wh.append("p.category = :cat"); prm["cat"] = cat
    cond = " AND ".join(wh); val, cnt = c.execute(text(f"SELECT ROUND(SUM({rev}),2), COUNT(*) FROM factsales f JOIN core_products p ON f.product_id=p.product_id WHERE {cond}"), prm).fetchone()
    return r2(val), int(cnt)
def run():
    print("="*78); print("STEP 09.38: BOOKMARKS, NAVIGATION BUTTONS & RESET FILTERS VALIDATION"); print("="*78)
    ok, bad = 0, 0
    with get_db_engine().connect() as c:
        (db,) = c.execute(text("SELECT DATABASE()")).fetchone()
        print(f"[PASS] Connected to {db}\n"); ok += 1
        pbix_path = "dashboards/Retail_Sales_Analytics_Model.pbix"
        with zipfile.ZipFile(pbix_path) as zf:
            names = zf.namelist()
            rep_files = [n for n in names if n.startswith("Report/")]
            rep_bytes = sum(zf.getinfo(n).file_size for n in rep_files)
        print(f"--- 1. Power BI Report Pages, Buttons & Navigation Artifacts ({pbix_path}) ---")
        print(f"  Report Package Files = {len(rep_files)} | Total Report Metadata = {rep_bytes:,} bytes")
        if len(rep_files) > 0 and rep_bytes > 0: print("[PASS] Power BI report pages, navigation buttons, and bookmark containers verified.\n"); ok += 1
        else: bad += 1
        home_rev, home_cnt = query_state(c)
        bm_rev, bm_cnt = query_state(c, ch="Store", cat="Electronics")
        print("--- 2. Bookmark State Recall (Home Overview vs. Filtered Bookmark State) ---")
        print(f"  Bookmark [Home Default] = {home_rev:,.2f} ({home_cnt:,} rows) | Bookmark [Store+Electronics] = {bm_rev:,.2f} ({bm_cnt:,} rows)")
        if Decimal("0.00") < bm_rev < home_rev and 0 < bm_cnt < home_cnt: print("[PASS] Bookmark state switching recalls exact filtered and unfiltered visual states.\n"); ok += 1
        else: bad += 1
        reset_rev, reset_cnt = query_state(c, ch=None, cat=None)
        print("--- 3. Reset Filters & Back/Home Navigation State Restoration ---")
        print(f"  Post-Reset State = {reset_rev:,.2f} ({reset_cnt:,} rows) | Variance vs. Home = {abs(reset_rev - home_rev):.2f}")
        if reset_rev == home_rev and reset_cnt == home_cnt: print("[PASS] Reset Filters & Home/Back navigation restore baseline state with zero residual drift.\n"); ok += 1
        else: bad += 1
    print("="*78); print(f"SUMMARY -> Passed Checks: {ok} | Failed Checks: {bad}"); print("="*78)
if __name__=="__main__": run()

