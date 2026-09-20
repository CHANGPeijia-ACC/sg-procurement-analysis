"""The SQL queries and the pandas functions must produce the same numbers.

Two independent implementations agreeing is the point of this file: a mistake
in either one shows up as a mismatch.
"""

from pathlib import Path

import pandas as pd
import pytest

from analysis import aggregate_by_tender, concentration_by_group, threshold_window_counts, top_suppliers, yearly_trend
from run_sql import load_awards, run_query

PROCESSED_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "gebiz_cleaned.csv"


def _toy_awards() -> pd.DataFrame:
    rows = []
    for i in range(12):  # agency A: 12 awards, so it passes the 10-award filter
        rows.append({
            "tender_no": f"A{i:03d}", "agency": "Agency A", "supplier_name": f"SUPPLIER {i % 4}",
            "fiscal_year": f"FY202{1 + i % 3}", "awarded_amt": 10_000.0 * (i + 1),
            "procurement_type": "ETT", "award_date": "2021-04-01",
            "tender_detail_status": "Awarded to Suppliers", "tender_description": "supply of things",
        })
    for i, amount in enumerate([88_000.0, 90_000.0, 95_000.0]):  # around the threshold
        rows.append({
            "tender_no": f"B{i:03d}", "agency": "Agency B", "supplier_name": "SUPPLIER X",
            "fiscal_year": "FY2021", "awarded_amt": amount, "procurement_type": "ETT",
            "award_date": "2021-04-01", "tender_detail_status": "Awarded to Suppliers",
            "tender_description": "supply of things",
        })
    return pd.DataFrame(rows)


def _assert_same(sql_result: pd.DataFrame, pandas_result: pd.DataFrame, sort_on: list[str]) -> None:
    columns = list(sql_result.columns)
    left = sql_result.sort_values(sort_on).reset_index(drop=True)[columns]
    right = pandas_result.sort_values(sort_on).reset_index(drop=True)[columns]
    pd.testing.assert_frame_equal(left, right, check_dtype=False, rtol=1e-9)


@pytest.fixture(scope="module")
def real_awards() -> pd.DataFrame:
    if not PROCESSED_PATH.exists():
        pytest.skip("processed data not present")
    return load_awards(PROCESSED_PATH)


@pytest.mark.parametrize("awards_name", ["toy", "real"])
def test_yearly_trend_matches_pandas(awards_name, real_awards):
    awards = _toy_awards() if awards_name == "toy" else real_awards
    _assert_same(run_query("yearly_trend", awards), yearly_trend(awards), ["fiscal_year"])


@pytest.mark.parametrize("awards_name", ["toy", "real"])
def test_agency_concentration_matches_pandas(awards_name, real_awards):
    awards = _toy_awards() if awards_name == "toy" else real_awards
    sql_result = run_query("agency_concentration", awards)
    expected = concentration_by_group(awards, ["agency"], min_awards=10)
    _assert_same(sql_result, expected, ["agency"])


@pytest.mark.parametrize("awards_name", ["toy", "real"])
def test_threshold_windows_match_pandas(awards_name, real_awards):
    awards = _toy_awards() if awards_name == "toy" else real_awards
    tenders = aggregate_by_tender(awards).query("procurement_type == 'ETT'")
    expected = pd.concat([threshold_window_counts(tenders, [90_000], window_pct=w) for w in (0.10, 0.05, 0.02)])
    _assert_same(run_query("threshold_windows", awards), expected, ["window_pct"])


@pytest.mark.parametrize("awards_name", ["toy", "real"])
def test_top_suppliers_match_pandas(awards_name, real_awards):
    awards = _toy_awards() if awards_name == "toy" else real_awards
    _assert_same(run_query("top_suppliers", awards), top_suppliers(awards, 10), ["supplier_name"])


def test_toy_threshold_counts_are_what_we_expect():
    # The toy tenders near the line are 88,000 and 95,000 from agency B and two
    # at exactly 90,000 (agency A's ninth award and agency B's second).
    # +/-10% spans 81,000 to 99,000: 88,000 below; both 90,000s and 95,000 above.
    # +/-2% spans 88,200 to 91,800: nothing below; both 90,000s above.
    result = run_query("threshold_windows", _toy_awards()).set_index("window_pct")
    assert (result.loc[0.10, "n_just_below"], result.loc[0.10, "n_just_above"]) == (1, 3)
    assert (result.loc[0.02, "n_just_below"], result.loc[0.02, "n_just_above"]) == (0, 2)
