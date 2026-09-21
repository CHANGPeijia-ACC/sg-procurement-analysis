# Singapore Government Procurement (GeBIZ) — Audit Analysis

Can Singapore's public record of government contract awards show where a
procurement audit would be worth a closer look? This project tests 18,464
award records for supplier concentration, clustering below approval
thresholds, Benford's-law deviations and several other screening signals, and
reports what the data supports and what it does not.

## Data

- **Source:** [data.gov.sg — Government Procurement via GeBIZ](https://data.gov.sg/datasets/d_acde1106003906a75c3fa052592f2fcb/view) (Ministry of Finance), Open Data Licence. Downloaded 14 September 2026; re-downloads on 17 and 20 September 2026 were byte-identical.
- **Scale:** 18,464 award records, 7 columns (`tender_no`, `tender_description`, `agency`, `award_date`, `tender_detail_status`, `supplier_name`, `awarded_amt`), 113 agencies and 6,152 raw supplier-name strings. After cleaning: 17,825 award rows in 11,413 tenders.
- **Time span:** FY2021 to FY2025 (1 April 2021 to 31 March 2026, Singapore fiscal year). This is a rolling five-year window, not a full archive — see [Limitations](#limitations).
- **Scope:** the dataset page describes the data as the open tenders called by government agencies since FY2021; quotations and small value purchases are not included. Every coded tender number carries the code `ETT` (17,139 rows after cleaning); 686 interface-record rows have no code. No official definition of the code was found.

## Key findings

**1. Agency-level supplier concentration is often high, even with dozens of suppliers on record.**
14 agencies with at least 10 awards have an HHI above 4,000 (Science Centre Board: 8,314 with 64 suppliers; Singapore Sports Council: 5,305 with 208 suppliers), because one or two large contracts dominate the dollar spend while many smaller suppliers share the rest. A single whole-of-government HHI is close to zero (69) and not meaningful: it mixes thousands of unrelated purchases.

![Supplier concentration by agency](outputs/figures/concentration_by_agency.png)

**2. At tender level, award amounts do not cluster below the S$90,000 tender threshold.**
The threshold applies to a whole procurement, so awards were summed per `tender_no` before testing (10,909 tenders coded ETT; 504 interface-record tenders without a code excluded). Within ±10%, ±5% and ±2% of S$90,000 there are fewer tenders just below than just above (±2%: 25 below, 38 above), and a one-sided binomial test of "more below than above" gives p = 0.837, 0.747 and 0.962. The same test at seven placebo thresholds between S$70,000 and S$120,000 gives p < 0.05 in 1 of 21 cases, about the number expected by chance across 21 tests. Counting individual award rows instead does show more awards below (±2%: 82 below, 51 above, p = 0.005), but that excess disappears once line items are summed per tender.

The data contains only open tenders, so it could not show avoidance of open tender in any case, and the rule is set on estimated value while the data has awarded amounts only.

![Awards near the S$90,000 threshold, row level and tender level](outputs/figures/threshold_zoom_90000.png)

**3. Award amounts of S$10 or more follow Benford's law closely overall; 8 of 18 agencies deviate more than their sample size explains.**
Across 16,057 row-level amounts of at least S$10, the first-digit MAD is 0.00221 and the first-two-digit MAD is 0.00086, both in Nigrini's "close" band; an S$1,000 floor and tender totals give the same bands. Without a floor the first-digit MAD rises to 0.01092, and 1,294 awards are recorded at exactly S$1. At agency level (18 agencies with at least 300 amounts), fixed MAD bands mislabel small samples, so each agency was compared with simulated Benford samples of the same size: 7 agencies deviate on the first digit and 6 on the first two digits at p < 0.05, 8 on either, against about one per test expected by chance (18 × 0.05). The table is in [`outputs/benford_by_agency.csv`](outputs/benford_by_agency.csv). These are screening signals, not findings about the agencies.

![First digit vs Benford's law](outputs/figures/benford_test.png)

![First two digits vs Benford's law](outputs/figures/benford_two_digits.png)

**4. The 10 largest suppliers by dollar value are construction and engineering firms**, each with only 2–19 awards but S$1.4B–S$3.5B in cumulative value, consistent with a handful of infrastructure projects dominating total spend rather than a few firms winning across procurement in general. This started as a reading of company names; classifying their tenders supports it for 9 of the 10, while the tenth has 76% of its amount under "other" because its two tender descriptions match no construction keyword.

![Top 10 suppliers](outputs/figures/top_suppliers.png)

**5. Total spend rose from about S$24B (FY2021) to about S$31B (FY2025) while the number of awards stayed roughly flat** (3,333–3,810 per year), so the growth comes from larger contracts rather than more of them.

![Yearly trend](outputs/figures/yearly_trend.png)

## Audit tests

Five screening tests, run in [`notebooks/02_audit_tests.ipynb`](notebooks/02_audit_tests.ipynb) with the code in [`src/audit_tests.py`](src/audit_tests.py). They are for deciding where to look; none of them shows that anything is wrong, and none of the results identifies any agency or supplier as a concern.

- **Round numbers.** 19.3% of award amounts of at least S$10 are exact multiples of S$1,000 and 7.1% are multiples of S$10,000 (tender totals: 21.6% and 8.8%). Across the 18 agencies with at least 300 such amounts, the S$1,000 share runs from 5.5% to 33.5%. Budgets, rate schedules and price lists all produce round amounts, so a high share is a question about how prices are set.
- **Long-running supply relationships.** 8 of 11,890 agency–supplier pairs appear in at least 4 of the 5 fiscal years and hold at least 10% of that agency's spend, across 7 agencies; the largest holds 73.1%. Most relationships are brief: 8,982 pairs appear in a single fiscal year. Multi-year term contracts produce this pattern by design.
- **Categories.** A keyword dictionary ([`src/categories.py`](src/categories.py)) labels each tender as consultancy, IT, construction, cleaning/facilities, training, supplies or "other". 37.4% stay "other". Construction is 11.4% of tenders but 57.8% of the awarded amount; consultancy, IT and training together are 22.4% of tenders and 5.2% of the amount.
- **Concentration inside categories.** Among the 215 agency × category groups with at least 10 award rows, 87 have HHI above 2,500 and 18 above 5,000. The median is highest for IT (2,844) and lowest for training (1,652). Concentration within a narrow category is easier to interpret than the agency-level figure in Finding 1, though specialised work often has few able suppliers.
- **Tender Lite at S$1 million.** No effect visible. For general goods and services, the share of tenders just below S$1 million moved from 61.3% to 67.1% after the rule started (one-sided Fisher p = 0.238); the IT control group, which the rule does not reach until after this data ends, moved the same way (55.6% to 77.8%, p = 0.244). Construction has only 2 tenders after its own start date. Awards in the six months after each start date are excluded, because the data records award dates and not the date a tender was called.

**Audit sample.** [`outputs/audit_sample.csv`](outputs/audit_sample.csv) holds the 50 highest-scoring tenders with the reasons for each. Flags: round amount (925 tenders), high-share incumbent (60), dominant supplier in an agency category (30), and near-threshold at half weight (142), which is weighted down because Finding 2 found no clustering below S$90,000. Only 14 tenders trip two flags and none trips three, so the list is those 14 followed by 36 single-flag tenders ordered by size. It is a sample-selection aid, not a ranking of risk.

## Methodology

**Cleaning** ([`src/cleaning.py`](src/cleaning.py); the full investigation is in [`notes.md`](notes.md)):

- Drops the 639 "Awarded to No Suppliers" rows, where no award was made (all have `awarded_amt` of 0). Four genuine S$0 line items inside multi-item contracts are kept, since dropping on "amount is 0" alone would discard real data.
- Keeps rows as the unit for concentration and Benford, and sums rows per `tender_no` for the threshold test. A multi-item tender spans up to 135 rows, one per supplier; agency, award date, status and description never vary within a tender, and no supplier appears twice in the same tender.
- Normalises supplier names for case, punctuation and legal-suffix spelling only (`PTE. LTD.`, `PTE LTD`, `PRIVATE LIMITED` and `PTE. LIMITED` all become `PTE LTD`), and never merges names on keyword similarity: `ACCENTURE SG SERVICES PTE LTD` and `ACCENTURE PTE LTD` are different registered entities, as are the three unrelated companies whose names contain "NCS". The rule merged 14 raw spellings into 7 names, taking the distinct supplier names from 6,152 to 6,145; every merged group was checked by hand.
- Strips whitespace defects in `agency` (one agency name carried a trailing tab; 356 rows had a double space), without merging agency names that look alike but are distinct sub-units.
- Reads the procurement code from `tender_no` and stops with an error on any format it does not recognise, so a change in the source data is noticed.

**Concentration (HHI and CR4):** amount-weighted, per agency and per agency × category, because one large contract carries more weight than many small ones. Notebook 01 also shows count-weighted figures, which rank agencies differently.

**Threshold test:** awards are summed per `tender_no`, the unit the rule applies to, then counted just below and just above S$90,000 in ±10%/±5%/±2% windows, with a one-sided binomial test against a 50/50 split. Award counts fall as amounts grow and round numbers can attract awards, so the same test is run at placebo thresholds (S$70k, 80k, 85k, 95k, 100k, 110k, 120k); S$90,000 is only notable if it stands out from them. The S$6,000 small-value-purchase limit is not tested: the data has no small value purchases or quotations, and an older undated GeBIZ guide gives a lower limit of S$3,000, so the limit in force across FY2021–FY2025 is not confirmed. Current thresholds: [MOF](https://www.mof.gov.sg/policies/government-procurement/understanding-the-procurement-process).

**Benford's law:** first-digit (1–9) and first-two-digit (10–99) tests on row-level amounts of at least S$10, with an S$1,000 floor and tender totals as checks. Each test reports the mean absolute deviation (MAD) with the Nigrini (2012) conformity bands, and a chi-square test. For a deviation of the same size, the chi-square statistic grows in proportion to the number of amounts, so with 16,057 amounts it rejects departures too small to matter (two-digit test: p = 5.4e-08 while MAD is in the "close" band). MAD does not grow with sample size, but its fixed bands are too strict for small samples: in simulation, samples of 600 amounts drawn exactly from Benford proportions fall in the two-digit nonconformity band every time. Agencies are therefore also judged by a simulated p-value, the share of 10,000 exact-Benford samples of the same size with a MAD at least as large.

**Checks on the code:** the four headline metrics are computed twice, in pandas and in SQL, and the tests fail if the two disagree. The pipeline was re-run from a fresh clone with a fresh download and reproduced every committed table and figure byte for byte.

## What I corrected

- **Threshold test, wrong unit.** The first version counted individual award rows and read the excess just below S$90,000 as consistent with avoiding open tender. The rule applies to a whole procurement and every award in this dataset already came from a tender, so the test was redone at tender level, where the excess is not present.
- **Benford, unsupported explanation.** The Benford finding previously attributed the failure on the full dataset to small, often round-numbered line items under S$1,000; round numbers were never measured. Raising the floor to S$10, which removes 1,764 amounts including 1,294 of exactly S$1, is enough to bring the first-digit test into Nigrini's "close" band.
- **Two wrong numbers.** Finding 5 gave the yearly award count as about 3,400 to 3,800; FY2022 has 3,333. The cleaning summary said normalisation merged 8 spellings; it merged 14 spellings into 7 names.
- **Two bugs in the first-digit function,** found by the unit tests: a floating-point error misread a few amounts below S$1, and the function crashed when no amount in a group was positive. Neither changed a number in this README.

## Limitations

- **Five-fiscal-year rolling window, not full history.** Trend conclusions describe FY2021–FY2025 only; data.gov.sg does not publish the full GeBIZ archive through this dataset.
- **Supplier concentration is a lower bound.** Normalisation fixes known formatting variants but does not attempt fuzzy matching, so a supplier-name variant it did not catch (a typo, unusual formatting) still splits that supplier's awards across two names. It never overstates concentration, because it never merges distinct entities.
- **Whole-of-government metrics are not meaningful.** Concentration should be read at agency level, or better at agency × category level; a single national figure mixes incomparable purchases.
- **Screening signals are not evidence.** A threshold excess or a Benford deviation can have ordinary explanations (budgets set at round numbers; small transactions that do not fit Benford's assumptions). These tests show where a closer look might be worthwhile; they do not establish that any award was improperly structured.
- **Category labels are keyword guesses.** 37.4% of tenders match no keyword, and spot-checks of 80 tenders found labels wrong in both directions: facility management at a data centre lands in IT, and a finance-system tender lands in cleaning/facilities because its description mentions maintenance. Category results are directional.
- **The risk score is not validated.** The weights are set by hand, there is nothing to test them against, and the flags fire very unevenly, so the score separates tenders only weakly.
- **Awarded amount is not estimated value.** Procurement thresholds apply to estimated value excluding GST. The data has awarded amounts only, and whether they include GST is not stated. 1,782 of 10,909 ETT tenders (16.3%) were awarded at or below S$90,000.
- **Coverage is not fully documented.** MOF lists several tender types (open, selective, limited, innovative procurement partnership); the dataset page mentions open tenders only. The 504 interface-record tenders (686 rows) carry no procurement code, their nature is not documented, and they are excluded from the threshold test.
- **No ground truth for supplier identity.** Individuals, sole proprietors, foreign entities and unregistered trade names (13.9% of rows) have no company-registration suffix to normalise against; two spellings of one person's name would not be merged.

## Reproduction

Developed on Python 3.14.6. `requirements.txt` pins the versions that produced the committed outputs, and GitHub Actions runs the tests on every push.

```bash
git clone <this-repo>
cd sg-procurement-analysis
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv/bin/activate on macOS/Linux
pip install -r requirements.txt

python src/run_pipeline.py      # clean the data, write the tables, rebuild the figures
python src/run_sql.py           # the same metrics again, in SQL
pytest tests -q                 # unit tests, plus the SQL-vs-pandas checks
```

`python src/run_pipeline.py --download` fetches a fresh copy of the raw data first. The raw file is not committed and the cleaned data in `data/processed/` is, so a clone reproduces every table and figure without downloading anything. Because the dataset is a rolling window, a later download can change any number in this README.

### Repository layout

| Path | Contents |
|---|---|
| [`src/cleaning.py`](src/cleaning.py) | cleaning rules |
| [`src/analysis.py`](src/analysis.py) | concentration, threshold test, Benford, trends |
| [`src/audit_tests.py`](src/audit_tests.py), [`src/categories.py`](src/categories.py) | audit screening tests and the category keyword dictionary |
| [`src/run_pipeline.py`](src/run_pipeline.py) | one command to rebuild every output |
| [`sql/`](sql), [`src/run_sql.py`](src/run_sql.py) | SQL versions of four metrics, run with DuckDB |
| [`tests/`](tests) | 34 pytest tests, including the SQL-vs-pandas checks |
| [`notebooks/`](notebooks) | `01_procurement_analysis` (findings 1–5) and `02_audit_tests` |
| [`data/processed/`](data/processed) | cleaned data, committed |
| [`outputs/`](outputs) | figures, `benford_by_agency.csv`, `audit_sample.csv` |
| [`pbi/`](pbi), [`docs/`](docs), [`src/export_powerbi.py`](src/export_powerbi.py) | Power BI tables, DAX measures and setup notes |
| [`notes.md`](notes.md) | the data-quality investigation behind the cleaning rules |

### SQL layer

[`sql/`](sql) recomputes four metrics — yearly trend, agency concentration, the S$90,000 threshold windows at tender level, and the largest suppliers — as DuckDB queries that read the cleaned data directly. `tests/test_sql.py` compares each one with the matching pandas function, on small hand-made data and on the committed dataset, so an error in either implementation shows up as a mismatch. `python src/run_sql.py --save` also writes the results to `outputs/sql/`.

### Power BI

A Power BI report reads the award rows from `data/processed/gebiz_cleaned.csv`, one row per tender from [`pbi/tenders.csv`](pbi/tenders.csv) with its category, red flags and risk score, and a date table from [`pbi/dim_date.csv`](pbi/dim_date.csv); `python src/export_powerbi.py` rebuilds the two exports. [`docs/powerbi_measures.md`](docs/powerbi_measures.md) lists thirteen DAX measures, including HHI and CR4, each with the value it should return, and [`docs/powerbi_setup.md`](docs/powerbi_setup.md) covers the import, the relationships and four report pages.

Screenshots of the report: to be added.
