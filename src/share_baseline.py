"""Share model, baseline stage (pandas + NumPy): predict next year's state shares from earlier years.

Methods (see docs/MODEL_CARD_share_model.md):
  naive   last year's shares (the plan's baseline to beat)
  mean3   average of the last three years' shares
  pooled  all earlier years' releases pooled
Each held-out fiscal year (FY2018-FY2025) is predicted from earlier years only and scored with
mean absolute error (share points) and log score per release (higher is better).

Usage: python src/share_baseline.py   (after src/build_dataset.py)
"""
# ===================================================================================================
# HOW TO READ THIS FILE
# Business purpose: before building a forecasting model (Week 5), set the bar it must beat. Three
# simple rules predict next year's state shares; if a model can't beat "same as last year", it is not
# worth using. The results feed docs/MODEL_CARD_share_model.md.
#
# Python ideas: pandas pivot, .loc with a condition, if/elif chains, raising an error for bad input,
# returning a tuple, release-weighted averages with groupby.
# ===================================================================================================
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EPS = 1e-4  # tiny amount added to every state so no prediction is exactly 0 (log(0) is minus infinity)
HELD_OUT = range(2018, 2026)  # three earlier years available from FY2015


# A "wide" table: one row per fiscal year, one column per state. fillna(0) treats a missing state-year
# as zero releases. The default file path lets tests pass in a different file.
def state_shares(path=ROOT / "data/processed/releases_by_fy_geo.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    s = df[(df.geo_level == "state") & ~df.state.isin(["PR", "VI"]) & (df.fiscal_year >= 2015)]
    wide = s.pivot(index="fiscal_year", columns="state", values="releases").fillna(0).astype(float)
    return wide  # rows: fiscal years, columns: states, values: releases


# Predict one held-out year from earlier years only (wide.index < fy), just as a real forecast would
# have to. The result is a share for every state, adding up to 1.
def predict(wide: pd.DataFrame, fy: int, method: str) -> np.ndarray:
    past = wide.loc[wide.index < fy]
    if method == "naive":
        counts = past.iloc[-1]
    elif method == "mean3":
        counts = past.iloc[-3:].div(past.iloc[-3:].sum(axis=1), axis=0).mean()
    elif method == "pooled":
        counts = past.sum()
    else:
        raise ValueError(method)
    p = counts.to_numpy() + EPS
    return p / p.sum()


# Two scores. MAE: the average gap between predicted and actual shares (x100 = share points). Log score:
# the average log of the share predicted for where each child was actually released; closer to 0 is
# better, and confident misses are punished hard.
def score(pred: np.ndarray, actual: np.ndarray) -> tuple[float, float]:
    share = actual / actual.sum()
    mae = float(np.mean(np.abs(pred - share)))
    log_score = float(np.sum(actual * np.log(pred)) / actual.sum())
    return mae, log_score


def backtest(wide: pd.DataFrame) -> pd.DataFrame:  # every held-out year x every method -> one row of scores
    rows = []
    for fy in HELD_OUT:
        actual = wide.loc[fy].to_numpy()
        for method in ("naive", "mean3", "pooled"):
            mae, log_score = score(predict(wide, fy, method), actual)
            rows.append({"fiscal_year": fy, "method": method, "releases": int(actual.sum()),
                         "mae_share_points": round(100 * mae, 3), "log_score": round(log_score, 4)})
    return pd.DataFrame(rows)


# Years with more releases count more. .assign adds the weighted columns, groupby sums them per method,
# and dividing by total releases gives the weighted average.
def summarize(bt: pd.DataFrame) -> pd.DataFrame:
    """Release-weighted averages over held-out years, best method first."""
    w = bt.assign(wm=bt.mae_share_points * bt.releases, wl=bt.log_score * bt.releases)
    g = w.groupby("method")[["wm", "wl", "releases"]].sum()
    out = pd.DataFrame({"mae_share_points": (g.wm / g.releases).round(3), "log_score": (g.wl / g.releases).round(4)})
    return out.sort_values("mae_share_points").reset_index()


def main():  # backtest, save the detail and the summary, print the summary
    bt = backtest(state_shares())
    (ROOT / "results").mkdir(exist_ok=True)
    bt.to_csv(ROOT / "results/share_baseline_backtest.csv", index=False)
    s = summarize(bt)
    s.to_csv(ROOT / "results/share_baseline_summary.csv", index=False)
    print(s.to_string(index=False))


if __name__ == "__main__":
    main()
