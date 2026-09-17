"""Analysis functions for the GeBIZ procurement dataset.

Four analyses, matching the project brief:
1. Supplier concentration (HHI, CR4)
2. Amount-threshold clustering
3. Benford's law first-digit test
4. Supplier profile & trend (top-N, yearly, agency x year)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

# ---------------------------------------------------------------------------
# 4.1 Supplier concentration
# ---------------------------------------------------------------------------


def _shares(df: pd.DataFrame, group_cols: list[str], value_col: str, entity_col: str) -> pd.DataFrame:
    """Per-(group, entity) share of the group total, as a percentage."""
    totals = df.groupby(group_cols)[value_col].transform("sum")
    share = np.where(totals > 0, df[value_col] / totals * 100, 0.0)
    out = df[group_cols + [entity_col]].copy()
    out["share_pct"] = share
    return out.groupby(group_cols + [entity_col], as_index=False)["share_pct"].sum()


def hhi(df: pd.DataFrame, group_cols: list[str], value_col: str = "awarded_amt", entity_col: str = "supplier_name") -> pd.DataFrame:
    """Herfindahl-Hirschman Index per group, on a 0-10,000 scale.

    HHI = sum(share_pct^2) where share_pct is each entity's % of the
    group's total `value_col` (or count, if value_col is a constant/count
    column). 10,000 = single-supplier monopoly; below ~1,500 is considered
    unconcentrated by common (US DOJ) rule-of-thumb bands.
    """
    entity_totals = df.groupby(group_cols + [entity_col])[value_col].sum().reset_index()
    group_totals = entity_totals.groupby(group_cols)[value_col].transform("sum")
    entity_totals["share_pct"] = np.where(group_totals > 0, entity_totals[value_col] / group_totals * 100, 0.0)
    result = (
        entity_totals.groupby(group_cols)
        .agg(hhi=("share_pct", lambda s: (s**2).sum()), n_suppliers=(entity_col, "nunique"), total=(value_col, "sum"))
        .reset_index()
    )
    return result


def cr4(df: pd.DataFrame, group_cols: list[str], value_col: str = "awarded_amt", entity_col: str = "supplier_name") -> pd.DataFrame:
    """Combined market share (%) of the top 4 suppliers per group."""
    entity_totals = df.groupby(group_cols + [entity_col])[value_col].sum().reset_index()
    group_totals = entity_totals.groupby(group_cols)[value_col].transform("sum")
    entity_totals["share_pct"] = np.where(group_totals > 0, entity_totals[value_col] / group_totals * 100, 0.0)

    def top4_share(g: pd.DataFrame) -> float:
        return g["share_pct"].nlargest(4).sum()

    result = entity_totals.groupby(group_cols).apply(top4_share, include_groups=False).reset_index(name="cr4")
    n_suppliers = entity_totals.groupby(group_cols)[entity_col].nunique().reset_index(name="n_suppliers")
    return result.merge(n_suppliers, on=group_cols)


def concentration_by_group(
    df: pd.DataFrame,
    group_cols: list[str],
    value_col: str = "awarded_amt",
    entity_col: str = "supplier_name",
    min_awards: int = 5,
) -> pd.DataFrame:
    """HHI + CR4 side by side per group, filtered to groups with enough awards to be meaningful."""
    h = hhi(df, group_cols, value_col, entity_col)
    c = cr4(df, group_cols, value_col, entity_col)[group_cols + ["cr4"]]
    counts = df.groupby(group_cols).size().reset_index(name="n_awards")
    result = h.merge(c, on=group_cols).merge(counts, on=group_cols)
    return result[result["n_awards"] >= min_awards].sort_values("hhi", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 4.2 Amount-threshold clustering
# ---------------------------------------------------------------------------

TENDER_LEVEL_COLS = ["agency", "award_date", "fiscal_year", "procurement_type", "tender_detail_status", "tender_description"]


def aggregate_by_tender(df: pd.DataFrame) -> pd.DataFrame:
    """One row per tender_no, with awarded_amt summed over its rows.

    Procurement thresholds apply to a whole procurement, not to each awarded
    line item. The descriptive columns must be constant within a tender;
    raises otherwise.
    """
    g = df.groupby("tender_no")
    varying = [c for c in TENDER_LEVEL_COLS if (g[c].nunique(dropna=False) > 1).any()]
    if varying:
        raise ValueError(f"Columns vary within a tender_no: {varying}")
    return g.agg(
        **{c: (c, "first") for c in TENDER_LEVEL_COLS},
        n_rows=("awarded_amt", "size"),
        n_suppliers=("supplier_name", "nunique"),
        awarded_amt=("awarded_amt", "sum"),
    ).reset_index()


def threshold_window_counts(
    df: pd.DataFrame, thresholds: list[float], window_pct: float = 0.10, value_col: str = "awarded_amt"
) -> pd.DataFrame:
    """Count awards just below vs. just above each threshold, within +/- window_pct."""
    rows = []
    amounts = df[value_col]
    for t in thresholds:
        lo, hi = t * (1 - window_pct), t * (1 + window_pct)
        below = ((amounts >= lo) & (amounts < t)).sum()
        above = ((amounts >= t) & (amounts <= hi)).sum()
        rows.append(
            {
                "threshold": t,
                "window_pct": window_pct,
                "n_just_below": int(below),
                "n_just_above": int(above),
                "ratio_below_over_above": (below / above) if above else np.nan,
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 4.3 Benford's law
# ---------------------------------------------------------------------------

BENFORD_EXPECTED = {d: np.log10(1 + 1 / d) for d in range(1, 10)}


def leading_digit(series: pd.Series) -> pd.Series:
    """First significant digit (1-9) of each positive value; NaN elsewhere."""
    s = series.astype(float)
    s = s.where(s > 0)
    exponent = np.floor(np.log10(s))
    leading = np.floor(s / (10**exponent))
    # floating point can push a value just over/under a power of ten
    leading = leading.where(leading <= 9, 9)
    leading = leading.where((leading >= 1) | leading.isna(), 1)
    return leading


def benford_test(series: pd.Series, min_amount: float = 0) -> dict:
    """Chi-square goodness-of-fit test of leading digits against Benford's law.

    min_amount: exclude values below this before testing (Benford's law
    assumes magnitudes spanning several orders of ten; a floor filters out
    a spike of small round-number transactions that isn't what the law
    models).
    """
    vals = series[series > min_amount]
    digits = leading_digit(vals).dropna()
    n = len(digits)
    observed = digits.value_counts().reindex(range(1, 10), fill_value=0).sort_index()
    expected_pct = pd.Series(BENFORD_EXPECTED).sort_index()
    expected_counts = expected_pct * n
    chi2, p_value = stats.chisquare(f_obs=observed.values, f_exp=expected_counts.values)
    return {
        "n": n,
        "observed_pct": (observed / n * 100).to_dict(),
        "expected_pct": (expected_pct * 100).to_dict(),
        "chi2": chi2,
        "p_value": p_value,
        "dof": 8,
    }


# ---------------------------------------------------------------------------
# 4.4 Supplier profile & trend
# ---------------------------------------------------------------------------


def top_suppliers(df: pd.DataFrame, n: int = 10, value_col: str = "awarded_amt", entity_col: str = "supplier_name") -> pd.DataFrame:
    agg = df.groupby(entity_col).agg(total_amt=(value_col, "sum"), n_awards=(entity_col, "count"), n_agencies=("agency", "nunique")).reset_index()
    return agg.sort_values("total_amt", ascending=False).head(n).reset_index(drop=True)


def yearly_trend(df: pd.DataFrame, value_col: str = "awarded_amt", year_col: str = "fiscal_year") -> pd.DataFrame:
    return (
        df.groupby(year_col)
        .agg(total_amt=(value_col, "sum"), n_awards=(value_col, "count"), n_suppliers=("supplier_name", "nunique"))
        .reset_index()
        .sort_values(year_col)
    )


def agency_year_pivot(df: pd.DataFrame, value_col: str = "awarded_amt", agency_col: str = "agency", year_col: str = "fiscal_year", agg: str = "sum") -> pd.DataFrame:
    return df.pivot_table(index=agency_col, columns=year_col, values=value_col, aggfunc=agg, fill_value=0)
