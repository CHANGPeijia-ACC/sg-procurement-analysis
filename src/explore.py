"""Quick structural profile of the raw GeBIZ dataset.

Prints shape, dtypes, missingness, cardinality, and a numeric summary.
Run: python src/explore.py
"""

from pathlib import Path

import pandas as pd

RAW_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "gebiz_procurement.csv"


def profile(df: pd.DataFrame) -> None:
    print(f"shape: {df.shape[0]} rows x {df.shape[1]} cols\n")

    summary = pd.DataFrame(
        {
            "dtype": df.dtypes,
            "missing_pct": (df.isna().mean() * 100).round(2),
            "n_unique": df.nunique(),
        }
    )
    print(summary.to_string())
    print()

    numeric_cols = df.select_dtypes("number").columns
    if len(numeric_cols):
        print("numeric column summary:")
        print(df[numeric_cols].describe().to_string())


if __name__ == "__main__":
    df = pd.read_csv(RAW_PATH, low_memory=False)
    profile(df)
