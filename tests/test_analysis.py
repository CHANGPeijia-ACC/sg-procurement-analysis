import numpy as np
import pandas as pd
import pytest

from analysis import (aggregate_by_tender, benford_expected, benford_mad, cr4, hhi, leading_digit,
                      leading_digits, nigrini_band, threshold_window_counts)


def test_leading_digit_edge_values():
    got = leading_digit(pd.Series([1, 9.999, 10, 0.5, 0.3, 0.7, 1_814_961_925.0]))
    assert got.tolist() == [1, 9, 1, 5, 3, 7, 1]


def test_leading_digit_has_no_digit_for_zero_or_negative():
    assert leading_digit(pd.Series([0, -3, np.nan])).isna().all()


def test_leading_two_digits():
    assert leading_digits(pd.Series([1234.5, 10, 99.99, 15160.0]), 2).tolist() == [12, 10, 99, 15]


def test_hhi_monopoly_and_two_equal_suppliers():
    monopoly = pd.DataFrame({"agency": ["A"] * 2, "supplier_name": ["X", "X"], "awarded_amt": [40.0, 60.0]})
    split = pd.DataFrame({"agency": ["B"] * 2, "supplier_name": ["X", "Y"], "awarded_amt": [50.0, 50.0]})
    assert hhi(monopoly, ["agency"])["hhi"].iloc[0] == pytest.approx(10_000)
    assert hhi(split, ["agency"])["hhi"].iloc[0] == pytest.approx(5_000)


def test_cr4_counts_only_the_four_largest():
    df = pd.DataFrame({"agency": ["A"] * 5, "supplier_name": list("VWXYZ"), "awarded_amt": [40.0, 30.0, 20.0, 5.0, 5.0]})
    assert cr4(df, ["agency"])["cr4"].iloc[0] == pytest.approx(95.0)


def _tender_rows():
    return pd.DataFrame({
        "tender_no": ["T1", "T1", "T2"],
        "agency": ["A", "A", "B"],
        "award_date": ["2021-04-01"] * 3,
        "fiscal_year": ["FY2021"] * 3,
        "procurement_type": ["ETT"] * 3,
        "tender_detail_status": ["Awarded by Items", "Awarded by Items", "Awarded to Suppliers"],
        "tender_description": ["desc one", "desc one", "desc two"],
        "supplier_name": ["X", "Y", "Z"],
        "awarded_amt": [60.0, 40.0, 25.0],
    })


def test_aggregate_by_tender_sums_line_items():
    got = aggregate_by_tender(_tender_rows()).set_index("tender_no")
    assert got.loc["T1", "awarded_amt"] == 100.0
    assert got.loc["T1", "n_rows"] == 2 and got.loc["T1", "n_suppliers"] == 2
    assert got.loc["T2", "awarded_amt"] == 25.0


def test_aggregate_by_tender_raises_when_a_tender_has_two_agencies():
    rows = _tender_rows()
    rows.loc[1, "agency"] = "OTHER"
    with pytest.raises(ValueError, match="vary within a tender_no"):
        aggregate_by_tender(rows)


def test_threshold_window_counts_splits_at_the_threshold():
    df = pd.DataFrame({"awarded_amt": [88_000.0, 89_500.0, 90_000.0, 91_000.0, 120_000.0]})
    got = threshold_window_counts(df, [90_000], window_pct=0.10).iloc[0]
    assert (got["n_just_below"], got["n_just_above"]) == (2, 2)
    assert got["p_more_below"] == pytest.approx(0.6875)


def test_benford_expected_proportions_sum_to_one():
    for digits, groups in [(1, 9), (2, 90)]:
        expected = benford_expected(digits)
        assert len(expected) == groups
        assert expected.sum() == pytest.approx(1.0)


def test_benford_mad_is_near_zero_for_benford_shaped_data():
    expected = benford_expected(1)
    values = [digit * 10.0 for digit, share in expected.items() for _ in range(round(share * 100_000))]
    result = benford_mad(pd.Series(values), digits=1, min_amount=10)
    assert result["mad"] < 1e-5
    assert result["band"] == "close"


def test_nigrini_band_edges_go_to_the_better_band():
    assert nigrini_band(0.006, 1) == "close"
    assert nigrini_band(0.0061, 1) == "acceptable"
    assert nigrini_band(0.015, 1) == "marginal"
    assert nigrini_band(0.0151, 1) == "nonconformity"
    assert nigrini_band(0.0012, 2) == "close"
    assert nigrini_band(0.0022, 2) == "marginal"
