import unittest
import pandas as pd

REQUIRED_SCHEMA = {
    "transaction_id": "str",
    "store_id": "str",
    "product_id": "str",
    "quantity": "numeric",
    "unit_selling_price": "numeric"
}

APPROVED_OPTIONAL_COLUMNS = {
    "promo_code": "str",
    "loyalty_points_earned": "numeric"
}

def validate_dataframe_schema(df, allow_approved_evolution=True):
    errors = []
    actual_cols = set(df.columns)
    required_cols = set(REQUIRED_SCHEMA.keys())
    allowed_cols = required_cols | (set(APPROVED_OPTIONAL_COLUMNS.keys()) if allow_approved_evolution else set())

    # 1. Missing required columns check
    missing_cols = sorted(required_cols - actual_cols)
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")

    # 2. Unexpected extra columns check
    extra_cols = sorted(actual_cols - allowed_cols)
    if extra_cols:
        errors.append(f"Unapproved extra columns: {extra_cols}")

    # 3. Data type validation on present columns
    combined_types = {**REQUIRED_SCHEMA, **(APPROVED_OPTIONAL_COLUMNS if allow_approved_evolution else {})}
    for col, expected_type in combined_types.items():
        if col not in df.columns:
            continue
        if expected_type == "numeric":
            converted = pd.to_numeric(df[col], errors="coerce")
            invalid_mask = df[col].notna() & converted.isna()
            if invalid_mask.any():
                errors.append(f"Type failure in numeric column '{col}': {int(invalid_mask.sum())} non-numeric values")
        elif expected_type == "str":
            if df[col].dropna().empty and len(df) > 0 and col in required_cols:
                errors.append(f"Null/empty failure in required string column '{col}'")

    return len(errors) == 0, errors


class TestSchemaValidationRules(unittest.TestCase):

    def test_valid_canonical_schema(self):
        df = pd.DataFrame({
            "transaction_id": list(("TXN001", "TXN002")),
            "store_id": list(("STR01", "STR02")),
            "product_id": list(("PRD01", "PRD02")),
            "quantity": list((2, 5)),
            "unit_selling_price": list((199.50, 499.00))
        })
        is_valid, errors = validate_dataframe_schema(df)
        self.assertTrue(is_valid, f"Expected valid schema, got errors: {errors}")

    def test_missing_required_columns(self):
        df = pd.DataFrame({
            "transaction_id": list(("TXN001",)),
            "store_id": list(("STR01",)),
            "quantity": list((1,))
        })
        is_valid, errors = validate_dataframe_schema(df)
        self.assertFalse(is_valid)
        self.assertTrue(any("Missing required columns" in e for e in errors))

    def test_unapproved_extra_columns(self):
        df = pd.DataFrame({
            "transaction_id": list(("TXN001",)),
            "store_id": list(("STR01",)),
            "product_id": list(("PRD01",)),
            "quantity": list((1,)),
            "unit_selling_price": list((199.50,)),
            "random_unapproved_col": list(("unexpected",))
        })
        is_valid, errors = validate_dataframe_schema(df)
        self.assertFalse(is_valid)
        self.assertTrue(any("Unapproved extra columns" in e for e in errors))

    def test_numeric_type_failure(self):
        df = pd.DataFrame({
            "transaction_id": list(("TXN001", "TXN002")),
            "store_id": list(("STR01", "STR02")),
            "product_id": list(("PRD01", "PRD02")),
            "quantity": list(("TWO_UNITS", 5)),
            "unit_selling_price": list((199.50, "FREE"))
        })
        is_valid, errors = validate_dataframe_schema(df)
        self.assertFalse(is_valid)
        self.assertTrue(any("Type failure in numeric column" in e for e in errors))

    def test_approved_schema_evolution(self):
        df = pd.DataFrame({
            "transaction_id": list(("TXN001",)),
            "store_id": list(("STR01",)),
            "product_id": list(("PRD01",)),
            "quantity": list((3,)),
            "unit_selling_price": list((250.00,)),
            "promo_code": list(("FESTIVE10",)),
            "loyalty_points_earned": list((50,))
        })
        is_valid, errors = validate_dataframe_schema(df, allow_approved_evolution=True)
        self.assertTrue(is_valid, f"Expected approved schema evolution to pass, got errors: {errors}")


if __name__ == "__main__":
    print("=" * 75)
    print("STEP 09.07: UNIT-TEST SCHEMA VALIDATION & EVOLUTION RULES")
    print("=" * 75)
    unittest.main(verbosity=2)
