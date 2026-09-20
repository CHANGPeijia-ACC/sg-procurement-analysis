import pandas as pd
import pytest

from cleaning import clean_amount, drop_invalid, extract_procurement_type, normalize_supplier, parse_dates


def test_clean_amount_strips_symbols():
    got = clean_amount(pd.Series(["$1,234.50", "2000", 3.5, "", "n/a"]))
    assert got.tolist()[:3] == [1234.5, 2000.0, 3.5]
    assert got.isna().tolist()[3:] == [True, True]


def test_normalize_supplier_merges_suffix_spellings():
    variants = pd.Series(["ACME PTE. LTD.", "ACME PTE LTD", "Acme Private Limited", "ACME PTE. LIMITED", " acme  pte ltd "])
    assert set(normalize_supplier(variants)) == {"ACME PTE LTD"}


def test_normalize_supplier_keeps_different_entities_apart():
    names = pd.Series(["ACCENTURE PTE. LTD.", "ACCENTURE SG SERVICES PTE. LTD.", "NCS PTE. LTD.",
                       "NCS COMMUNICATIONS ENGINEERING PTE. LTD.", "NCS Pearson, Inc."])
    assert normalize_supplier(names).nunique() == 5


def test_normalize_supplier_keeps_llp_separate_from_pte_ltd():
    got = normalize_supplier(pd.Series(["ACME LLP", "ACME PTE LTD"]))
    assert got.nunique() == 2


def test_fiscal_year_boundary_is_1_april():
    df = pd.DataFrame({"award_date": ["31/3/2022", "1/4/2022", "31/3/2023"]})
    got = parse_dates(df)
    assert got["fiscal_year"].tolist() == ["FY2021", "FY2022", "FY2022"]


def test_extract_procurement_type_reads_code_and_marks_interface_records():
    got = extract_procurement_type(pd.Series(["ACR000ETT21000001", "CCYNYCETT20300017", "HTX00103000020914"]))
    assert got.tolist() == ["ETT", "ETT", "(no code)"]


def test_extract_procurement_type_raises_on_unknown_format():
    with pytest.raises(ValueError, match="Unrecognised tender_no format"):
        extract_procurement_type(pd.Series(["ACR000ETT21000001", "NOT-A-TENDER-NO"]))


def test_drop_invalid_removes_only_no_award_rows():
    df = pd.DataFrame({
        "tender_detail_status": ["Awarded to Suppliers", "Awarded to No Suppliers", "Awarded by Items"],
        "awarded_amt": [100.0, 0.0, 0.0],
    })
    got = drop_invalid(df)
    assert got["tender_detail_status"].tolist() == ["Awarded to Suppliers", "Awarded by Items"]
