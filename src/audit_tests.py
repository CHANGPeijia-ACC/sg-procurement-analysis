"""Audit screening tests on the cleaned GeBIZ data.

Each function returns a DataFrame. Results are screening signals for
choosing what to look at, not evidence of irregularity.
"""

from __future__ import annotations

import pandas as pd
from scipy import stats

from analysis import aggregate_by_tender, concentration_by_group
from categories import OTHER, classify_descriptions

INCUMBENT_MIN_YEARS = 4
INCUMBENT_MIN_SHARE = 0.10

# Tender Lite (MOF): tenders with estimated value up to S$1 million, for
# general goods and services called from end April 2024 and construction
# from May 2025; ICT only from April 2026, after the data ends, so IT is a
# control group and gets the goods/services date as a placebo.
TENDER_LITE_LIMIT = 1_000_000
TENDER_LITE_CUTS = {"goods/services": "2024-05-01", "construction": "2025-05-01", "IT (control)": "2024-05-01"}


def _is_multiple(amounts: pd.Series, multiple: int) -> pd.Series:
    """Exact multiple test done in whole cents, so float noise does not matter."""
    cents = (pd.to_numeric(amounts, errors="coerce") * 100).round()
    return (cents % (multiple * 100)) == 0


def round_number_shares(
    df: pd.DataFrame,
    group_col: str | None = "agency",
    value_col: str = "awarded_amt",
    min_amount: float = 10.0,
    min_rows: int = 300,
    multiples: tuple[int, ...] = (1000, 10000),
) -> pd.DataFrame:
    """Share of amounts that are exact multiples of 1,000 and 10,000.

    The first row ("all") covers every amount >= min_amount. With group_col,
    one row follows per group that has at least min_rows such amounts,
    sorted by the share of the largest multiple.
    """
    kept = df[pd.to_numeric(df[value_col], errors="coerce") >= min_amount]

    def summarise(amounts: pd.Series) -> dict:
        row = {"n": len(amounts)}
        for m in multiples:
            flag = _is_multiple(amounts, m)
            row[f"n_x{m}"] = int(flag.sum())
            row[f"share_x{m}"] = float(flag.mean())
        return row

    rows = [{"group": "all", **summarise(kept[value_col])}]
    if group_col is not None:
        counts = kept[group_col].value_counts()
        groups = [{"group": g, **summarise(kept.loc[kept[group_col] == g, value_col])}
                  for g in counts[counts >= min_rows].index]
        groups.sort(key=lambda r: r[f"share_x{max(multiples)}"], reverse=True)
        rows += groups
    return pd.DataFrame(rows)


def incumbency(
    df: pd.DataFrame, min_years: int = INCUMBENT_MIN_YEARS, min_share: float = INCUMBENT_MIN_SHARE
) -> pd.DataFrame:
    """One row per agency-supplier pair with the fiscal years it won awards in.

    share_of_agency is the pair's awarded amount over the agency's total for
    all fiscal years in the data. flagged marks pairs present in at least
    min_years fiscal years with at least min_share of the agency's spend.
    Supplier names are only normalised for formatting, so a supplier split
    across name variants is understated here.
    """
    pairs = (
        df.groupby(["agency", "supplier_name"])
        .agg(years=("fiscal_year", "nunique"), n_tenders=("tender_no", "nunique"), awarded_amt=("awarded_amt", "sum"))
        .reset_index()
    )
    agency_total = pairs.groupby("agency")["awarded_amt"].transform("sum")
    pairs["share_of_agency"] = (pairs["awarded_amt"] / agency_total).where(agency_total > 0, 0.0)
    pairs["flagged"] = (pairs["years"] >= min_years) & (pairs["share_of_agency"] >= min_share)
    return pairs.sort_values(["flagged", "share_of_agency"], ascending=False).reset_index(drop=True)


def with_category(df: pd.DataFrame) -> pd.DataFrame:
    """Copy of df with a category column from the keyword classification of tender_description."""
    out = df.copy()
    out["category"] = classify_descriptions(out["tender_description"])["category"].to_numpy()
    return out


def category_concentration(df: pd.DataFrame, min_rows: int = 10) -> pd.DataFrame:
    """Amount-weighted HHI and CR4 per agency x category.

    Uses ETT rows only and leaves out "other", so it covers the classified
    part of the data. Groups need at least min_rows award rows.
    """
    rows = with_category(df[df["procurement_type"] == "ETT"])
    rows = rows[rows["category"] != OTHER]
    return concentration_by_group(rows, ["agency", "category"], min_awards=min_rows)


def tender_lite_comparison(df: pd.DataFrame, window_pct: float = 0.10, buffer_months: int = 6) -> pd.DataFrame:
    """Tender totals just below vs. just above S$1 million, before and after Tender Lite.

    ETT tenders are grouped as construction, IT (control) or goods/services
    (every other category, including "other"). "before" is awarded before the
    cut date; "after" starts buffer_months later, because the data has award
    dates only and tenders awarded soon after the cut were probably called
    before it. fisher_p tests whether the after period has a larger share
    below the line than the before period (one-sided).
    """
    tenders = with_category(aggregate_by_tender(df).query("procurement_type == 'ETT'"))
    tenders["group"] = tenders["category"].map({"construction": "construction", "IT": "IT (control)"}).fillna("goods/services")
    tenders["award_date"] = pd.to_datetime(tenders["award_date"])
    lo, hi = TENDER_LITE_LIMIT * (1 - window_pct), TENDER_LITE_LIMIT * (1 + window_pct)
    near = tenders[tenders["awarded_amt"].between(lo, hi)]

    rows = []
    for group, cut in TENDER_LITE_CUTS.items():
        g = near[near["group"] == group]
        cut = pd.Timestamp(cut)
        periods = {
            "before": g[g["award_date"] < cut],
            "after": g[g["award_date"] >= cut + pd.DateOffset(months=buffer_months)],
        }
        counts = {}
        for period, p in periods.items():
            below = int((p["awarded_amt"] < TENDER_LITE_LIMIT).sum())
            above = len(p) - below
            counts[period] = (below, above)
            rows.append({"group": group, "cut_date": cut.date(), "period": period, "n_below": below, "n_above": above,
                         "share_below": below / len(p) if len(p) else float("nan")})
        (b_below, b_above), (a_below, a_above) = counts["before"], counts["after"]
        fisher_p = stats.fisher_exact([[a_below, a_above], [b_below, b_above]], alternative="greater").pvalue
        rows[-1]["fisher_p"] = fisher_p
        rows[-1]["excluded_buffer"] = len(g) - len(periods["before"]) - len(periods["after"])
    return pd.DataFrame(rows)
