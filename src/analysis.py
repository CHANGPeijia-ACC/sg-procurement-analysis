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


def entity_shares(df: pd.DataFrame, group_cols: list[str], value_col: str = "awarded_amt",
                  entity_col: str = "supplier_name") -> pd.DataFrame:
    """One row per (group, entity) with its share of the group total, in percent."""
    totals = df.groupby(group_cols + [entity_col])[value_col].sum().reset_index()
    group_totals = totals.groupby(group_cols)[value_col].transform("sum")
    totals["share_pct"] = np.where(group_totals > 0, totals[value_col] / group_totals * 100, 0.0)
    return totals


def hhi(df: pd.DataFrame, group_cols: list[str], value_col: str = "awarded_amt", entity_col: str = "supplier_name") -> pd.DataFrame:
    """Herfindahl-Hirschman Index per group, on a 0-10,000 scale.

    HHI = sum(share_pct^2) where share_pct is each entity's % of the
    group's total `value_col` (or count, if value_col is a constant/count
    column). 10,000 = single-supplier monopoly; below ~1,500 is considered
    unconcentrated by common (US DOJ) rule-of-thumb bands.
    """
    entity_totals = entity_shares(df, group_cols, value_col, entity_col)
    result = (
        entity_totals.groupby(group_cols)
        .agg(hhi=("share_pct", lambda s: (s**2).sum()), n_suppliers=(entity_col, "nunique"), total=(value_col, "sum"))
        .reset_index()
    )
    return result


def cr4(df: pd.DataFrame, group_cols: list[str], value_col: str = "awarded_amt", entity_col: str = "supplier_name") -> pd.DataFrame:
    """Combined market share (%) of the top 4 suppliers per group."""
    entity_totals = entity_shares(df, group_cols, value_col, entity_col)

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
    """Count awards just below vs. just above each threshold, within +/- window_pct.

    An amount exactly at the threshold counts as above. p_more_below is a
    one-sided binomial test of "more below than above" against a 50/50 split.
    """
    rows = []
    amounts = df[value_col]
    for t in thresholds:
        lo, hi = t * (1 - window_pct), t * (1 + window_pct)
        below = int(((amounts >= lo) & (amounts < t)).sum())
        above = int(((amounts >= t) & (amounts <= hi)).sum())
        n = below + above
        rows.append(
            {
                "threshold": t,
                "window_pct": window_pct,
                "n_just_below": below,
                "n_just_above": above,
                "ratio_below_over_above": (below / above) if above else np.nan,
                "p_more_below": stats.binomtest(below, n, 0.5, alternative="greater").pvalue if n else np.nan,
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 4.3 Benford's law
# ---------------------------------------------------------------------------

def leading_digits(series: pd.Series, n_digits: int = 1) -> pd.Series:
    """First n significant digits of each positive value; NaN for zero, negative or missing.

    1,234.5 gives 1 (n_digits=1) or 12 (n_digits=2). Digits are read from the
    number written in scientific notation, which avoids floating-point errors
    such as 0.3 / 0.1 = 2.9999999999999996. For n_digits=2, apply a floor of 10
    first: a value such as 5 would otherwise be read as 50.
    """
    s = pd.to_numeric(series, errors="coerce")
    s = s.where(s > 0)
    # astype(object) keeps the text operations working when nothing is positive
    text = s.map(lambda x: f"{x:.12e}", na_action="ignore").astype("object")
    return pd.to_numeric(text.str.replace(".", "", regex=False).str[:n_digits], errors="coerce")


def leading_digit(series: pd.Series) -> pd.Series:
    """First significant digit (1-9) of each positive value; NaN elsewhere."""
    return leading_digits(series, 1)


# Nigrini (2012) MAD conformity bands: (upper limit, label). A MAD exactly on
# a limit goes to the better band.
NIGRINI_BANDS = {
    1: [(0.006, "close"), (0.012, "acceptable"), (0.015, "marginal"), (np.inf, "nonconformity")],
    2: [(0.0012, "close"), (0.0018, "acceptable"), (0.0022, "marginal"), (np.inf, "nonconformity")],
}


def nigrini_band(mad: float, digits: int = 1) -> str:
    return next(label for upper, label in NIGRINI_BANDS[digits] if mad <= upper)


def benford_expected(digits: int = 1) -> pd.Series:
    """Benford proportions for first digits 1-9 (digits=1) or first two digits 10-99 (digits=2)."""
    first = 10 ** (digits - 1)
    d = np.arange(first, 10 * first)
    return pd.Series(np.log10(1 + 1 / d), index=d)


def benford_mad(series: pd.Series, digits: int = 1, min_amount: float = 10.0) -> dict:
    """Benford conformity by mean absolute deviation (MAD), with a chi-square test alongside.

    Uses values >= min_amount. MAD is the average of |observed share -
    expected share| over the 9 (or 90) digit groups, and does not grow with
    sample size the way the chi-square statistic does.
    """
    values = pd.to_numeric(series, errors="coerce")
    values = values[values >= min_amount]
    found = leading_digits(values, digits).dropna().astype(int)
    expected = benford_expected(digits)
    counts = found.value_counts().reindex(expected.index, fill_value=0)
    n = int(counts.sum())
    if n == 0:
        raise ValueError("No values at or above min_amount")
    observed = counts / n
    mad = float((observed - expected).abs().mean())
    band = nigrini_band(mad, digits)
    chi2, p_value = stats.chisquare(counts.to_numpy(), expected.to_numpy() * n)
    table = pd.DataFrame({"count": counts, "observed": observed, "expected": expected})
    table.index.name = "digits"
    return {"digits": digits, "min_amount": min_amount, "n": n, "mad": mad, "band": band,
            "chi2": float(chi2), "p_value": float(p_value), "table": table}


def benford_simulated_p(mad: float, n: int, digits: int = 1, n_sims: int = 10_000, seed: int = 0) -> tuple[float, float]:
    """Size-adjusted check of a MAD value.

    Draws n_sims samples of size n exactly from Benford proportions. Returns
    the share of them with MAD >= mad, as (k + 1) / (n_sims + 1), and their
    median MAD. Needed because small samples have large MADs even when they
    follow Benford's law, which the fixed Nigrini bands do not allow for.
    """
    p = benford_expected(digits).to_numpy()
    rng = np.random.default_rng(seed)
    sims = np.abs(rng.multinomial(n, p, size=n_sims) / n - p).mean(axis=1)
    return float((np.sum(sims >= mad) + 1) / (n_sims + 1)), float(np.median(sims))


def benford_by_agency(df: pd.DataFrame, min_rows: int = 300, min_amount: float = 10.0,
                      value_col: str = "awarded_amt", agency_col: str = "agency") -> pd.DataFrame:
    """First-digit and first-two-digit Benford tests per agency, sorted by first-digit MAD (largest first).

    Only agencies with at least min_rows values >= min_amount are tested.
    sim_p_* is the size-adjusted check from benford_simulated_p; mad_*_if_benford
    is the median MAD of exact-Benford samples of the same size.
    """
    kept = df[pd.to_numeric(df[value_col], errors="coerce") >= min_amount]
    counts = kept[agency_col].value_counts()
    rows = []
    for agency in counts[counts >= min_rows].index:
        values = kept.loc[kept[agency_col] == agency, value_col]
        row = {agency_col: agency, "n": len(values)}
        for digits in (1, 2):
            r = benford_mad(values, digits, min_amount)
            sim_p, typical = benford_simulated_p(r["mad"], r["n"], digits)
            row.update({f"mad_{digits}": r["mad"], f"mad_{digits}_if_benford": typical, f"band_{digits}": r["band"],
                        f"p_{digits}": r["p_value"], f"sim_p_{digits}": sim_p})
        rows.append(row)
    return pd.DataFrame(rows).sort_values("mad_1", ascending=False).reset_index(drop=True)


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
