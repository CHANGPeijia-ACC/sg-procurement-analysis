"""Data cleaning functions for the GeBIZ procurement dataset.

Rules here follow the decisions recorded in notes.md, in particular:
- normalize_supplier only touches punctuation/case/whitespace/suffix spelling
  around an otherwise-identical name string. It never merges names based on
  partial or keyword similarity (e.g. "ACCENTURE SG SERVICES PTE. LTD." and
  "ACCENTURE PTE LTD" are different registered entities and must stay apart).
- drop_invalid removes "Awarded to No Suppliers" rows (no award happened),
  but keeps genuine $0 line items under other statuses.
"""

from __future__ import annotations

import re

import pandas as pd

NO_AWARD_STATUS = "Awarded to No Suppliers"

# tender_no is 17 characters in one of two shapes:
#   6-char agency prefix + 3-letter procurement code + 8 digits  (ACR000ETT21000001)
#   3 letters + 14 digits, no code (interface records)             (HTX00103000020914)
_TENDER_WITH_CODE = r"^[A-Z0-9]{6}([A-Z]{3})\d{8}$"
_TENDER_INTERFACE = r"^[A-Z]{3}\d{14}$"
NO_PROCUREMENT_CODE = "(no code)"

# Suffix spellings that are the same legal form ("private limited company")
# written differently. Applied after periods have been stripped, so
# "PTE. LTD." and "PTE LTD." have already collapsed to "PTE LTD" by the time
# these run.
_SUFFIX_REWRITES = [
    (re.compile(r"\bPRIVATE LIMITED\b"), "PTE LTD"),
    (re.compile(r"\bPTE LIMITED\b"), "PTE LTD"),
]


def clean_amount(series: pd.Series) -> pd.Series:
    """Strip currency symbols/thousands separators and coerce to float."""
    s = series.astype(str).str.strip()
    s = s.str.replace(r"[\$,]", "", regex=True)
    return pd.to_numeric(s, errors="coerce")


def normalize_supplier(series: pd.Series) -> pd.Series:
    """Normalize supplier name formatting without merging distinct entities.

    1. Upper-case, trim surrounding whitespace.
    2. Strip abbreviation periods ("PTE. LTD." -> "PTE LTD").
    3. Canonicalize equivalent suffix wording ("PRIVATE LIMITED" ->
       "PTE LTD"). Distinct entity types (e.g. "LLP") are left untouched.
    4. Drop remaining punctuation that carries no entity-distinguishing
       meaning (commas, parentheses) without deleting the text inside them.
    5. Collapse repeated whitespace.
    """
    s = series.astype(str).str.strip().str.upper()
    s = s.str.replace(r"\.", "", regex=True)
    for pattern, replacement in _SUFFIX_REWRITES:
        s = s.str.replace(pattern, replacement, regex=True)
    s = s.str.replace(r"[(),]", " ", regex=True)
    s = s.str.replace(r"\s+", " ", regex=True).str.strip()
    return s


def parse_dates(df: pd.DataFrame, date_col: str = "award_date") -> pd.DataFrame:
    """Parse award_date (D/M/YYYY strings) and derive Singapore fiscal year.

    SG fiscal year runs 1 Apr - 31 Mar, labelled by its starting calendar
    year (e.g. "FY2021" = 1 Apr 2021 - 31 Mar 2022).
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors="raise")
    fy_start_year = df[date_col].dt.year.where(df[date_col].dt.month >= 4, df[date_col].dt.year - 1)
    df["fiscal_year"] = "FY" + fy_start_year.astype(str)
    return df


def drop_invalid(df: pd.DataFrame, status_col: str = "tender_detail_status") -> pd.DataFrame:
    """Drop tenders with no actual award (see notes.md).

    Genuine $0 line items under other statuses are real data and are kept —
    only rows where the tender process produced no award at all are removed.
    """
    mask = df[status_col] != NO_AWARD_STATUS
    return df.loc[mask].reset_index(drop=True)


def extract_procurement_type(series: pd.Series) -> pd.Series:
    """Three-letter procurement code from tender_no (e.g. "ETT").

    Interface records carry no code and get NO_PROCUREMENT_CODE. Any other
    format raises, so a change in the source data is noticed rather than
    silently labelled.
    """
    s = series.astype(str)
    code = s.str.extract(_TENDER_WITH_CODE, expand=False)
    unknown = code.isna() & ~s.str.match(_TENDER_INTERFACE)
    if unknown.any():
        raise ValueError(f"Unrecognised tender_no format, e.g. {s[unknown].head(3).tolist()}")
    return code.fillna(NO_PROCUREMENT_CODE)


def clean_pipeline(df: pd.DataFrame) -> pd.DataFrame:
    """Run the full cleaning pipeline used by the analysis notebooks."""
    df = df.copy()
    df["agency"] = df["agency"].str.strip().str.replace(r"\s+", " ", regex=True)
    df["tender_description"] = df["tender_description"].str.strip().str.replace(r"\s+", " ", regex=True)
    df["supplier_name_raw"] = df["supplier_name"]
    df["supplier_name"] = normalize_supplier(df["supplier_name"])
    df["awarded_amt"] = clean_amount(df["awarded_amt"])
    df = parse_dates(df)
    df["procurement_type"] = extract_procurement_type(df["tender_no"])
    df = drop_invalid(df)
    return df
