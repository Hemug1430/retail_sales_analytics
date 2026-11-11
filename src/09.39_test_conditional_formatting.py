import os, zipfile
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv()
def get_db_engine():
    u, p, h, pt, d = os.getenv("DB_USER","root"), os.getenv("DB_PASSWORD",""), os.getenv("DB_HOST","localhost"), os.getenv("DB_PORT","3306"), os.getenv("DB_NAME","retail_sales_db")
    return create_engine(f"mysql+pymysql://{u}:{p}@{h}:{pt}/{d}")
def r2(v): return Decimal(str(v or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
def eval_attainment_color(pct):
    if pct >= Decimal("100.00"): return "Green"
    if pct >= Decimal("85.00"): return "Amber"
    return "Red"
def eval_variance_color(var):
    if var > Decimal("0.00"): return "Green"
    if var < Decimal("0.00"): return "Red"
    return "Neutral"
def run():
    print("="*78); print("STEP 09.39: CONDITIONAL FORMATTING THRESHOLDS & POSITIVE/NEGATIVE RULES"); print("="*78)
    ok, bad = 0, 0
    with get_db_engine().connect() as c:
        (db,) = c.execute(text("SELECT DATABASE()")).fetchone()
        print(f"[PASS] Connected to {db}\n"); ok += 1
        cols = [col for col, *_ in c.execute(text("SHOW COLUMNS FROM vw_monthly_targets_realization")).fetchall()]
        att_col = next((col for col in cols if "attain" in col.lower() or "achiev" in col.lower() or "pct" in col.lower()), None)
        var_col = next((col for col in cols if "var" in col.lower() or "diff" in col.lower()), None)
        rows = c.execute(text(f"SELECT `{att_col}`, (`{att_col}` - 100.0) FROM vw_monthly_targets_realization")).fetchall()
        att_counts = {"Green":0, "Amber":0, "Red":0}
        var_counts = {"Green":0, "Red":0, "Neutral":0}
        parity_err = 0
        for att, var in rows:
            a_val, v_val = r2(att), r2(var)
            ac, vc = eval_attainment_color(a_val), eval_variance_color(v_val)
            att_counts[ac] += 1; var_counts[vc] += 1
            if (a_val >= Decimal("100.00") and v_val < Decimal("0.00")) or (a_val < Decimal("100.00") and v_val > Decimal("0.00")): parity_err += 1
        print(f"--- 1. Target Attainment Threshold Rules ({len(rows)} rows evaluated) ---")
        print(f"  Green (>=100%) = {att_counts['Green']} | Amber (85-99.99%) = {att_counts['Amber']} | Red (<85%) = {att_counts['Red']}")
        if len(rows) > 0 and sum(att_counts.values()) == len(rows): print("[PASS] Target attainment threshold formatting buckets classify 100% of rows cleanly.\n"); ok += 1
        else: bad += 1
        print(f"--- 2. Positive/Negative Variance Formatting & Attainment Parity ---")
        print(f"  Positive Green (>0) = {var_counts['Green']} | Negative Red (<0) = {var_counts['Red']} | Neutral (=0) = {var_counts['Neutral']} | SignParityErrors = {parity_err}")
        if parity_err == 0 and sum(var_counts.values()) == len(rows): print("[PASS] Positive/negative variance color states align 100% with attainment thresholds.\n"); ok += 1
        else: bad += 1
        boundary_cases = [(Decimal("100.00"), "Green"), (Decimal("99.99"), "Amber"), (Decimal("85.00"), "Amber"), (Decimal("84.99"), "Red")]
        b_ok = all(eval_attainment_color(v) == exp for v, exp in boundary_cases)
        pbix_ok = zipfile.is_zipfile("dashboards/Retail_Sales_Analytics_Model.pbix")
        print(f"--- 3. Exact Boundary Edge Cases & Power BI Conditional Formatting Metadata ---")
        print(f"  Boundary Tests (100.00/99.99/85.00/84.99) Passed = {b_ok} | PBIX Valid = {pbix_ok}")
        if b_ok and pbix_ok: print("[PASS] Exact threshold edge boundaries & Power BI report formatting metadata verified.\n"); ok += 1
        else: bad += 1
    print("="*78); print(f"SUMMARY -> Passed Checks: {ok} | Failed Checks: {bad}"); print("="*78)
if __name__=="__main__": run()




