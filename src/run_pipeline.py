"""Run the whole analysis: clean the raw data, then write the tables and figures.

    python src/run_pipeline.py              # use the raw file already downloaded
    python src/run_pipeline.py --download   # fetch a fresh copy of the raw data first

The dataset is a rolling window, so --download can change the numbers. Without
it the pipeline reproduces the committed results from the existing raw file.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

import make_figures
from analysis import aggregate_by_tender, benford_by_agency
from audit_tests import risk_scores
from cleaning import clean_pipeline
from download import download

ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "data" / "raw" / "gebiz_procurement.csv"
PROCESSED_PATH = ROOT / "data" / "processed" / "gebiz_cleaned.csv"
OUTPUTS = ROOT / "outputs"
AUDIT_SAMPLE_SIZE = 50


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Clean the GeBIZ data and rebuild every output.")
    parser.add_argument("--download", action="store_true", help="fetch a fresh copy of the raw data first")
    args = parser.parse_args(argv)

    if args.download:
        print(f"Downloading raw data to {RAW_PATH}")
        download(RAW_PATH)
    if not RAW_PATH.exists():
        raise SystemExit(f"No raw data at {RAW_PATH}. Run again with --download.")

    raw = pd.read_csv(RAW_PATH, low_memory=False)
    df = clean_pipeline(raw)
    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_PATH, index=False)

    OUTPUTS.mkdir(parents=True, exist_ok=True)
    benford_by_agency(df).to_csv(OUTPUTS / "benford_by_agency.csv", index=False)
    risk_scores(df).head(AUDIT_SAMPLE_SIZE).to_csv(OUTPUTS / "audit_sample.csv", index=False)
    make_figures.main(df)

    tenders = aggregate_by_tender(df)
    print(f"raw rows           {len(raw):,}")
    print(f"cleaned rows       {len(df):,}")
    print(f"tenders            {len(tenders):,} ({int((tenders['procurement_type'] == 'ETT').sum()):,} ETT)")
    print(f"fiscal years       {df['fiscal_year'].min()} to {df['fiscal_year'].max()}")
    print(f"processed data     {PROCESSED_PATH}")
    print(f"tables             {OUTPUTS / 'benford_by_agency.csv'}, {OUTPUTS / 'audit_sample.csv'}")


if __name__ == "__main__":
    main()
