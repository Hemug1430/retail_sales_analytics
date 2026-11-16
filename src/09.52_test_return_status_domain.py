"""
09.52 - Return status / refund domain check (Doc 02 + Doc 04 + Doc 05 BR-07).
Run from the project root:  python src/09.52_test_return_status_domain.py
"""
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(".env")
VALID = ("Requested", "Approved", "Rejected", "Refunded")
METHODS = ("Original Payment", "Store Credit", "Cash")


def engine():
    u, p = os.getenv("DB_USER", "root"), os.getenv("DB_PASSWORD", "")
    h, pt, d = os.getenv("DB_HOST", "localhost"), os.getenv("DB_PORT", "3306"), os.getenv("DB_NAME", "retail_sales_db")
    return create_engine(f"mysql+pymysql://{u}:{p}@{h}:{pt}/{d}")


def main():
    in_list = ",".join(f"'{v}'" for v in VALID)
    m_list = ",".join(f"'{m}'" for m in METHODS)
    checks = {
        "return_status outside allowed domain": f"SELECT COUNT(*) FROM factreturns WHERE return_status NOT IN ({in_list})",
        "Refunded rows missing refund_amount or refund_method": "SELECT COUNT(*) FROM factreturns WHERE return_status='Refunded' AND (refund_amount IS NULL OR refund_method IS NULL)",
        "Refunded rows with invalid refund_method": f"SELECT COUNT(*) FROM factreturns WHERE return_status='Refunded' AND refund_method NOT IN ({m_list})",
        "Rejected/Requested/Approved rows carrying a refund_amount > 0": "SELECT COUNT(*) FROM factreturns WHERE return_status<>'Refunded' AND COALESCE(refund_amount,0) > 0",
    }
    bad = 0
    print("=" * 78)
    print("STEP 09.52: RETURN STATUS & REFUND DOMAIN CHECK")
    print("=" * 78)
    with engine().connect() as c:
        for label, sql in checks.items():
            n = int(c.execute(text(sql)).scalar())
            print(f"  [{'PASS' if n == 0 else 'FAIL'}] {label}: {n}")
            bad += n > 0
        rf, amt = c.execute(text("SELECT COUNT(*), COALESCE(SUM(refund_amount),0) FROM factreturns WHERE return_status='Refunded'")).fetchone()
        kpi = c.execute(text("SELECT refunded_revenue FROM analytics_master_kpi_reconciliation")).scalar()
        ok = abs(float(kpi) - float(amt)) < 0.01
        print(f"  [{'PASS' if ok else 'FAIL'}] KPI view refunded_revenue {float(kpi):,.2f} = Refunded SUM {float(amt):,.2f} ({rf} rows)")
        bad += not ok
    print("=" * 78)
    print(f"SUMMARY -> Failed Checks: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
