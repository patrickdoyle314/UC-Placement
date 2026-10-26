# Problem statement: Where Unaccompanied Children Are Placed

**Status:** draft (Week 1). The repository was made public on October 25, 2026, at the project owner's
direction; the approval table below is for the owner to complete.
**Date:** October 22, 2026. Plan of record: `docs/portfolio_plan_2026-10-20.docx`.

## Question

Where in the United States are unaccompanied children released to sponsors, how concentrated
and how stable is that pattern from year to year, and what would a future rise in national
volume mean for local services: schools, legal aid and case management?

## Why it matters

Children released to sponsors enroll in local schools and need legal and case-management
services in the communities that receive them. Those communities have to plan capacity before
volumes change. National releases have ranged from 16,864 (FY2020) to 127,512 (FY2022), and ORR
reported 106 releases in October 2025. The project studies the historical record and builds
scenarios. It does not forecast next month.

## Scope

- **Population:** unaccompanied children released from ORR custody to sponsors, FY2015–FY2025
  (FY2014 is also in the source file and is kept for reference).
- **Geography:** states, and counties that received 50 or more children in a year. All other
  counties in a state are one "other counties" group, never split further.
- **Measures:** releases to sponsors per fiscal year (October–September); school-age population
  (ages 5–17) for context.
- **Deliverables:** documented Python repository and README; analysis notebook (trends,
  concentration, persistence, geography); share model with uncertainty; scenario app; short
  write-up and 15-minute demo.

## Out of scope

- Anything that could locate a child, sponsor or household.
- Program data, internal knowledge, or anything learned on the job.
- Estimating counties below the 50-release threshold.
- Policy conclusions or assigning blame.

## Data

| Source | Use |
|---|---|
| Migration Policy Institute, *Unaccompanied Children Released to Sponsors by State and County, FY 2014–2025* (tabulation of ACF/ORR data) | Core release counts by state and county |
| Census Bureau, Vintage 2024 county population estimates by age | County FIPS codes, total and school-age population |
| ORR Facts and Data; CBP Southwest Border Encounters | National context and leading indicator (later weeks) |
| Census American Community Survey, 5-year | Language spoken at home (pending; needs a free Census API key) |

## Guardrails

Public, aggregate data only. Service planning only. ORR's 50-release threshold is respected and
never reversed. Neutral language: "unaccompanied children", "released to sponsors". Counts
describe communities' service needs, not the communities themselves. FSO and contract-lead
sign-off is recorded before anything is published.

## Success criteria

State and county totals reconcile to the source for every year. Concentration and persistence
are measured and explained for every year. The share model beats "last year's shares" on
held-out years, or the write-up explains why not. 80% scenario ranges cover about 80% of
held-out actuals. The app runs from a clean install.

## Approval

| Role | Name | Decision | Date |
|---|---|---|---|
| FSO | | | |
| Contract lead | | | |
