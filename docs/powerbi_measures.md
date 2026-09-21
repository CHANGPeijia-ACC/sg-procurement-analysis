# DAX measures

Measures for the Power BI report. Table names assume the import described in
[powerbi_setup.md](powerbi_setup.md):

| Table | File |
|---|---|
| `Awards` | `data/processed/gebiz_cleaned.csv` (one row per award line item) |
| `Tenders` | `pbi/tenders.csv` (one row per tender) |
| `Dates` | `pbi/dim_date.csv` (one row per calendar day) |

Each measure lists the value it should return with no filters applied, taken
from the Python results in the README. If a measure returns something else,
the measure or the model is wrong.

## Basic measures

```dax
Total Awarded = SUM ( Awards[awarded_amt] )
```
Total awarded value. Unfiltered: 123,821,872,772.

```dax
Award Count = COUNTROWS ( Awards )
```
Award line items. Unfiltered: 17,825.

```dax
Tender Count = COUNTROWS ( Tenders )
```
Tenders. Unfiltered: 11,413, of which 10,909 have `is_ett` true.

```dax
Distinct Suppliers = DISTINCTCOUNT ( Awards[supplier_name] )
```
Unfiltered: 6,144 normalised supplier names.

```dax
Average Tender Value = DIVIDE ( [Total Awarded], [Tender Count] )
```

## Concentration

`Supplier Spend Share %` gives each supplier's share of whatever is currently
filtered, for example one agency. `REMOVEFILTERS` on the supplier column is
what turns "this supplier's spend" into "this supplier's spend out of the
whole agency".

```dax
Supplier Spend Share % =
DIVIDE (
    [Total Awarded],
    CALCULATE ( [Total Awarded], REMOVEFILTERS ( Awards[supplier_name] ) )
) * 100
```

HHI squares every supplier's percentage share and adds the results, so it runs
from near 0 to 10,000. `SUMMARIZE` lists the suppliers in the current filter,
`ADDCOLUMNS` attaches each supplier's total, and `SUMX` walks that list row by
row. This is the same calculation as `analysis.hhi()`.

```dax
HHI =
VAR SupplierTotals =
    ADDCOLUMNS (
        SUMMARIZE ( Awards, Awards[supplier_name] ),
        "@SupplierAmount", CALCULATE ( SUM ( Awards[awarded_amt] ) )
    )
VAR GroupTotal = SUMX ( SupplierTotals, [@SupplierAmount] )
RETURN
    IF (
        GroupTotal > 0,
        SUMX ( SupplierTotals, ( DIVIDE ( [@SupplierAmount], GroupTotal ) * 100 ) ^ 2 )
    )
```
Filtered to Science Centre Board: 8,314 across 64 suppliers. With no filter it
is near 69, which is why the README reads concentration per agency and not for
the whole of government.

`CR4 %` adds up the four largest suppliers' shares. `TOPN` picks those four
rows out of the same list.

```dax
CR4 % =
VAR SupplierTotals =
    ADDCOLUMNS (
        SUMMARIZE ( Awards, Awards[supplier_name] ),
        "@SupplierAmount", CALCULATE ( SUM ( Awards[awarded_amt] ) )
    )
VAR GroupTotal = SUMX ( SupplierTotals, [@SupplierAmount] )
VAR TopFour = TOPN ( 4, SupplierTotals, [@SupplierAmount], DESC )
RETURN DIVIDE ( SUMX ( TopFour, [@SupplierAmount] ), GroupTotal ) * 100
```
Filtered to Science Centre Board: 95.0.

## Audit screening

```dax
ETT Tender Count = CALCULATE ( [Tender Count], Tenders[is_ett] = TRUE () )
```
Unfiltered: 10,909.

```dax
Round Amount Share % =
DIVIDE (
    CALCULATE ( [Tender Count], Tenders[round_amount] = TRUE () ),
    [ETT Tender Count]
) * 100
```
Unfiltered: 8.5 (925 of 10,909 ETT tenders are exact multiples of S$10,000).
The README quotes 8.8% for the same flag because it counts only tenders of at
least S$10 (925 of 10,565).

```dax
Near-Threshold Tenders = CALCULATE ( [Tender Count], Tenders[near_threshold] = TRUE () )
```
Unfiltered: 142 tenders within 10% below S$90,000.

```dax
Flagged Tenders = CALCULATE ( [Tender Count], Tenders[score] >= 2 )
```
Unfiltered: 14 tenders trip two or more flags. None trips three.

## Trend

`Dates[fiscal_year_index]` numbers the fiscal years 1 to 5, so the previous
year is simply the current index minus one. `REMOVEFILTERS ( Dates )` clears
the current year filter before applying the earlier one.

```dax
Spend Previous FY =
VAR CurrentIndex = SELECTEDVALUE ( Dates[fiscal_year_index] )
RETURN
    CALCULATE (
        [Total Awarded],
        REMOVEFILTERS ( Dates ),
        Dates[fiscal_year_index] = CurrentIndex - 1
    )
```

```dax
Spend YoY % =
DIVIDE ( [Total Awarded] - [Spend Previous FY], [Spend Previous FY] ) * 100
```
By fiscal year the totals are FY2021 24.18B, FY2022 19.73B, FY2023 21.68B,
FY2024 27.35B, FY2025 30.88B, so FY2022 shows about -18% and FY2024 about +26%.

## Reading the results

Concentration, round amounts and the risk score are screening signals. A high
HHI or a flagged tender is a reason to look at a procurement, not a finding
about an agency or a supplier.
