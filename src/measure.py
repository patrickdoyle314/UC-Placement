"""Week 3 measures with pandas and NumPy: how concentrated releases are, and how stable the pattern is.

Concentration, each fiscal year:
  HHI             sum of squared shares (1 = all in one place, 1/n = spread evenly over n)
  effective_n     1 / HHI, "as concentrated as this many equal-sized places"
  gini            inequality of shares, 0 (equal) to near 1 (all in one place)
  top10_share     share of releases in the 10 largest places
States: the 50 states and DC. Counties: every listed county (>= 50 releases that year) plus one
"all other counties" category, which is never split (plan guardrail).

Persistence, each pair of consecutive fiscal years: Spearman and Kendall rank correlation of state shares.

Also writes data/processed/releases_by_fy_geo.parquet for DuckDB (sql/).

Usage: python src/measure.py   (after src/build_dataset.py)
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
RESULTS = ROOT / "results"
FISCAL_YEARS = range(2015, 2026)
TERRITORIES = ("PR", "VI")


# --------------------------------------------------------------------------- metrics (pure NumPy)

def shares(values) -> np.ndarray:
    v = np.asarray(values, dtype=float)
    total = v.sum()
    return v / total if total > 0 else np.zeros_like(v)


def hhi(values) -> float:
    """Herfindahl-Hirschman index of the shares of `values`."""
    return float(np.sum(shares(values) ** 2))


def gini(values) -> float:
    """Gini coefficient of non-negative `values` (0 = all equal)."""
    v = np.sort(np.asarray(values, dtype=float))
    n = v.size
    if n == 0 or v.sum() == 0:
        return 0.0
    ranks = np.arange(1, n + 1)
    return float((2 * np.sum(ranks * v) / (n * v.sum())) - (n + 1) / n)


def top_share(values, n: int = 10) -> float:
    s = np.sort(shares(values))[::-1]
    return float(s[:n].sum())


def lorenz(values) -> tuple[np.ndarray, np.ndarray]:
    """Lorenz curve points: cumulative share of places (x) vs cumulative share of releases (y)."""
    v = np.sort(np.asarray(values, dtype=float))
    x = np.arange(0, v.size + 1) / v.size
    y = np.concatenate([[0.0], np.cumsum(v) / v.sum()])
    return x, y


# --------------------------------------------------------------------------- data

def load() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "releases_by_fy_geo.csv", dtype={"county_fips": "string"})
    df["releases"] = df["releases"].astype("int64")
    return df


def state_table(df: pd.DataFrame) -> pd.DataFrame:
    s = df[(df.geo_level == "state") & ~df.state.isin(TERRITORIES) & df.fiscal_year.isin(FISCAL_YEARS)]
    return s[["fiscal_year", "state", "releases"]].reset_index(drop=True)


def county_table(df: pd.DataFrame) -> pd.DataFrame:
    """Listed counties, plus all other counties nationally as one category per year."""
    c = df[df.fiscal_year.isin(FISCAL_YEARS)]
    listed = c[c.geo_level == "county"][["fiscal_year", "county_name", "releases"]]
    other = (c[c.geo_level == "other_counties"].groupby("fiscal_year", as_index=False)["releases"].sum()
             .assign(county_name="All other counties"))
    return pd.concat([listed, other], ignore_index=True)


# --------------------------------------------------------------------------- measures

def concentration(states: pd.DataFrame, counties: pd.DataFrame) -> pd.DataFrame:
    def per_year(g: pd.DataFrame, level: str) -> pd.Series:
        v = g["releases"].to_numpy()
        h = hhi(v)
        return pd.Series({"level": level, "places": len(v), "releases": int(v.sum()), "hhi": round(h, 4),
                          "effective_n": round(1 / h, 1), "gini": round(gini(v), 3),
                          "top10_share": round(top_share(v, 10), 3)})
    st = states.groupby("fiscal_year").apply(per_year, level="state", include_groups=False)
    co = counties.groupby("fiscal_year").apply(per_year, level="county", include_groups=False)
    return pd.concat([st, co]).reset_index().sort_values(["level", "fiscal_year"], ignore_index=True)


def persistence(states: pd.DataFrame) -> pd.DataFrame:
    wide = states.assign(share=states.groupby("fiscal_year")["releases"].transform(lambda r: r / r.sum())) \
                 .pivot(index="state", columns="fiscal_year", values="share")
    rows = []
    for a, b in zip(wide.columns[:-1], wide.columns[1:]):
        pair = wide[[a, b]].dropna()
        rows.append({"from_fy": a, "to_fy": b, "states": len(pair),
                     "spearman": round(pair[a].corr(pair[b], method="spearman"), 3),
                     "kendall": round(pair[a].corr(pair[b], method="kendall"), 3)})
    return pd.DataFrame(rows)


def main():
    df = load()
    df.to_parquet(PROCESSED / "releases_by_fy_geo.parquet", index=False)
    states, counties = state_table(df), county_table(df)
    conc, pers = concentration(states, counties), persistence(states)
    RESULTS.mkdir(exist_ok=True)
    conc.to_csv(RESULTS / "concentration_by_year.csv", index=False)
    pers.to_csv(RESULTS / "persistence_state_ranks.csv", index=False)
    with pd.option_context("display.width", 140, "display.max_columns", 20):
        print(conc.to_string(index=False))
        print()
        print(pers.to_string(index=False))


if __name__ == "__main__":
    main()
