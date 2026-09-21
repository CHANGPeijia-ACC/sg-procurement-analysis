"""Export the tables the Power BI report imports.

    python src/export_powerbi.py

Writes two files to pbi/:

    tenders.csv   one row per tender: total amount, category, red flags, risk score
    dim_date.csv  one row per calendar day in the data, with fiscal year

The award rows themselves are already committed as
data/processed/gebiz_cleaned.csv, so they are not exported again. In Power BI,
tenders relates to the awards table on tender_no, and dim_date relates to it on
award_date. See docs/powerbi_setup.md.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from analysis import aggregate_by_tender
from audit_tests import RISK_WEIGHTS, risk_scores, with_category

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_PATH = ROOT / "data" / "processed" / "gebiz_cleaned.csv"
PBI_DIR = ROOT / "pbi"

FLAG_COLUMNS = list(RISK_WEIGHTS)


def build_tenders(df: pd.DataFrame) -> pd.DataFrame:
    """One row per tender, with the category and the risk flags.

    Flags and score come from risk_scores(), which covers ETT tenders only.
    Interface-record tenders keep the same columns with the flags set to false,
    so the table can be filtered on procurement_type rather than split in two.
    """
    tenders = with_category(aggregate_by_tender(df))
    scored = risk_scores(df)[["tender_no", *FLAG_COLUMNS, "score", "reasons"]]
    out = tenders.merge(scored, on="tender_no", how="left")
    out[FLAG_COLUMNS] = out[FLAG_COLUMNS].fillna(False).astype(bool)
    out["score"] = out["score"].fillna(0.0)
    out["reasons"] = out["reasons"].fillna("")
    out["is_ett"] = out["procurement_type"] == "ETT"
    columns = ["tender_no", "agency", "category", "award_date", "fiscal_year", "procurement_type", "is_ett",
               "n_rows", "n_suppliers", "awarded_amt", *FLAG_COLUMNS, "score", "reasons"]
    return out[columns].sort_values("award_date").reset_index(drop=True)


def build_dim_date(df: pd.DataFrame) -> pd.DataFrame:
    """One row per calendar day between the first and last award date.

    Power BI needs a gap-free date table for time comparisons. The Singapore
    fiscal year starts on 1 April, so fiscal_year_index orders FY2021 to FY2025
    as 1 to 5 for year-on-year measures.
    """
    dates = pd.to_datetime(df["award_date"])
    calendar = pd.DataFrame({"date": pd.date_range(dates.min(), dates.max(), freq="D")})
    fy_start = calendar["date"].dt.year.where(calendar["date"].dt.month >= 4, calendar["date"].dt.year - 1)
    calendar["fiscal_year"] = "FY" + fy_start.astype(str)
    calendar["fiscal_year_index"] = fy_start - fy_start.min() + 1
    fiscal_month = (calendar["date"].dt.month - 4) % 12 + 1
    calendar["fiscal_quarter"] = "Q" + ((fiscal_month - 1) // 3 + 1).astype(str)
    calendar["calendar_year"] = calendar["date"].dt.year
    calendar["month_number"] = calendar["date"].dt.month
    calendar["month_name"] = calendar["date"].dt.strftime("%b")
    return calendar


def main() -> None:
    df = pd.read_csv(PROCESSED_PATH, low_memory=False)
    PBI_DIR.mkdir(parents=True, exist_ok=True)

    tenders = build_tenders(df)
    dim_date = build_dim_date(df)
    tenders.to_csv(PBI_DIR / "tenders.csv", index=False)
    dim_date.to_csv(PBI_DIR / "dim_date.csv", index=False)

    print(f"tenders.csv   {len(tenders):,} rows, {tenders['awarded_amt'].sum():,.0f} total awarded")
    print(f"dim_date.csv  {len(dim_date):,} days, {dim_date['fiscal_year'].min()} to {dim_date['fiscal_year'].max()}")
    print(f"written to {PBI_DIR}")


if __name__ == "__main__":
    main()
