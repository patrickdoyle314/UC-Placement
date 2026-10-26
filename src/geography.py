"""Week 4: geography. Do releases cluster in space, and how do release shares compare with school-age population?

Spatial clustering, on the contiguous 48 states and DC (Alaska, Hawaii and the territories have no land neighbors):
  states    releases FY2015-FY2025 per 1,000 school-age children (ages 5-17, Census July 2024):
            global Moran's I, local clusters (LISA), and Moran's I for each fiscal year
  counties  years listed (0-11): in how many fiscal years a county had 50+ releases. This uses only what
            ORR publishes; counties under the threshold are never estimated. Connecticut's four listed
            counties are left off the county map (its 2023 Census geography uses planning regions).
School-age comparison: each listed county's share of national releases next to its share of the nation's
school-age population (their ratio is a location quotient), and the same for all "other counties" as one group.

Inputs : data/processed/releases_by_fy_geo.parquet (python src/measure.py), data/raw/geo/cb_2023_us_*_20m.zip
Outputs: results/moran_global.csv, moran_by_year.csv, lisa_states.csv, lisa_summary.csv, lisa_county_clusters.csv,
         school_age_comparison.csv, county_school_age_always_listed.csv, results/figures/week4_*.png
Usage  : python src/geography.py
"""
# ===================================================================================================
# HOW TO READ THIS FILE
# Business purpose: the plan's Week 4 questions. (1) Are the places that receive many children next to
# each other? If so, services such as legal aid and school support can be organized regionally. Moran's
# I answers "is there clustering overall?" and LISA (local Moran) shows where the clusters are.
# (2) How do release shares compare with the local school-age population? A county that receives 2% of
# the nation's released children and has 1% of its school-age children has a ratio of 2: its schools can
# expect twice as many newly arrived students as the county's size alone would suggest. That is a
# service-need measure, not a description of the community.
#
# Guardrails: counts below ORR's 50-release threshold are never estimated or backed out. County-level
# clustering uses only the published fact "listed or not listed" in each year.
#
# Python ideas: GeoPandas (tables with a map shape per row), spatial weights (who neighbors whom),
# esda's Moran and Moran_Local with permutation tests, a breadth-first search to group neighboring
# counties into clusters, matplotlib maps with a hand-made legend.
# ===================================================================================================
import warnings
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")  # draw to files without opening windows
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
from esda import fdr
from esda.moran import Moran, Moran_Local
from matplotlib.patches import Patch
from libpysal.weights import KNN, Queen, attach_islands

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data/processed/releases_by_fy_geo.parquet"
GEO = ROOT / "data/raw/geo"
RESULTS = ROOT / "results"
FIG = RESULTS / "figures"
FISCAL_YEARS = list(range(2015, 2026))
OFF_MAP = ("AK", "HI", "PR", "VI")  # no land neighbors, so they can't take part in a contiguity test
# Permutation tests: shuffle the values across the map 9,999 times and see how often chance alone gives
# a result as strong as the real one. The fixed seed makes every run give the same p-values.
PERMUTATIONS = 9999
SEED = 20261026
ALPHA = 0.05
QUADRANT = {1: "High-High", 2: "Low-High", 3: "Low-Low", 4: "High-Low"}  # esda's numbering of LISA quadrants
# Diverging colors (validated for color-vision deficiency): warm = high, cool = low, grey = not significant.
LISA_COLORS = {"High-High": "#e34948", "High-Low": "#f0928f", "Low-High": "#86b6ef", "Low-Low": "#256abf",
               "Not significant": "#f0efec"}
# County map: Low-Low (never-listed counties among never-listed neighbors) covers most of the rural map
# and would drown out the clusters planners need, so it is drawn with the "not significant" grey.
COUNTY_COLORS = {"High-High": LISA_COLORS["High-High"], "High-Low": LISA_COLORS["High-Low"],
                 "Low-High": LISA_COLORS["Low-High"], "Low-Low": LISA_COLORS["Not significant"],
                 "Not significant": LISA_COLORS["Not significant"]}
# Any county listed even once is above the national average (under 1 year), so "low" here means never listed.
COUNTY_LEGEND = {"High-High": "High-High: listed, among often-listed neighbors",
                 "High-Low": "High-Low: listed, among never-listed neighbors",
                 "Low-High": "Low-High: never listed, next to a cluster",
                 "Not significant": "Low-Low or not significant"}
HALO = [pe.withStroke(linewidth=2.5, foreground="white")]  # white outline keeps labels readable on any fill
# Small eastern states: label them out at sea with a leader line, offset in points (right, up).
LABEL_OFFSETS = {"DC": (-38, -16), "MD": (52, -14), "DE": (40, 4), "NJ": (34, 6), "CT": (30, 14), "RI": (30, 0)}
LABELED_CLUSTERS = 8
BLUE, ORANGE, INK, MUTED = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e"
plt.rcParams.update({"font.family": "Arial", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#c9c8c3", "axes.grid": True, "grid.color": "#e6e5e1", "axes.axisbelow": True})


# --------------------------------------------------------------------------- data and neighbors

def load() -> pd.DataFrame:
    df = pd.read_parquet(DATA)
    return df[df.fiscal_year.isin(FISCAL_YEARS)].copy()


def shapes() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """State and county shapes for the contiguous US, in an equal-area projection (EPSG:5070)."""
    st = gpd.read_file(f"zip://{GEO / 'cb_2023_us_state_20m.zip'}").to_crs(5070)
    co = gpd.read_file(f"zip://{GEO / 'cb_2023_us_county_20m.zip'}").to_crs(5070)
    st = st[~st.STUSPS.isin(OFF_MAP)].sort_values("STUSPS").reset_index(drop=True)
    co = co[~co.STUSPS.isin(OFF_MAP + ("CT",))].sort_values("GEOID").reset_index(drop=True)
    return st, co


def weights(gdf: gpd.GeoDataFrame):
    """Queen contiguity: places are neighbors if their borders touch, even at a corner.

    A few island counties touch nothing; each is linked to its nearest neighbor so it still takes part.
    Row-standardizing ("r") makes each place's neighbors count as an average, not a sum.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # libpysal warns about islands; they are handled on the next lines
        w = Queen.from_dataframe(gdf, use_index=False)
        if w.islands:
            w = attach_islands(w, KNN.from_dataframe(gdf, k=1))
    w.transform = "r"
    return w


# --------------------------------------------------------------------------- statistics

def global_moran(y, w) -> dict:
    """Moran's I: +1 = like values sit together, 0 = no pattern, negative = neighbors tend to differ."""
    np.random.seed(SEED)  # Moran's permutations use NumPy's global random generator
    m = Moran(np.asarray(y, dtype=float), w, permutations=PERMUTATIONS)
    return {"places": w.n, "moran_i": round(float(m.I), 3), "expected_i": round(float(m.EI), 4),
            "z_sim": round(float(m.z_sim), 2), "p_sim": round(float(m.p_sim), 4)}


def local_moran(y, w) -> tuple[np.ndarray, np.ndarray]:
    """LISA label per place: High-High = a high value among high neighbors, and so on; else Not significant."""
    m = Moran_Local(np.asarray(y, dtype=float), w, permutations=PERMUTATIONS, seed=SEED)
    quadrant = pd.Series(m.q).map(QUADRANT).to_numpy()
    return np.where(m.p_sim < ALPHA, quadrant, "Not significant"), m.p_sim


def lisa_summary(g, level: str) -> pd.DataFrame:
    """Places per LISA category at p < 0.05, and how many stay significant under a false discovery rate.

    Testing thousands of counties at p < 0.05 lets about 1 in 20 pass by chance; fdr() returns a stricter
    cutoff that keeps the expected share of false positives among the flagged places at 5%.
    """
    cutoff = fdr(g.p_sim.to_numpy(), ALPHA)
    return pd.DataFrame([{"level": level, "category": cat, "places_p05": int((g.lisa == cat).sum()),
                          "places_fdr05": int(((g.lisa == cat) & (g.p_sim <= cutoff)).sum()),
                          "fdr_cutoff": round(float(cutoff), 5)} for cat in QUADRANT.values()])


def connected_groups(members: np.ndarray, w) -> dict:
    """Group neighboring members into clusters (breadth-first search over the neighbor lists).

    members: positions of the places to group. Returns {position: cluster number}.
    """
    inside, group, k = set(members.tolist()), {}, 0
    for start in sorted(inside):
        if start in group:
            continue
        group[start], queue = k, [start]
        while queue:  # visit every member reachable from start through member neighbors
            i = queue.pop()
            for j in w.neighbors[i]:
                if j in inside and j not in group:
                    group[j] = k
                    queue.append(j)
        k += 1
    return group


# --------------------------------------------------------------------------- analyses

def states_analysis(df, st):
    """Releases per 1,000 school-age children by state: global and yearly Moran's I, and LISA clusters."""
    s = df[df.geo_level == "state"]
    wide = s.pivot(index="state", columns="fiscal_year", values="releases")
    pop = s.groupby("state")["pop_5_17_2024"].first()
    g = st.merge(pd.DataFrame({"releases": wide.sum(axis=1), "pop_5_17": pop}), left_on="STUSPS", right_index=True)
    g["per_1000_school_age"] = 1000 * g.releases / g.pop_5_17
    nat_rate = 1000 * g.releases.sum() / g.pop_5_17.sum()
    g["ratio_to_national"] = g.per_1000_school_age / nat_rate  # 2.0 = twice the national rate
    w = weights(g)
    overall = global_moran(g.per_1000_school_age, w)
    g["lisa"], g["p_sim"] = local_moran(g.per_1000_school_age, w)
    yearly = [{"fiscal_year": fy, **global_moran(1000 * g.STUSPS.map(wide[fy]) / g.pop_5_17, w)} for fy in FISCAL_YEARS]
    return g, w, overall, yearly


def counties_analysis(df, co):
    """Years listed (0-11) by county: global and yearly Moran's I, LISA, and High-High clusters."""
    c = df[(df.geo_level == "county") & df.county_fips.notna()]
    years = c.groupby("county_fips")["fiscal_year"].nunique()
    g = co.copy()
    g["years_listed"] = g.GEOID.map(years).fillna(0).astype(int)  # never listed -> 0 years (a published fact)
    w = weights(g)
    overall = global_moran(g.years_listed, w)
    g["lisa"], g["p_sim"] = local_moran(g.years_listed, w)
    yearly = []
    for fy in FISCAL_YEARS:  # each year: 1 if the county was listed (50+ releases), else 0
        listed = g.GEOID.isin(c.loc[c.fiscal_year == fy, "county_fips"]).astype(int)
        yearly.append({"fiscal_year": fy, "listed_counties": int(listed.sum()), **global_moran(listed, w)})

    # Group neighboring High-High counties into named regional clusters.
    hh = np.flatnonzero(g.lisa.to_numpy() == "High-High")
    g["cluster"] = pd.Series(connected_groups(hh, w)).reindex(range(len(g))).to_numpy()
    totals = c.groupby("county_fips").agg(releases=("releases", "sum"), pop_5_17=("pop_5_17_2024", "first"),
                                           county_name=("county_name", "first"))
    us_releases = df.loc[df.geo_level == "national", "releases"].sum()
    rows = []
    for k, members in g[g.cluster.notna()].groupby("cluster"):
        t = totals.reindex(members.GEOID).dropna(subset=["releases"])
        t = t.sort_values("releases", ascending=False)
        # Name a one-state cluster after its largest county; a multi-state one after the largest county in
        # each of its two largest states ("X to Y"), so a corridor is not named after one county.
        leaders = t.groupby(t.county_name.str[-2:], sort=False).head(1).county_name.tolist()
        rows.append({"group": k, "name": leaders[0] if len(leaders) == 1 else f"{leaders[0]} to {leaders[1]}",
                     "largest_counties": "; ".join(t.county_name.head(3)),
                     "states": " ".join(members.STUSPS.value_counts().index), "counties": len(members),
                     "listed_releases_fy2015_2025": int(t.releases.sum()),
                     "share_of_national_releases": round(t.releases.sum() / us_releases, 4),
                     "mean_years_listed": round(members.years_listed.mean(), 1)})
    clusters = pd.DataFrame(rows).sort_values("listed_releases_fy2015_2025", ascending=False, ignore_index=True)
    clusters.insert(0, "cluster", range(1, len(clusters) + 1))  # 1 = the cluster with the most releases
    g["cluster"] = g.cluster.map(dict(zip(clusters.group, clusters.cluster)))
    return g, w, overall, yearly, clusters.drop(columns="group")


def school_age_comparison(df) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Release share vs school-age share: listed counties and "other counties" per year; always-listed counties."""
    nat = df[df.geo_level == "national"].set_index("fiscal_year")
    us_pop = nat.pop_5_17_2024.iloc[0]
    rows = []
    for fy in FISCAL_YEARS:
        y = df[df.fiscal_year == fy]
        for level, label in (("county", "listed counties"), ("other_counties", "other counties, all states")):
            # Only places with a population figure, so both shares cover exactly the same places.
            g = y[(y.geo_level == level) & y.pop_5_17_2024.notna()]
            rel, pop = g.releases.sum() / nat.releases[fy], g.pop_5_17_2024.sum() / us_pop
            ratios = (g.releases / nat.releases[fy]) / (g.pop_5_17_2024 / us_pop)
            rows.append({"fiscal_year": fy, "group": label, "places": len(g), "release_share": round(rel, 3),
                         "school_age_share": round(pop, 3), "ratio": round(rel / pop, 2),
                         "median_place_ratio": round(ratios.median(), 2)})
    per_year = pd.DataFrame(rows)

    # Counties listed in all 11 years: their full record is published, so a cumulative ratio is exact.
    c = df[(df.geo_level == "county") & df.county_fips.notna()]
    n_years = c.groupby("county_fips").fiscal_year.nunique()
    a = (c[c.county_fips.isin(n_years[n_years == len(FISCAL_YEARS)].index)]
         .groupby(["county_fips", "county_name"], as_index=False)
         .agg(releases=("releases", "sum"), pop_5_17=("pop_5_17_2024", "first")))
    a["release_share"] = a.releases / nat.releases.sum()
    a["school_age_share"] = a.pop_5_17 / us_pop
    a["ratio"] = (a.release_share / a.school_age_share).round(2)
    a["per_1000_school_age"] = (1000 * a.releases / a.pop_5_17).round(1)
    a[["release_share", "school_age_share"]] = a[["release_share", "school_age_share"]].round(5)
    return per_year, a.sort_values("releases", ascending=False, ignore_index=True)


# --------------------------------------------------------------------------- charts

def legend_patches(colors, labels=None):
    labels = labels or {k: k for k in colors}
    return [Patch(facecolor=colors[k], edgecolor="#c9c8c3", linewidth=0.5, label=text) for k, text in labels.items()]


def chart_states(g):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout="constrained")
    g.plot(column="per_1000_school_age", cmap="Blues", linewidth=0.4, edgecolor="white", ax=axes[0], legend=True,
           legend_kwds={"shrink": 0.5, "orientation": "horizontal", "pad": 0.02,
                        "label": "Releases per 1,000 school-age children"})
    axes[0].set_title("Releases FY2015-FY2025 per 1,000 children aged 5-17", fontsize=9, loc="left")
    g.plot(color=g.lisa.map(LISA_COLORS), linewidth=0.4, edgecolor="white", ax=axes[1])
    for _, r in g[g.lisa != "Not significant"].iterrows():  # direct labels: identity never by color alone
        p = r.geometry.representative_point()
        dx, dy = LABEL_OFFSETS.get(r.STUSPS, (0, 0))
        axes[1].annotate(r.STUSPS, (p.x, p.y), xytext=(dx, dy), textcoords="offset points", ha="center",
                         va="center", fontsize=7, color=INK, path_effects=HALO,
                         arrowprops={"arrowstyle": "-", "color": MUTED, "lw": 0.5} if (dx, dy) != (0, 0) else None)
    axes[1].legend(handles=legend_patches(LISA_COLORS), loc="lower left", fontsize=7, frameon=False)
    axes[1].set_title("Local clusters (LISA, p < 0.05)", fontsize=9, loc="left")
    for ax in axes:
        ax.set_axis_off()
    fig.savefig(FIG / "week4_state_clusters.png", dpi=200, facecolor="white")
    plt.close(fig)


def chart_counties(g, st, clusters):
    fig, ax = plt.subplots(figsize=(10, 6))
    g.plot(color=g.lisa.map(COUNTY_COLORS), linewidth=0.05, edgecolor="white", ax=ax)
    st.boundary.plot(ax=ax, color="#9a9a96", linewidth=0.3)
    merged = g[g.cluster.notna()].dissolve(by="cluster")  # one shape per cluster
    for _, r in clusters.head(LABELED_CLUSTERS).iterrows():  # label the largest clusters by their anchor county
        p = merged.loc[r.cluster].geometry.representative_point()
        ax.annotate(f"{r.cluster}. {r['name']}", (p.x, p.y), xytext=(8, -2), textcoords="offset points",
                    fontsize=7, color=INK, path_effects=HALO, arrowprops={"arrowstyle": "-", "color": MUTED, "lw": 0.5})
    ax.legend(handles=legend_patches(COUNTY_COLORS, COUNTY_LEGEND), loc="lower left", fontsize=7, frameon=False)
    ax.set_title("Counties: local clusters of years listed (50+ releases), FY2015-FY2025 (LISA, p < 0.05)",
                 fontsize=9, loc="left")
    ax.set_axis_off()
    fig.text(0.99, 0.02, "Connecticut is not shown: its 2023 Census counties are planning regions that do not match the "
             "listed counties.", ha="right", fontsize=7, color=MUTED)
    fig.tight_layout()
    fig.savefig(FIG / "week4_county_clusters.png", dpi=200, facecolor="white")
    plt.close(fig)


def chart_moran_by_year(st_year, co_year):
    fig, ax = plt.subplots(figsize=(7, 2.8))
    for data, color, label in ((st_year, BLUE, "States: releases per school-age child"),
                               (co_year, ORANGE, "Counties: listed (50+) or not")):
        d = pd.DataFrame(data)
        ax.plot(d.fiscal_year, d.moran_i, color=color, lw=2, label=label)
        sig = d.p_sim < ALPHA
        ax.scatter(d.fiscal_year[sig], d.moran_i[sig], s=36, color=color, zorder=3, edgecolor="white", linewidth=1.5)
        ax.scatter(d.fiscal_year[~sig], d.moran_i[~sig], s=36, facecolor="white", edgecolor=color, linewidth=1.5,
                   zorder=3)
    ax.axhline(0, color="#c9c8c3", lw=1)
    ax.set_xticks(FISCAL_YEARS, [f"FY{str(y)[2:]}" for y in FISCAL_YEARS])
    ax.set_ylabel("Moran's I")
    ax.set_ylim(0, 0.6)
    ax.legend(loc="lower left", fontsize=8, frameon=False, title="Filled dot = p < 0.05; hollow = not significant",
              title_fontsize=7, alignment="left")
    fig.tight_layout()
    fig.savefig(FIG / "week4_moran_by_year.png", dpi=200, facecolor="white")
    plt.close(fig)


def chart_school_age(a):
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    ax.scatter(a.school_age_share, a.release_share, s=28, color=BLUE, edgecolor="white", linewidth=1, zorder=3)
    lo, hi = 0.8 * min(a.school_age_share.min(), a.release_share.min()), 1.25 * max(a.school_age_share.max(),
                                                                                     a.release_share.max())
    ax.plot([lo, hi], [lo, hi], color=MUTED, lw=1, ls="--")
    ax.annotate("ratio = 1: same share\nof releases as of\nschool-age children", (hi / 3, hi / 3), xytext=(8, -8),
                textcoords="offset points", ha="left", va="top", fontsize=7, color=MUTED)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    pct = mtick.FuncFormatter(lambda v, _: f"{v:.1%}" if v < 0.01 else f"{v:.0%}")
    ax.xaxis.set_major_formatter(pct); ax.yaxis.set_major_formatter(pct)
    ax.set_xlabel("Share of the nation's school-age children (2024)")
    ax.set_ylabel("Share of national releases, FY2015-FY2025")
    for _, r in pd.concat([a.nlargest(4, "ratio"), a.nlargest(3, "releases")]).drop_duplicates("county_fips").iterrows():
        ax.annotate(f"{r.county_name} ({r.ratio:.1f}x)", (r.school_age_share, r.release_share), xytext=(5, 2),
                    textcoords="offset points", fontsize=7, color=INK, path_effects=HALO)
    fig.tight_layout()
    fig.savefig(FIG / "week4_release_vs_school_share.png", dpi=200, facecolor="white")
    plt.close(fig)


def main():
    df = load()
    st, co = shapes()
    FIG.mkdir(parents=True, exist_ok=True)
    sg, _, s_all, s_year = states_analysis(df, st)
    cg, _, c_all, c_year, clusters = counties_analysis(df, co)
    per_year, always = school_age_comparison(df)

    pd.DataFrame([{"level": "state", "variable": "releases per 1,000 school-age children, FY2015-FY2025", **s_all},
                  {"level": "county", "variable": "years listed (50+ releases), FY2015-FY2025", **c_all}]) \
        .to_csv(RESULTS / "moran_global.csv", index=False)
    pd.concat([pd.DataFrame(s_year).assign(level="state"), pd.DataFrame(c_year).assign(level="county")]) \
        .to_csv(RESULTS / "moran_by_year.csv", index=False)
    sg[["STUSPS", "NAME", "releases", "pop_5_17", "per_1000_school_age", "ratio_to_national", "lisa", "p_sim"]] \
        .rename(columns={"STUSPS": "state", "NAME": "state_name"}).round(3) \
        .to_csv(RESULTS / "lisa_states.csv", index=False)
    clusters.to_csv(RESULTS / "lisa_county_clusters.csv", index=False)
    pd.concat([lisa_summary(sg, "state"), lisa_summary(cg, "county")]).to_csv(RESULTS / "lisa_summary.csv", index=False)
    per_year.to_csv(RESULTS / "school_age_comparison.csv", index=False)
    always.to_csv(RESULTS / "county_school_age_always_listed.csv", index=False)

    chart_states(sg)
    chart_counties(cg, st, clusters)
    chart_moran_by_year(s_year, c_year)
    chart_school_age(always)

    print("global Moran's I:", s_all, c_all, sep="\n  ")
    print("state LISA:", sg.lisa.value_counts().to_dict())
    print("county LISA:", cg.lisa.value_counts().to_dict())
    print(clusters.head(10).to_string(index=False))
    print(per_year.to_string(index=False))
    print(always.head(8).to_string(index=False))


if __name__ == "__main__":
    main()
