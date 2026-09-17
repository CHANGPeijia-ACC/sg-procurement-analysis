"""Audit screening tests on the cleaned GeBIZ data.

Each function returns a DataFrame. Results are screening signals for
choosing what to look at, not evidence of irregularity.
"""

from __future__ import annotations

import pandas as pd


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
