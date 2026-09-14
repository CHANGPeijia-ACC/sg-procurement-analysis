# Data quality notes — GeBIZ procurement dataset

Working notes from manual data exploration. Each entry: what I found, why it
matters for the analysis, what I decided to do about it, and why. This is the
source material for the README's "Data cleaning" and "Limitations" sections.

## Dataset shape

- 18,464 rows x 7 columns: `tender_no`, `tender_description`, `agency`,
  `award_date`, `tender_detail_status`, `supplier_name`, `awarded_amt`.
- No missing values in any column. No negative amounts.

## Time coverage: this is a rolling 5-FY window, not a full history

`award_date` spans exactly 2021-04-01 to 2026-03-31 — precisely five Singapore
fiscal years (FY runs 1 Apr - 31 Mar), FY2021 through FY2025. This lines up
too cleanly to be coincidental: data.gov.sg republishes this dataset as a
rolling window, not a complete historical archive.

**Impact**: any "trend over time" analysis (4.4) is a 5-year window, not the
full history of GeBIZ. Framing conclusions as "over the observed period"
rather than implying a longer history is a README limitation, not just a
footnote.

**Decision**: derive fiscal year as `FY = year if month >= 4 else year - 1`,
labelled `FY2021` etc. for the Apr(year)-Mar(year+1) period.

## `tender_detail_status`: four categories, and zero-amount rows aren't all the same thing

| status | rows | zero-amount rows |
|---|---:|---:|
| Awarded to Suppliers | 9,294 | 0 |
| Awarded by Items | 7,845 | 4 |
| Award by interface record | 686 | 0 |
| Awarded to No Suppliers | 639 | 639 |

- **"Awarded to No Suppliers"** (639 rows) means the tender process completed
  with *no actual award* — these are not real transactions, just record-keeping
  for a failed/void tender. All 639 have `awarded_amt == 0`, which is
  consistent with "no award happened," not a data error.
- The other **4 zero-amount rows** sit under "Awarded by Items" — these are
  individual line items inside a multi-item term contract that were
  legitimately valued at $0 (e.g. a free/no-cost item bundled into an
  otherwise-paid contract). I checked all 4 manually (e.g. `ITE000ETT22000004`,
  a joint ITE/Polytechnic library-resources term contract with multiple
  suppliers) — the surrounding line items on the same tender have normal
  positive amounts, so these are real $0 items, not missing data.

**Decision** (`drop_invalid`): drop rows where `tender_detail_status ==
"Awarded to No Suppliers"` before any spend/concentration/Benford analysis —
they contain no real award. Keep the 4 genuine $0 line items; dropping "amount
== 0" as a blanket rule would have silently discarded real data. Also keep a
raw/pre-drop count so the README can report "N tenders had no award" as its
own small finding, separate from the spend analysis.

## `tender_no` isn't 1:1 with rows — decide the unit of analysis

12,052 unique `tender_no` values across 18,464 rows. The gap is explained by
`tender_detail_status`: "Awarded by Items" tenders are split into one row per
line item (I found one term contract, `FINVITETT25000004`, with 10 rows —
others go up to 135 rows for a single `tender_no`), and some "Awarded to
Suppliers" tenders list multiple co-awarded suppliers on separate rows.

**Decision**: the unit of analysis for concentration (4.1) and Benford (4.3)
is the **row** (one supplier + one amount = one award decision), not the
`tender_no`. A 100-line-item term contract represents 100 separate award
decisions across (possibly different) suppliers, and collapsing it to one row
per `tender_no` would need an arbitrary aggregation rule (sum? first row?)
that either double-counts or hides supplier-level detail. This does mean a
single large contract with many line items contributes many rows to the
concentration metrics — noted as a limitation, since it can inflate a
supplier's apparent award *count* (though not necessarily their award
*amount*, which is what HHI-by-amount is computed on).

No exact duplicate rows, and no duplicates on `(tender_no, supplier_name,
awarded_amt)` — so this row-level multiplicity is real structure, not a data
error.

## Supplier name variants

Spot-checked by searching for known large suppliers and by profiling suffix
patterns across all 18,464 rows.

**Formatting-only variants (safe to normalize):**

| variant | rows |
|---|---:|
| `PTE. LTD.` (with dots) | 10,129 |
| `PTE LTD` (no dots) | 3,159 |
| `PRIVATE LIMITED` | 515 |
| `PTE. LIMITED` | 118 |

These four are the same legal suffix ("private limited company") written four
different ways — collapsing them to one canonical `PTE LTD` is safe and
necessary; otherwise the same company is silently split across 2-4 name
strings and every concentration metric understates real concentration.

**Not the same thing, despite looking similar — kept separate:**

- `LLP` (493 rows) is a legally distinct entity type (limited liability
  partnership, not a private company). I did **not** fold this into
  `PTE LTD` — only cleaned its punctuation/spacing. Merging entity types
  would be wrong even though "LLP" and "PTE LTD" both mean "not a sole
  proprietor."
- **Substring/keyword similarity is not enough to merge.** Spot check:
  `ACCENTURE SG SERVICES PTE. LTD.` (43 rows) vs `ACCENTURE PTE LTD` (12
  rows) — two different registered Accenture entities in Singapore, not a
  formatting variant of each other. Similarly `NCS PTE. LTD.` (198 rows) vs
  `NCS COMMUNICATIONS ENGINEERING PTE. LTD.` (8 rows) vs `NCS Pearson, Inc.`
  (1 row) — three unrelated companies that happen to share the word "NCS"
  (the third is a US test-administration company, unrelated to Singapore's
  NCS Pte Ltd). **Rule I'm enforcing**: normalization only touches
  punctuation/case/whitespace/suffix-spelling around an otherwise-identical
  name string. It never merges names based on partial or keyword similarity,
  no matter how tempting a fuzzy match looks. This is the single most
  important rule for avoiding overstated supplier concentration.

**No recognizable company suffix at all**: 2,563 rows (13.9% of the dataset).
This bucket is a genuine mix, not one category:
- individuals / sole proprietors (e.g. `TAY KIM HUAT`, `TEO YONG MING,
  YONVIN`), including inconsistent casing (e.g. `kong poh meng` in lowercase
  while most rows are upper/title case)
- NGOs, clubs, associations (e.g. `Sentosa Golf Club`, `Association for Early
  Childhood Educators (Singapore)`)
- unregistered trade names (e.g. `CACTUS`, `GREY MATTERZ DESIGN`, `K K ART &
  DECOR`)
- foreign entities with non-SG suffixes (e.g. `Georealtime Sdn Bhd`, `Keller
  (M) Sdn. Bhd.` — Malaysian "Sdn Bhd" = private limited company equivalent)

**Decision**: normalize case/whitespace/punctuation uniformly across all of
these (so `kong poh meng` and `KONG POH MENG` at least collapse if they ever
co-occur), but do **not** attempt structural rewrites — e.g. reordering
"Lastname, Firstname" individual names, or inferring that two individual
names refer to the same person. That requires manual identity judgment this
dataset doesn't support, and guessing wrong creates exactly the kind of false
merge that inflates concentration metrics.

**Verification plan for after cleaning** (see step 3 self-check): count
distinct suppliers before/after normalization, and manually spot-check 20
merged groups to confirm none of them merge legally distinct entities. This
step matters more than the normalization code itself.

## `agency`: whitespace defects, and some near-identical names that are deliberately distinct

113 unique agency strings.

- One agency name carries a literal **trailing tab character**:
  `"Anglo-Chinese School (Independent)\t"`. Would silently create a duplicate
  "agency" if not stripped.
- 356 rows carry a **double space** inside `"Government Technology Agency
  (GovTech)"`.

**Decision**: strip leading/trailing whitespace and collapse internal
whitespace runs on `agency` (and `tender_description`) during parsing. This
is a straightforward trim, not a fuzzy-matching problem like supplier names.

**Deliberately NOT merged**: `"Info-communications Media Development
Authority"` vs `"Info-communications Media Development Authority - MDA"`, and
several `"Ministry of X - Y Division"` rows (e.g. the multiple `Ministry of
Manpower - ...` and `Ministry of Home Affairs ...` rows). These look like
near-duplicates but represent real distinct sub-units/divisions/statutory
boards procuring independently — merging them would hide real
organizational structure, the opposite mistake from the supplier case.

## Dates

Single consistent `D/M/YYYY` string format (e.g. `6/9/2021`), zero parse
failures with `dayfirst=True`. No mixed formats, no free text.

## Cleaning verification (step 3 self-check)

Ran `clean_pipeline` (src/cleaning.py) over the raw data and checked the
results before trusting them for analysis:

- **Row count**: 18,464 -> 17,825 after `drop_invalid` (639 "Awarded to No
  Suppliers" rows removed, matching the count found during exploration
  exactly — no unexpected extra drops).
- **Supplier count**: 6,152 raw distinct spellings -> 6,144 after
  `normalize_supplier` — a reduction of only 8 names across 7 merged groups.
  This is intentionally small: the rule only fixes punctuation/case/suffix
  spelling, so it should *not* collapse a large fraction of the supplier
  list. A big drop would have been a red flag for an overly aggressive rule.
- **Manually checked all 7 merged groups** (not just a sample, since there
  were only 7) — every one is a genuine formatting duplicate of the same
  entity, e.g. `Advancedata Network Sdn Bhd` / `ADVANCEDATA NETWORK SDN.
  BHD.`, `BAHWAN CYBERTEK PTE. LTD.` / `BAHWAN CYBERTEK PRIVATE LIMITED`,
  `SUEZ (SINGAPORE) SERVICES  PTE. LTD.` (double space) / `SUEZ (SINGAPORE)
  SERVICES PTE. LTD.`. None of the 7 merges combine different entities.
- **Re-checked the known-tricky cases from earlier**: `ACCENTURE PTE LTD`
  and `ACCENTURE SG SERVICES PTE LTD` are still two separate normalized
  names after cleaning (correct — they're different entities), and the
  three unrelated "NCS" companies (`NCS PTE LTD`, `NCS COMMUNICATIONS
  ENGINEERING PTE LTD`, `NCS PEARSON INC`) also remain three separate names.
- **Spot-checked 20 random raw/normalized name pairs** beyond the merged
  groups — all reasonable (suffix punctuation stripped, case unified,
  individual/no-suffix names left structurally alone as intended, e.g.
  `Suhail Jindran` -> `SUHAIL JINDRAN`, `nPlan Limited` -> `NPLAN LIMITED`).

**Conclusion**: the normalization is conservative by design — it trades a
smaller reduction in supplier count for confidence that no two distinct
companies got merged. Any concentration metric computed downstream should
therefore be read as a **lower bound** on true concentration (some
formatting variants I didn't catch, e.g. typos, may still be splitting a
supplier's awards across two name strings), not an upper bound.

## Encoding

No non-ASCII characters found in `supplier_name` (checked all rows) — the
`matplotlib` Chinese-font setup in `src/analysis.py` is precautionary only
(e.g. for chart titles I write in the notebook), not required by the raw
data itself.
