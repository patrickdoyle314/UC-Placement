# Model card: release share model

*Status: baseline stage built (Week 3 groundwork); Bayesian model planned for Week 5. Last updated 2026-10-23.*

## Purpose

Predict each state's share of next year's releases of unaccompanied children to sponsors, so that a
national volume scenario can be turned into expected releases, and service needs, by state (Week 6).
**Service planning only.** The model works on aggregate public counts and never on individual children,
sponsors or households.

## Data

| Item | Value |
|---|---|
| Source | Migration Policy Institute tabulation of ACF/ORR releases to sponsors, FY2014–FY2025 (`data/raw/mpi/`) |
| Unit | State × federal fiscal year (October–September); 50 states and DC |
| Years used | FY2015–FY2025 (FY2014 kept for reference) |
| Prepared by | `src/build_dataset.py` (reshape, reconcile), `src/measure.py` (parquet) |
| Excluded | Puerto Rico and the U.S. Virgin Islands (1–9 releases a year) |

## What the data looks like

From `src/measure.py` (`results/concentration_by_year.csv`, `results/persistence_state_ranks.csv`):

- **Concentrated, slowly spreading.** State HHI is 0.058–0.074 (equivalent to 13.5–17.3 equal-sized
  states). The 10 largest states took 75% of releases in FY2016 and 64% in FY2024.
- **Very stable ranks.** Spearman rank correlation of state shares between consecutive years is
  0.985–0.996 (Kendall 0.910–0.962). That stability is why "last year's shares" is hard to beat.

## Stage 1: baselines (built)

`src/share_baseline.py`. Each held-out year FY2018–FY2025 is predicted from earlier years only.

| Method | Prediction for year *t* |
|---|---|
| naive | $\hat p_{s,t} = p_{s,t-1}$ (the plan's baseline) |
| mean3 | $\hat p_{s,t} = \tfrac13 \sum_{k=1}^{3} p_{s,t-k}$ |
| pooled | $\hat p_{s,t} = \sum_{u<t} y_{s,u} \big/ \sum_{s'} \sum_{u<t} y_{s',u}$ |

where $y_{s,t}$ is releases and $p_{s,t} = y_{s,t} / \sum_{s'} y_{s',t}$. A small constant (1e-4) is added
before renormalizing so no state gets zero probability.

**Scores** (release-weighted means over held-out years, `results/share_baseline_summary.csv`):

| Method | Mean absolute error (share points) | Log score per release |
|---|---|---|
| **naive** | **0.212** | **−3.168** |
| mean3 | 0.227 | −3.169 |
| pooled | 0.294 | −3.177 |

Mean absolute error is the average over states of $|\hat p_{s,t} - p_{s,t}|$; the log score is
$\frac{1}{Y_t}\sum_s y_{s,t} \log \hat p_{s,t}$, the average log-probability the forecast gave each actual
release (higher is better; a uniform forecast over 51 states scores $\log(1/51) = -3.93$).
An earlier probe (`src/probes/share_backtest.py`, held-out FY2017–FY2025) gave 0.206 for naive; the
difference is only the held-out window.

## Stage 2: Bayesian share model (planned, Week 5)

A Dirichlet-multinomial model in PyMC, scored against the naive baseline with the same backtest:

$$
\mathbf{y}_t \sim \text{DirichletMultinomial}\big(Y_t,\ \kappa\,\boldsymbol{\mu}_t\big), \qquad
\boldsymbol{\mu}_t = \operatorname{softmax}\big(\alpha_s + \rho\,\log p_{s,t-1}\big)
$$

- $\boldsymbol{\mu}_t$: expected shares, built from last year's shares ($\rho$ near 1 means "like last
  year") and a state effect $\alpha_s$ that pools toward each state's long-run share.
- $\kappa$: concentration; small $\kappa$ means year-to-year shares vary more than counts alone imply.
- County shares within a state follow the same form, with "other counties" as one category.
- Output: posterior predictive shares with 80% intervals, checked for calibration (about 80% of held-out
  actuals inside the 80% interval) and diagnosed with ArviZ ($\hat R$, effective sample size).

The model is worth using only if it beats 0.212 share points, or if its intervals are well calibrated
where the baseline gives none.

## Limitations

- **First release location only.** Later moves are not in the data.
- **Suppressed counties.** Counties with fewer than 50 releases are never estimated; they stay one
  "other counties" category (plan guardrail).
- **Regime changes.** FY2020 (16,864) and FY2025 (24,259) were low-volume years; shares held steady
  through them, but a policy change could shift where children are released.
- **Not a forecast of volume.** National volume comes from scenarios (lowest, median, highest year),
  not from this model.

## Reproduce

```bash
pip install -r requirements.txt
python src/build_dataset.py
python src/measure.py
python src/share_baseline.py
python src/run_sql.py          # sql/state_ranks.sql
python -m pytest
```
