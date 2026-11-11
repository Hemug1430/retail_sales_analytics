"""
Module: Data Ingestion
Purpose: Load Retail Sales dataset from data/raw folder.
"""

from pathlib import Path
import pandas as pd

from config import RAW_DATA_PATH


def check_dataset_exists(filename: str = "retail_sales.csv") -> Path:
    """Check if dataset exists."""
    dataset_path = RAW_DATA_PATH / filename

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    print(f"Dataset Found: {dataset_path.name}")
    return dataset_path


def load_dataset(filename: str = "retail_sales.csv") -> pd.DataFrame:
    """Load CSV into a Pandas DataFrame."""

    dataset_path = check_dataset_exists(filename)

    df = pd.read_csv(dataset_path)

    print("\nDataset Loaded Successfully!")
    print(f"Rows    : {df.shape[0]}")
    print(f"Columns : {df.shape[1]}")

    print("\nColumn Names")
    print(df.columns.tolist())

    print("\nFirst Five Rows")
    print(df.head())

    return df


if __name__ == "__main__":
    load_dataset()

print(df.head())

return df