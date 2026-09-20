import pandas as pd

from audit_tests import incumbency, risk_scores, round_number_shares
from categories import classify_descriptions


def test_round_number_shares_counts_exact_multiples():
    df = pd.DataFrame({"awarded_amt": [1000.0, 2500.0, 20000.0, 999.99, 10000.0, 5.0], "agency": ["A"] * 6})
    got = round_number_shares(df, group_col=None).iloc[0]
    assert got["n"] == 5  # the S$5 amount is below the S$10 floor
    assert got["n_x1000"] == 3 and got["n_x10000"] == 2


def _pair_rows():
    rows = []
    for year in ["FY2021", "FY2022", "FY2023", "FY2024", "FY2025"]:
        rows.append(("A", "LONG RUNNER", year, 90.0, f"t-long-{year}"))
        rows.append(("A", "SMALL FRY", year, 2.0, f"t-small-{year}"))
    rows.append(("B", "THREE YEARS ONLY", "FY2021", 100.0, "t-b"))
    return pd.DataFrame(rows, columns=["agency", "supplier_name", "fiscal_year", "awarded_amt", "tender_no"])


def test_incumbency_flags_long_relationships_with_a_large_share():
    got = incumbency(_pair_rows()).set_index("supplier_name")
    assert got.loc["LONG RUNNER", "years"] == 5
    assert got.loc["LONG RUNNER", "share_of_agency"] > 0.9
    assert bool(got.loc["LONG RUNNER", "flagged"]) is True


def test_incumbency_does_not_flag_a_small_share_or_a_short_relationship():
    got = incumbency(_pair_rows()).set_index("supplier_name")
    assert bool(got.loc["SMALL FRY", "flagged"]) is False  # 5 years but only about 2% of spend
    assert bool(got.loc["THREE YEARS ONLY", "flagged"]) is False  # whole agency, but one year


def test_classify_descriptions_uses_first_match_in_order():
    got = classify_descriptions(pd.Series([
        "Consultancy services for the proposed construction of a polyclinic",
        "Term contract for maintenance of fire protection systems",
        "Supply, delivery and installation of servers",
        "Supply of uniforms",
        "Rental of forklift trucks",
    ]))["category"]
    assert got.tolist() == ["consultancy", "cleaning/facilities", "IT", "supplies", "other"]


def _risk_rows():
    rows = []
    for year in ["FY2021", "FY2022", "FY2023", "FY2024", "FY2025"]:
        rows.append(("A", "DOMINANT PTE LTD", year, 100_000.0, f"t-dom-{year}", "cleaning services for offices"))
    rows.append(("B", "OTHER PTE LTD", "FY2021", 85_000.0, "t-near", "supply of office chairs"))
    rows.append(("B", "OTHER PTE LTD", "FY2021", 123_456.0, "t-plain", "supply of office chairs"))
    return pd.DataFrame(rows, columns=["agency", "supplier_name", "fiscal_year", "awarded_amt", "tender_no", "tender_description"]).assign(
        procurement_type="ETT", award_date="2021-04-01", tender_detail_status="Awarded to Suppliers")


def test_risk_scores_flags_and_weights():
    got = risk_scores(_risk_rows()).set_index("tender_no")
    dominant = got.loc["t-dom-FY2021"]
    assert bool(dominant["round_amount"]) and bool(dominant["high_share_incumbent"]) and bool(dominant["dominant_supplier_category"])
    assert not bool(dominant["near_threshold"])
    assert dominant["score"] == 3.0

    near = got.loc["t-near"]
    assert bool(near["near_threshold"]) and near["score"] == 0.5
    assert near["reasons"] == "near_threshold"

    assert got.loc["t-plain", "score"] == 0.0


def test_risk_scores_sorts_ties_by_amount():
    got = risk_scores(_risk_rows())
    ties = got[got["score"] == 3.0]["awarded_amt"].tolist()
    assert ties == sorted(ties, reverse=True)
