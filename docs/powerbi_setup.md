# Power BI setup

Steps to build the report in Power BI Desktop. Measures are in
[powerbi_measures.md](powerbi_measures.md).

## 1. Refresh the exports

```bash
python src/run_pipeline.py        # only needed if the data changed
python src/export_powerbi.py      # writes pbi/tenders.csv and pbi/dim_date.csv
```

## 2. Import three files

Home > Get data > Text/CSV, once per file. Set the encoding to UTF-8 and check
that `awarded_amt` arrives as a decimal number and `award_date` as a date.

| Table name | File | Grain |
|---|---|---|
| `Awards` | `data/processed/gebiz_cleaned.csv` | one row per award line item (17,825) |
| `Tenders` | `pbi/tenders.csv` | one row per tender (11,413) |
| `Dates` | `pbi/dim_date.csv` | one row per calendar day (1,826) |

## 3. Create two relationships

Model view, drag the field on the left onto the field on the right:

| From | To | Cardinality | Direction |
|---|---|---|---|
| `Awards[tender_no]` | `Tenders[tender_no]` | many to one | single |
| `Awards[award_date]` | `Dates[date]` | many to one | single |

Then mark `Dates` as a date table (Table tools > Mark as date table, date
column `date`). Without this, time comparisons can silently give wrong answers.

A tender has several award rows when it was awarded by items, which is why
`Awards` is the many side. Filter by category, fiscal year or a red flag on
`Tenders`, and the related award rows follow.

## 4. Add the measures

New measure, one per block in `powerbi_measures.md`. Check `Total Awarded`
against 123,821,872,772 and `Tender Count` against 11,413 before going on: if
those two are right, the import and the relationships are right.

## 5. Suggested pages

1. **Overview** — cards for Total Awarded, Tender Count, Distinct Suppliers;
   a column chart of Total Awarded by fiscal year; a table of the largest
   suppliers. Slicers for fiscal year and category.
2. **Concentration** — a table of agencies with HHI, CR4 % and award count,
   sorted by HHI, with a category slicer so concentration can be read within a
   category rather than across an agency's unrelated purchases.
3. **Thresholds** — a histogram of tender totals between S$81,000 and S$99,000
   with a line at S$90,000, next to Near-Threshold Tenders. The Python result
   is that tenders do not bunch below the line, and the page should show that
   plainly rather than implying otherwise.
4. **Audit sample** — tenders with a score of 1 or more, showing the reasons
   column, with slicers for each flag. Label the page as a sampling aid.

## 6. Screenshots

Export each page (File > Export > Export to PDF, or a screen capture) and save
the images to `outputs/figures/` as `powerbi_<page>.png`. They are then added
to the README.

## Notes

- Interface-record tenders (504 of them) carry no procurement code, and their
  flags are false. Use `Tenders[is_ett]` to include or exclude them.
- `Awards[supplier_name]` is normalised for formatting only. Two spellings of
  the same company that the rule did not catch still count as two suppliers,
  so concentration figures are a lower bound.
