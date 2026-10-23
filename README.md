# Where Unaccompanied Children Are Placed

Where unaccompanied children were released to sponsors across U.S. states and counties,
FY2015–FY2025, and what a future rise in national volume would mean for local services
(schools, legal aid, case management). Service planning only.

- Plan of record: [`docs/portfolio_plan_2026-10-20.docx`](docs/portfolio_plan_2026-10-20.docx)
- Problem statement (Week 1, draft for approval): [`docs/problem_statement.md`](docs/problem_statement.md)
- Changes: [`CHANGELOG.md`](CHANGELOG.md)

**Status:** Week 1 (scope and data assembly) done, pending FSO and contract-lead approval.
This repository is **private** on GitHub until sign-off is recorded; it becomes public only after that.

## Built alongside another project

This project is being built alongside **[MP](https://github.com/patrickdoyle314/MP)**, a separate
project on open missing-person cases for children and young adults. The two stay separate: each has
its own data, code, README and changelog. They communicate only through aggregate tables under the
shared contract in [`exchange/EXCHANGE.md`](exchange/EXCHANGE.md); no individual records pass between
them, and MP's adult figures never enter this project's comparisons.

## Guardrails

These apply to every file, chart and write-up in this project:

1. **Public, aggregate data only.** No program data, internal knowledge, screenshots, or anything learned on the job.
2. **Service planning only.** Never framed as, or usable as, a tool for locating children, sponsors or households.
3. **Respect ORR's threshold.** Counties with fewer than 50 releases are not published, and their counts are never backed out.
4. **Neutral language.** "Unaccompanied children", "released to sponsors"; describe patterns, not blame.
5. **Counts are service needs,** not characteristics of the communities.

## Layout

```
UC-Placement/
  README.md, CHANGELOG.md
  docs/                 plan of record (.docx, kept local), problem statement
  src/build_dataset.py  Week 1: reshape MPI data, add other-counties rows, join Census
  data/raw/             downloaded sources (not committed; see Data)
  data/processed/       generated tables (not committed)
  exchange/             contract and export for adjacent projects (see Exchange)
  alignment/            local-only coincidence notes with the MP project (not committed)
```

## Data

| Source | File | Notes |
|---|---|---|
| [Migration Policy Institute: Released to Sponsors by State and County, FY 2014–2025](https://www.migrationpolicy.org/data-tool/unaccompanied-children-state-county) | `data/raw/mpi/mpi-data-hub_uacsbystate-county-fy2014-fy2025.xlsx` (133,945 bytes, downloaded 2026-10-22) | Tabulation of ACF/ORR data. Counties listed only for years with ≥ 50 releases. First release location only. Includes FY2014, Puerto Rico and the U.S. Virgin Islands. |
| [Census Bureau Vintage 2024 county estimates by age and sex](https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/counties/asrh/) | `data/raw/census/cc-est2024-agesex-all.csv` | County FIPS codes; July 1, 2024 total and ages 5–17 population. Covers the 50 states and DC only. |
| Census ACS 5-year (language spoken at home) | — | Pending: needs a free Census API key, which you request yourself at api.census.gov. |

## Run

```bash
pip install openpyxl scipy
python src/build_dataset.py          # Week 1 table + reconciliation
python exchange/export_exchange.py   # aggregates for adjacent projects
python alignment/align_mp.py         # optional, local only: coincidence checks with MP
```

## Week 1 results

`src/build_dataset.py` writes:

- **`data/processed/releases_by_fy_geo.csv`**: 3,673 rows, one per fiscal year × geography:
  12 national, 636 state (50 states, DC, PR, VI), 2,389 county, 636 "other counties".
  Columns: `fiscal_year, geo_level, state, state_name, county_fips, county_name, county_key, releases,
  listed_counties, pop_total_2024, pop_5_17_2024`.
- **`data/processed/reconciliation.csv`**: 648 checks, **all pass**. For every state and year, listed
  counties plus "other counties" equal the state total. For every year, states sum to the national total.
- **`data/processed/county_fips_unmatched.csv`**: 389 of 393 MPI counties matched to a FIPS code. The 4
  unmatched are Connecticut counties (Fairfield, Hartford, New Haven, New London): since 2022 the Census
  reports Connecticut by planning region, not county.

Findings for the plan:

- The MPI file **includes FY2014** (53,515 releases); the plan's data table lists it as unavailable.
- MPI's national totals include Puerto Rico and the U.S. Virgin Islands (1–9 releases a year); both
  are kept as state-level rows so the totals reconcile.
- Census population is one reference year (July 1, 2024) on every row. Puerto Rico and the Virgin Islands
  have no population in this file.

## Exchange with adjacent projects

This project and the MP project (missing children and young adults, `../MP`) are **separate
projects that share aggregates only**, through the contract in
[`exchange/EXCHANGE.md`](exchange/EXCHANGE.md) (v1.0). Each writes `exchange/outbox/` and reads the
other's; no raw records cross. From MP, only **child** measures are used. Adult measures
(ages 18–25) are kept apart and never enter child comparisons.

## Alignment notes (local only)

`alignment/` holds the coincidence log between the two projects
([`alignment/README.md`](alignment/README.md)) and the script that produces it. It is excluded through
`.git/info/exclude` and is not part of this project's deliverables until sign-off covers it.
