# Singapore Government Procurement (GeBIZ) — Audit Analysis

Using Singapore's publicly disclosed government procurement award data, can we
identify supplier concentration, amount-threshold clustering, and Benford's-law
deviations that would be worth flagging for a closer procurement audit?

## Data

- **Source:** [data.gov.sg — Government Procurement via GeBIZ](https://data.gov.sg/datasets/d_acde1106003906a75c3fa052592f2fcb/view) (Ministry of Finance), Open Data Licence
- **Scale:** 18,464 award records, 7 columns (`tender_no`, `tender_description`, `agency`, `award_date`, `tender_detail_status`, `supplier_name`, `awarded_amt`) across **113 agencies** and **6,152 raw supplier-name strings**
- **Time span:** exactly **FY2021 – FY2025** (1 Apr 2021 – 31 Mar 2026, Singapore fiscal year). This is a rolling 5-year window data.gov.sg publishes, **not** a full historical archive — see [Limitations](#limitations)
- **Scope:** the dataset page describes the data as the open tenders called by government agencies since FY2021. Quotations and small value purchases are not included. Every coded tender number carries the code `ETT` (17,139 rows after cleaning); 686 interface-record rows have no code. No official definition of the code was found.

## Key findings

**1. Agency-level supplier concentration is often high, even with dozens of suppliers on record.**
Several agencies show HHI above 4,000 (Science Centre Board: 8,314 with 64 suppliers; Singapore Sports Council: 5,305 with 208 suppliers) — because one or two large contracts dominate *dollar* spend while many smaller suppliers share the remainder. A single whole-of-government HHI, by contrast, is close to zero and not meaningful — it conflates thousands of unrelated procurement categories.

![Supplier concentration by agency](outputs/figures/concentration_by_agency.png)

**2. At tender level, award amounts do not cluster below the S$90,000 tender threshold.**
The threshold applies to a whole procurement, so awards were summed per `tender_no` before testing (10,909 tenders coded ETT; 504 interface-record tenders without a code excluded). Within ±10%, ±5% and ±2% of S$90,000 there are fewer tenders just below than just above (±2%: 25 below, 38 above), and a one-sided binomial test of "more below than above" gives p = 0.837, 0.747 and 0.962. The same test at seven placebo thresholds between S$70,000 and S$120,000 gives p < 0.05 in 1 of 21 cases, about the number expected by chance across 21 tests. Counting individual award rows instead does show more awards below (±2%: 82 below, 51 above, p = 0.005), but that excess disappears once line items are summed per tender.

The data contains only open tenders, so it could not show avoidance of open tender in any case, and the rule is set on estimated value while the data has awarded amounts only.

![Awards near the S$90,000 threshold, row level and tender level](outputs/figures/threshold_zoom_90000.png)

**3. Benford's law holds for the bulk of awards, but only once very small amounts are excluded.**
The full dataset fails a Benford chi-square test (p < 0.0001), but that's mostly driven by thousands of small, often round-numbered line items under S$1,000 — not the kind of data Benford's law is meant to model. Excluding those, the leading-digit distribution fits Benford closely (p = 0.12).

![Leading digit vs Benford's law](outputs/figures/benford_test.png)

**4. The 10 largest suppliers by dollar value are all construction/engineering firms**, each with only 2–19 awards but S$1.4B–S$3.5B in cumulative value — consistent with a handful of infrastructure megaprojects dominating total spend, not systemic favoritism across procurement in general.

![Top 10 suppliers](outputs/figures/top_suppliers.png)

**5. Total spend rose from ~S$24B (FY2021) to ~S$31B (FY2025) while award count stayed flat** (~3,400–3,800/year) — growth is coming from larger contracts, not more of them.

![Yearly trend](outputs/figures/yearly_trend.png)

Full analysis, code, and interpretation: [`notebooks/01_procurement_analysis.ipynb`](notebooks/01_procurement_analysis.ipynb).

## Data cleaning

Full investigation and reasoning: [`notes.md`](notes.md). Summary of what `src/cleaning.py` does and why:

- **Drops 639 "Awarded to No Suppliers" rows** — these represent tenders where no award was actually made (all have `awarded_amt == 0`), not real transactions. A separate 4 rows that are legitimately $0 line items inside multi-item term contracts are kept, since dropping on "amount == 0" alone would have discarded real data.
- **Keeps rows as the unit for concentration and Benford, and uses tenders for the threshold test** — a multi-item tender spans up to 135 rows, one per supplier. Summing rows per `tender_no` is safe here: agency, award date, status and description never vary within a tender, and no supplier appears twice in the same tender.
- **Normalizes supplier-name punctuation/case/suffix spelling only** (`PTE. LTD.` / `PTE LTD` / `PRIVATE LIMITED` / `PTE. LIMITED` → one canonical `PTE LTD`) — and deliberately does **not** merge names on keyword/substring similarity. Spot checks confirmed this matters: `ACCENTURE SG SERVICES PTE LTD` and `ACCENTURE PTE LTD` are different registered entities, as are the three unrelated companies sharing the word "NCS". This rule only merged 7 groups (8 raw spellings) across all 6,152 supplier names — every one manually verified as a true formatting duplicate.
- **Strips whitespace defects in `agency`** (one agency name carried a literal trailing tab character; 356 rows had a double space) — while deliberately *not* merging agency names that look similar but represent real distinct sub-units (e.g. `Ministry of X` vs `Ministry of X - Y Division`).

**Verification matters more than the code**: see the "Cleaning verification" section of `notes.md` for the before/after supplier counts and the full list of manually-checked merges.

## Methodology

- **Concentration (HHI + CR4)**: computed per-agency, amount-weighted (not by award count), since one large contract represents more market power than many small ones. Reported alongside count-weighted numbers where they diverge — the two can tell different stories about the same agency.
- **Threshold test**: awards are summed per `tender_no`, the unit the rule applies to, then counted just below and just above S$90,000 in ±10%/±5%/±2% windows, with a one-sided binomial test against a 50/50 split. Award counts fall as amounts grow and round numbers can attract awards, so the same test is run at placebo thresholds (S$70k, 80k, 85k, 95k, 100k, 110k, 120k); S$90,000 is only notable if it stands out from them. The S$6,000 small-value-purchase limit is not tested: the data has no small value purchases or quotations, and an older undated GeBIZ guide gives a lower limit of S$3,000, so the limit in force across FY2021–FY2025 is not confirmed. Current thresholds: [MOF](https://www.mof.gov.sg/policies/government-procurement/understanding-the-procurement-process).
- **Benford's law**: chi-square goodness-of-fit test on leading digits, tested at several minimum-amount floors (S$0 / S$1,000 / S$6,000 / S$10,000) rather than a single arbitrary cutoff, since the law is not expected to hold for small, often-round-numbered transactions.

## What I corrected

The first version counted individual award rows and read the excess just below S$90,000 as consistent with avoiding open tender. The rule applies to a whole procurement and every award in this dataset already came from a tender, so the test was redone at tender level, where the excess is not present.

## Limitations

- **5-fiscal-year rolling window, not full history.** Trend conclusions ("spend is rising") describe FY2021–FY2025 only; data.gov.sg does not publish the full GeBIZ archive through this dataset.
- **Supplier concentration here is a lower bound.** Normalization is deliberately conservative — it fixes known formatting variants but does not attempt fuzzy matching, so any supplier-name variant it didn't catch (typos, unusual formatting) still splits that supplier's awards across two names, understating their true concentration. It never overstates concentration, because it never merges distinct entities.
- **Whole-of-government metrics are not meaningful.** Every concentration number should be read at the agency (or ideally procurement-category) level; a single national figure mixes incomparable procurement types.
- **Screening signals are not evidence.** A threshold excess or a Benford deviation can have ordinary explanations (budgets set at round numbers; small transactions that do not fit Benford's assumptions). These tests show where a closer look might be worthwhile; they do not establish that any award was improperly structured.
- **Awarded amount is not estimated value.** Procurement thresholds apply to estimated value excluding GST. The data has awarded amounts only, and whether they include GST is not stated. 1,782 of 10,909 ETT tenders (16.3%) were awarded at or below S$90,000.
- **Coverage is not fully documented.** MOF lists several tender types (open, selective, limited, innovative procurement partnership); the dataset page mentions open tenders only. The 504 interface-record tenders (686 rows) carry no procurement code, their nature is not documented, and they are excluded from the threshold test.
- **No ground truth for "correct" supplier identity.** Individuals/sole proprietors, foreign entities, and unregistered trade names (13.9% of rows) have no company-registration suffix to normalize against; two individuals who are actually the same person under slightly different name spellings would not be merged.

## Reproduction

```bash
git clone <this-repo>
cd sg-procurement-analysis
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv/bin/activate on macOS/Linux
pip install -r requirements.txt

python src/download.py          # fetch raw data -> data/raw/
python src/explore.py           # structural profile of the raw data
python -c "import sys; sys.path.insert(0,'src'); import pandas as pd; from cleaning import clean_pipeline; \
  df = clean_pipeline(pd.read_csv('data/raw/gebiz_procurement.csv', low_memory=False)); \
  df.to_csv('data/processed/gebiz_cleaned.csv', index=False)"
python src/make_figures.py      # regenerate outputs/figures/*.png

jupyter notebook notebooks/01_procurement_analysis.ipynb
```

`data/processed/gebiz_cleaned.csv` is committed to the repo, so the notebook
and figure script can also be run directly without re-downloading or
re-cleaning.
