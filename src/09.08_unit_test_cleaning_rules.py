import re
import unittest
import pandas as pd

CATEGORY_MAP = {
    "elec": "Electronics",
    "electronics": "Electronics",
    "apparel": "Fashion",
    "fashion": "Fashion",
    "home": "Home & Kitchen",
    "home & kitchen": "Home & Kitchen",
    "grocery": "Groceries",
    "groceries": "Groceries"
}

def clean_text_value(val):
    if pd.isna(val):
        return None
    cleaned = re.sub(r"\s+", " ", str(val).strip())
    return cleaned.title() if cleaned else None

def standardize_date_series(series):
    parsed = pd.to_datetime(series, format="mixed", errors="coerce")
    return parsed.dt.strftime("%Y-%m-%d")

def clean_numeric_series(series):
    cleaned = series.astype(str).str.replace(r"[₹$,\s]", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce")

def standardize_category(val):
    if pd.isna(val):
        return "Uncategorized"
    key = re.sub(r"\s+", " ", str(val).strip().lower())
    return CATEGORY_MAP.get(key, "Other")

def run_cleaning_pipeline(raw_df):
    df = raw_df.copy()

    # 1. Text cleaning
    df["customer_name"] = df["customer_name"].apply(clean_text_value)

    # 2. Category standardization
    df["category"] = df["category"].apply(standardize_category)

    # 3. Date standardization
    df["transaction_date"] = standardize_date_series(df["transaction_date"])

    # 4. Numeric cleaning
    df["quantity"] = clean_numeric_series(df["quantity"])
    df["unit_price"] = clean_numeric_series(df["unit_price"])
    df["discount_pct"] = clean_numeric_series(df["discount_pct"]).fillna(0.0)

    # 5. Deduplication on primary key
    df = df.drop_duplicates(subset=list(("transaction_id",)), keep="first").copy()

    # 6. Validation gate (separate valid rows from quarantine rows)
    valid_mask = (
        df["transaction_id"].notna()
        & (df["transaction_id"].astype(str).str.strip() != "")
        & df["transaction_date"].notna()
        & (df["quantity"] > 0)
        & (df["unit_price"] >= 0)
        & (df["discount_pct"].between(0.0, 100.0))
    )

    clean_df = df.loc[valid_mask].reset_index(drop=True)
    quarantine_df = df.loc[~valid_mask].reset_index(drop=True)
    return clean_df, quarantine_df


class TestDataCleaningRules(unittest.TestCase):

    def test_text_cleaning(self):
        self.assertEqual(clean_text_value("   rahul   SHARMA  "), "Rahul Sharma")
        self.assertIsNone(clean_text_value("   "))
        self.assertIsNone(clean_text_value(None))

    def test_date_standardization(self):
        s = pd.Series(list(("2026-03-15", "2026/04/05", "bad_date")))
        first_val, second_val, third_val = tuple(standardize_date_series(s))
        self.assertEqual(first_val, "2026-03-15")
        self.assertEqual(second_val, "2026-04-05")
        self.assertTrue(pd.isna(third_val))

    def test_numeric_cleaning(self):
        s = pd.Series(list(("₹1,499.50", "$250.00", "invalid")))
        first_num, second_num, third_num = tuple(clean_numeric_series(s))
        self.assertAlmostEqual(float(first_num), 1499.50)
        self.assertAlmostEqual(float(second_num), 250.00)
        self.assertTrue(pd.isna(third_num))

    def test_category_standardization(self):
        self.assertEqual(standardize_category("  ELEC "), "Electronics")
        self.assertEqual(standardize_category("apparel"), "Fashion")
        self.assertEqual(standardize_category(None), "Uncategorized")
        self.assertEqual(standardize_category("UnknownDept"), "Other")

    def test_null_duplicate_and_validation_pipeline(self):
        raw = pd.DataFrame({
            "transaction_id": list(("TXN01", "TXN01", "TXN02", "TXN03", None)),
            "customer_name": list(("  anita  verma ", "  anita  verma ", "vijay rao", "neha singh", "ghost user")),
            "category": list(("elec", "elec", "APPAREL", "home", "grocery")),
            "transaction_date": list(("2026-05-01", "2026-05-01", "2026/05/02", "not-a-date", "2026-05-03")),
            "quantity": list(("2", "2", "3", "-5", "1")),
            "unit_price": list(("₹500.00", "₹500.00", "1,200.00", "300.00", "100.00")),
            "discount_pct": list((None, None, "10", "5", "0"))
        })

        clean_df, quarantine_df = run_cleaning_pipeline(raw)

        self.assertEqual(len(clean_df), 2)
        self.assertEqual(list(clean_df["transaction_id"]), list(("TXN01", "TXN02")))

        first_row = clean_df.to_dict(orient="records").pop(0)
        self.assertEqual(float(first_row.get("discount_pct")), 0.0)
        self.assertEqual(first_row.get("category"), "Electronics")
        self.assertEqual(first_row.get("customer_name"), "Anita Verma")

        self.assertEqual(len(quarantine_df), 2)


if __name__ == "__main__":
    print("=" * 75)
    print("STEP 09.08: UNIT-TEST DATA CLEANING & TRANSFORMATION RULES")
    print("=" * 75)
    unittest.main(verbosity=2)
