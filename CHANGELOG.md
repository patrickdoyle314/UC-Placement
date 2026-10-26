# Changelog

All notable changes to this project. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
dates are when the change was made.

## [Unreleased]

Nothing yet.

## [0.4.2] - 2026-10-26

### Changed
- Comments for readers learning Python: every Python and SQL file now opens with a "HOW TO READ THIS FILE"
  block (business purpose, layout, Python ideas used), with notes through the code on why each step exists
  and which Python, pandas or SQL technique it uses. README gains a "Reading the code" section.
- The notebook builder's comments also appear inside the notebook's code cells; `notebooks/week2_eda.ipynb`
  was regenerated with identical outputs and byte-identical figures.
- Comments and docstrings only: syntax trees match the previous version file by file (notebook cell code
  included; SQL compared without comments); tests pass.

## [0.4.1] - 2026-10-25

### Changed
- Repository made public on GitHub at the project owner's direction (was private pending sign-off).
  README and problem statement status updated; the alignment notes with MP stay local and unpublished.

## [0.4.0] - 2026-10-25 (Week 2: exploratory analysis)

### Added
- `notebooks/week2_eda.ipynb`: five findings, each with a chart (national releases by year, top state shares,
  top 20 counties over time, listed vs other counties, state and county maps); outputs saved in the notebook.
- `notebooks/build_week2_eda.py`: builds and runs the notebook so it stays reproducible.
- `results/figures/week2_*.png`: the notebook's charts.
- `data/raw/geo/`: Census Bureau 2023 cartographic boundary files (states and counties, 1:20m), not committed.
- `requirements.txt`: GeoPandas, and nbformat / nbclient / ipykernel for building the notebook.

### Changed
- README status: Weeks 1–3 done (Week 3 had landed before Week 2).

## [0.3.0] - 2026-10-23

### Added
- `src/measure.py` (pandas + NumPy): concentration (HHI, effective number, Gini, top-10 share, Lorenz) and
  persistence (Spearman, Kendall) by fiscal year; writes the parquet table.
- `src/share_baseline.py`: share model baselines and backtest (last year's shares: 0.212 share points).
- `docs/MODEL_CARD_share_model.md`: model card, including the planned Dirichlet-multinomial model.
- `sql/state_ranks.sql`: CTEs and window functions (`RANK`, `LAG`, running `SUM`) over parquet with DuckDB;
  `src/run_sql.py` runs it.
- `tests/`: pytest checks (metrics, reconciliation, SQL matches pandas).
- `results/`: aggregate outputs.
- `requirements.txt`: pandas, pyarrow, DuckDB, pytest.

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
