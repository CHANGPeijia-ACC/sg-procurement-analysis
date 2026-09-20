"""Run the queries in sql/ against the cleaned data with DuckDB.

    python src/run_sql.py            # print every query result
    python src/run_sql.py --save     # also write them to outputs/sql/

DuckDB queries a pandas frame directly, so nothing is imported into a
database first. Each query sees the cleaned data as a view called `awards`.
The queries repeat metrics that src/analysis.py also computes; tests/test_sql.py
checks that the two agree.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = ROOT / "sql"
PROCESSED_PATH = ROOT / "data" / "processed" / "gebiz_cleaned.csv"
OUTPUT_DIR = ROOT / "outputs" / "sql"
QUERIES = ["yearly_trend", "agency_concentration", "threshold_windows", "top_suppliers"]


def load_awards(path: Path = PROCESSED_PATH) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def run_query(name: str, awards: pd.DataFrame) -> pd.DataFrame:
    """Run sql/<name>.sql with `awards` available as a view of the same name."""
    sql = (SQL_DIR / f"{name}.sql").read_text(encoding="utf-8")
    connection = duckdb.connect()
    try:
        connection.register("awards", awards)
        return connection.execute(sql).fetch_df()
    finally:
        connection.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the SQL queries in sql/ with DuckDB.")
    parser.add_argument("--save", action="store_true", help="also write each result to outputs/sql/")
    args = parser.parse_args(argv)

    awards = load_awards()
    if args.save:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name in QUERIES:
        result = run_query(name, awards)
        print(f"\n--- {name} ({len(result)} rows) ---")
        print(result.head(10).to_string(index=False))
        if args.save:
            result.to_csv(OUTPUT_DIR / f"{name}.csv", index=False)
            print(f"written to {OUTPUT_DIR / f'{name}.csv'}")


if __name__ == "__main__":
    main()
