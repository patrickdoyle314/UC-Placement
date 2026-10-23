# Changelog

All notable changes to this project. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
dates are when the change was made.

## [Unreleased]

Nothing yet.

## [0.2.1] - 2026-10-22

### Added
- `requirements.txt`, including `matplotlib` and `python-docx` for reporting, `scipy` for analysis and backtests,
  and `libpysal` for spatial weights (Week 4 Moran's I and LISA; brings in `geopandas`, `shapely`, `pandas`).

## [0.2.0] - 2026-10-22

### Added
- `docs/modeling_candidates.md`: ranked predictive candidates for service planning.
- `src/probes/share_backtest.py`: how predictable next year's state and county shares are (last year's shares: 0.206 share-point error at state level).

## [0.1.1] - 2026-10-22

### Added
- Private GitHub repository (github.com/patrickdoyle314/UC-Placement); public only after FSO and
  contract-lead sign-off.
- README section "Built alongside another project", linking to the MP repository.

### Changed
- README and problem statement status: private on GitHub instead of local only.

## [0.1.0] - 2026-10-22 (Week 1: scope and data assembly)

### Added
- Project folder, separate from the MP project and adjacent to it (`../MP`).
- `docs/portfolio_plan_2026-10-20.docx`: plan of record.
- `docs/problem_statement.md`: one-page problem statement, draft for FSO and contract-lead review.
- `data/raw/mpi/`: MPI release file, FY2014–FY2025 (133,945 bytes, downloaded 2026-10-22).
- `data/raw/census/cc-est2024-agesex-all.csv`: Census Vintage 2024 county population by age.
- `src/build_dataset.py`: one row per fiscal year × geography, keyed by county FIPS; "other counties"
  row per state; Census total and ages 5–17 population joined; reconciliation and unmatched-county reports.
- `exchange/` (contract v1.0, same core as MP's) and `exchange/export_exchange.py`.
- `alignment/align_mp.py`: coincidence checks that read only the two exchange outboxes and use MP's
  child measures only. Local only.

### Moved
- From MP: the MPI file (was `MP/data/mpi/`) and the alignment notes (was `MP/alignment/`).
  The old MP alignment script, which read MP's person-level table, is replaced by `alignment/align_mp.py`.

### Found
- 648 of 648 reconciliation checks pass once Puerto Rico and the U.S. Virgin Islands are included.
- 4 Connecticut counties have no FIPS match (Census uses planning regions since 2022).
- The MPI file includes FY2014, which the plan lists as unavailable.

### Pending
- FSO and contract-lead approval of the problem statement.
- ACS language-spoken-at-home join (needs a Census API key).
- Connecticut county-to-planning-region crosswalk.
