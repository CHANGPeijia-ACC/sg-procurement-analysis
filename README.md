# Singapore Government Procurement (GeBIZ) — Audit Analysis

Using Singapore's publicly disclosed government procurement award data, can we
identify supplier concentration, amount-threshold clustering, and Benford's-law
deviations that would be worth flagging for a closer procurement audit?

## Data

- **Source:** [data.gov.sg — Government Procurement via GeBIZ](https://data.gov.sg/datasets/d_acde1106003906a75c3fa052592f2fcb/view) (Ministry of Finance), Open Data Licence
- **Scale:** 18,464 award records, 7 columns (`tender_no`, `tender_description`, `agency`, `award_date`, `tender_detail_status`, `supplier_name`, `awarded_amt`) across **113 agencies** and **6,152 raw supplier-name strings**
- **Time span:** exactly **FY2021 – FY2025** (1 Apr 2021 – 31 Mar 2026, Singapore fiscal year). This is a rolling 5-year window data.gov.sg publishes, **not** a full historical archive — see [Limitations](#limitations)

## Key findings

**1. Agency-level supplier concentration is often high, even with dozens of suppliers on record.**
Several agencies show HHI above 4,000 (Science Centre Board: 8,314 with 64 suppliers; Singapore Sports Council: 5,305 with 208 suppliers) — because one or two large contracts dominate *dollar* spend while many smaller suppliers share the remainder. A single whole-of-government HHI, by contrast, is close to zero and not meaningful — it conflates thousands of unrelated procurement categories.

![Supplier concentration by agency](outputs/figures/concentration_by_agency.png)

**2. Award amounts cluster just under the S$90,000 open-tender threshold.**
Singapore's procurement rules require open tender above S$90,000 (MOF). The below:above ratio around that line *sharpens* as the window narrows (1.25x at ±10%, 1.61x at ±2%), with a visible spike in the S$88,000–S$89,000 band — a pattern consistent with (not proof of) avoiding the heavier open-tender process. No comparable pattern exists at the lower S$6,000 Small-Value-Purchase threshold.

![Award counts near the S$90,000 threshold](outputs/figures/threshold_zoom_90000.png)

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
- **Treats each row, not each `tender_no`, as the unit of analysis** — many tenders (e.g. multi-item term contracts) span dozens to 135 rows, each a distinct supplier + amount decision. Collapsing to one row per tender would require an arbitrary aggregation rule.
- **Normalizes supplier-name punctuation/case/suffix spelling only** (`PTE. LTD.` / `PTE LTD` / `PRIVATE LIMITED` / `PTE. LIMITED` → one canonical `PTE LTD`) — and deliberately does **not** merge names on keyword/substring similarity. Spot checks confirmed this matters: `ACCENTURE SG SERVICES PTE LTD` and `ACCENTURE PTE LTD` are different registered entities, as are the three unrelated companies sharing the word "NCS". This rule only merged 7 groups (8 raw spellings) across all 6,152 supplier names — every one manually verified as a true formatting duplicate.
- **Strips whitespace defects in `agency`** (one agency name carried a literal trailing tab character; 356 rows had a double space) — while deliberately *not* merging agency names that look similar but represent real distinct sub-units (e.g. `Ministry of X` vs `Ministry of X - Y Division`).

**Verification matters more than the code**: see the "Cleaning verification" section of `notes.md` for the before/after supplier counts and the full list of manually-checked merges.

## Methodology

- **Concentration (HHI + CR4)**: computed per-agency, amount-weighted (not by award count), since one large contract represents more market power than many small ones. Reported alongside count-weighted numbers where they diverge — the two can tell different stories about the same agency.
- **Threshold clustering**: counts awards within a shrinking window (±10%/±5%/±2%) around Singapore's published procurement thresholds (S$6,000 SVP limit, S$90,000 open-tender limit — [MOF](https://www.mof.gov.sg/policies/government-procurement/procurement-processes/)). A ratio that *increases* as the window narrows is the signature of deliberate clustering rather than noise.
- **Benford's law**: chi-square goodness-of-fit test on leading digits, tested at several minimum-amount floors (S$0 / S$1,000 / S$6,000 / S$10,000) rather than a single arbitrary cutoff, since the law is not expected to hold for small, often-round-numbered transactions.

## Limitations

- **5-fiscal-year rolling window, not full history.** Trend conclusions ("spend is rising") describe FY2021–FY2025 only; data.gov.sg does not publish the full GeBIZ archive through this dataset.
- **Supplier concentration here is a lower bound.** Normalization is deliberately conservative — it fixes known formatting variants but does not attempt fuzzy matching, so any supplier-name variant it didn't catch (typos, unusual formatting) still splits that supplier's awards across two names, understating their true concentration. It never overstates concentration, because it never merges distinct entities.
- **Whole-of-government metrics are not meaningful.** Every concentration number should be read at the agency (or ideally procurement-category) level; a single national figure mixes incomparable procurement types.
- **Threshold clustering and Benford deviation are screening signals, not evidence.** Both can have innocent explanations (legitimate budget negotiation toward a round number; small-transaction data simply not fitting Benford's assumptions). They indicate where a closer audit look could be worthwhile — they do not, alone or combined, establish that any specific award was improperly structured.
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
