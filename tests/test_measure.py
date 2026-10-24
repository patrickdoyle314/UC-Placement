"""Tests for the metrics, the reshaped data and the SQL statement."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import measure, run_sql, share_baseline

ROOT = Path(__file__).resolve().parent.parent
HAVE_DATA = (ROOT / "data/processed/releases_by_fy_geo.parquet").exists()
needs_data = pytest.mark.skipif(not HAVE_DATA, reason="run src/build_dataset.py and src/measure.py first")


# --------------------------------------------------------------------------- metrics

def test_hhi_bounds():
    assert measure.hhi([5]) == pytest.approx(1.0)
    assert measure.hhi([1, 1, 1, 1]) == pytest.approx(0.25)


def test_gini_bounds():
    assert measure.gini([3, 3, 3]) == pytest.approx(0.0)
    assert measure.gini([0, 0, 0, 10]) == pytest.approx(0.75)


def test_top_share_and_lorenz():
    assert measure.top_share([1, 2, 3, 4], n=1) == pytest.approx(0.4)
    x, y = measure.lorenz([1, 1, 2])
    assert (x[0], y[0], x[-1], y[-1]) == (0, 0, 1, 1)
    assert np.all(np.diff(y) >= 0)


def test_baseline_predictions_are_distributions():
    wide = pd.DataFrame({"A": [10, 20, 30, 40], "B": [30, 20, 10, 0]}, index=[2015, 2016, 2017, 2018])
    for method in ("naive", "mean3", "pooled"):
        p = share_baseline.predict(wide, 2018, method)
        assert p.sum() == pytest.approx(1.0) and np.all(p > 0)
    assert share_baseline.predict(wide, 2018, "naive")[0] == pytest.approx(0.75, abs=1e-3)


# --------------------------------------------------------------------------- data and SQL

@needs_data
def test_counties_plus_other_reconcile_to_states():
    df = measure.load()
    states = df[df.geo_level == "state"].set_index(["fiscal_year", "state"])["releases"]
    parts = df[df.geo_level.isin(["county", "other_counties"])].groupby(["fiscal_year", "state"])["releases"].sum()
    assert (parts.reindex(states.index) == states).all()


@needs_data
def test_sql_matches_pandas():
    sql = run_sql.run(ROOT / "sql/state_ranks.sql")
    states = measure.state_table(measure.load())
    states["share"] = states.groupby("fiscal_year")["releases"].transform(lambda r: r / r.sum())
    states["rank_in_year"] = states.groupby("fiscal_year")["releases"].rank(method="min", ascending=False).astype(int)
    merged = sql.merge(states, on=["fiscal_year", "state"], suffixes=("_sql", "_pd"))
    assert len(merged) == len(sql) == len(states)
    assert np.allclose(merged.share_sql, merged.share_pd, atol=1e-4)
    assert (merged.rank_in_year_sql == merged.rank_in_year_pd).all()


@needs_data
def test_sql_cumulative_share_matches_top10():
    sql = run_sql.run(ROOT / "sql/state_ranks.sql")
    conc = measure.concentration(measure.state_table(measure.load()), measure.county_table(measure.load()))
    top10 = conc[conc.level == "state"].set_index("fiscal_year")["top10_share"]
    tenth = sql.sort_values(["fiscal_year", "rank_in_year", "state"]).groupby("fiscal_year").nth(9)
    assert np.allclose(tenth.set_index("fiscal_year")["cumulative_share"], top10, atol=1e-3)
