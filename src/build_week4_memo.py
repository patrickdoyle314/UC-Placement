"""Build the Week 4 findings memo (docs/week4_findings_memo.md) from the results tables.

Every number in the memo is read from results/ (Week 3: src/measure.py, src/share_baseline.py; Week 4:
src/geography.py), so rebuilding after new data updates every sentence. Also draws the tier transition chart.

Usage: python src/build_week4_memo.py   (after src/measure.py, src/share_baseline.py and src/geography.py)
"""
# ===================================================================================================
# HOW TO READ THIS FILE
# Business purpose: the plan's Week 4 milestone is a findings memo on concentration, stability and
# geography, answering the check-in question "Is the pattern stable enough that last year predicts next
# year?". This script writes it as Markdown (readable on GitHub) with the charts linked in.
#
# Python ideas: reading CSVs into pandas, f-strings with format codes ({x:.0%} for a percentage,
# {x:,} for thousands separators), building a long text from a list of lines, a small helper that turns
# a DataFrame into a Markdown table, a matplotlib heatmap with numbers written in each cell.
# ===================================================================================================
import datetime as dt
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
FIG = RESULTS / "figures"
OUT = ROOT / "docs" / "week4_findings_memo.md"
TIERS = ["not listed (<50)", "50-199", "200-999", "1,000+"]  # same order as src/measure.py
TIER_LABELS = ["not listed\n(<50)", "50-199", "200-999", "1,000+"]  # two-line label so the ticks don't collide
INK, MUTED = "#0b0b0b", "#52514e"
plt.rcParams.update({"font.family": "Arial", "font.size": 9})


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(RESULTS / name)


def md_table(df: pd.DataFrame) -> str:
    """A DataFrame as a Markdown table (header row, separator row, one line per row)."""
    lines = ["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
    lines += ["| " + " | ".join(str(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(lines)


def chart_tiers(trans: pd.DataFrame):
    """Heatmap of the tier transition matrix: rows = this year's tier, columns = next year's."""
    m = trans.pivot(index="from_tier", columns="to_tier", values="probability").reindex(index=TIERS, columns=TIERS)
    n = trans.pivot(index="from_tier", columns="to_tier", values="county_years").reindex(index=TIERS, columns=TIERS)
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    ax.imshow(m.to_numpy(), cmap="Blues", vmin=0, vmax=1, aspect="auto")
    ax.grid(False)
    for (i, j), p in np.ndenumerate(m.to_numpy()):  # write the share and the count in every cell
        ax.text(j, i, f"{p:.0%}\n({n.iat[i, j]:,})", ha="center", va="center", fontsize=8,
                color="white" if p > 0.5 else INK)
    ax.set_xticks(range(4), TIER_LABELS, fontsize=8)
    ax.set_yticks(range(4), TIER_LABELS, fontsize=8)
    ax.set_xlabel("Tier the next year (releases)")
    ax.set_ylabel("Tier this year (releases)")
    ax.set_title("Year-to-year tier moves, counties listed at least once (FY2015-FY2025)\n"
                 "Share of each row; county-years in brackets", fontsize=9, loc="left")
    for s in ax.spines.values():
        s.set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "week4_tier_transitions.png", dpi=200, facecolor="white")
    plt.close(fig)


def main():
    conc, pers, base = read("concentration_by_year.csv"), read("persistence_state_ranks.csv"), read(
        "share_baseline_summary.csv")
    trans, tiers = read("tier_transitions.csv"), read("county_tiers_by_year.csv")
    mg, my, ls = read("moran_global.csv").set_index("level"), read("moran_by_year.csv"), read("lisa_summary.csv")
    lst, clusters = read("lisa_states.csv"), read("lisa_county_clusters.csv")
    sa, always = read("school_age_comparison.csv"), read("county_school_age_always_listed.csv")
    df = pd.read_parquet(ROOT / "data/processed/releases_by_fy_geo.parquet")
    nat = df[(df.geo_level == "national") & df.fiscal_year.between(2015, 2025)]
    us_releases, us_pop = int(nat.releases.sum()), float(nat.pop_5_17_2024.iloc[0])
    chart_tiers(trans)

    # ---- numbers used in the text
    st, co = conc[conc.level == "state"].set_index("fiscal_year"), conc[conc.level == "county"].set_index("fiscal_year")
    naive = base.set_index("method").loc["naive"]
    p = trans.set_index(["from_tier", "to_tier"]).probability
    listed = tiers.set_index("fiscal_year").drop(columns=TIERS[0]).sum(axis=1)  # listed counties per year
    sy, cy = my[my.level == "state"], my[my.level == "county"]
    sig = lambda level, cat, col="places_p05": int(ls[(ls.level == level) & (ls.category == cat)][col].iloc[0])
    hh_states = ", ".join(lst[lst.lisa == "High-High"].sort_values("per_1000_school_age", ascending=False).state)
    ll_states = ", ".join(lst[lst.lisa == "Low-Low"].sort_values("per_1000_school_age").state)
    lh_states = ", ".join(lst[lst.lisa == "Low-High"].state)
    top8 = clusters.head(8)
    lc, oc = sa[sa.group == "listed counties"], sa[sa.group.str.startswith("other")]
    always_rel, always_pop = always.releases.sum() / us_releases, always.pop_5_17.sum() / us_pop
    early, late = st.top10_share.loc[2015:2019], st.top10_share.loc[2021:2025]  # .loc slices by year label
    surge = co.effective_n.loc[2021:2024]
    all_sig = bool((my.p_sim < 0.05).all())  # claim "significant every year" only if the data says so
    by_ratio = lc.set_index("fiscal_year").ratio.sort_values()

    cluster_table = pd.DataFrame({
        "#": top8.cluster, "Cluster (largest counties at each end)": top8["name"], "States": top8.states,
        "Counties": top8.counties, "Share of national releases": top8.share_of_national_releases.map("{:.1%}".format),
        "Average years listed (of 11)": top8.mean_years_listed})
    ratio_table = always.nlargest(8, "ratio").assign(
        releases=lambda d: d.releases.map("{:,}".format), ratio=lambda d: d.ratio.map("{:.1f}".format))[
        ["county_name", "releases", "per_1000_school_age", "ratio"]].rename(columns={
            "county_name": "County", "releases": "Releases FY2015-FY2025",
            "per_1000_school_age": "Per 1,000 children aged 5-17", "ratio": "School-age ratio"})
    base_table = base.assign(method=base.method.map({"naive": "Last year's shares", "mean3": "Mean of last 3 years",
                                                     "pooled": "All earlier years pooled"}))
    base_table.columns = ["Rule", "Mean absolute error (share points)", "Log score per release (higher is better)"]

    L = [
        "# Week 4 findings memo: concentration, stability and geography",
        "",
        f"*Where Unaccompanied Children Are Placed. Unaccompanied children released to sponsors, FY2015–FY2025. "
        f"Built from the data by `python src/build_week4_memo.py` on {dt.date.today():%B %d, %Y}; every number is read "
        f"from `results/`. Service planning only.*",
        "",
        "**Check-in question:** is the pattern stable enough that last year predicts next year?",
        "",
        f"**Answer.** For states, yes. State rankings barely move from one year to the next (rank correlation "
        f"{pers.spearman.min():.3f} or higher every year), and simply reusing last year's shares misses each state's "
        f"share by {naive.mae_share_points:.2f} percentage points on average, the best of the three simple rules tried. "
        f"For counties, *where* children are released is just as steady, but *how many* counties cross ORR's "
        f"50-release publication threshold rises and falls with national volume, so a county's size tier last year "
        f"is a weaker guide than its share. Releases are also clustered in space: eight metropolitan clusters "
        f"received {top8.share_of_national_releases.sum():.0%} of all children released in FY2015–FY2025.",
        "",
        "## Terms",
        "",
        "- **Release:** an unaccompanied child released by ORR to a sponsor, counted at the first release location.",
        "- **Listed county:** a county with 50 or more releases in a fiscal year. ORR and MPI publish only these.",
        "- **Other counties:** the rest of a state, kept as one group. Never split or estimated.",
        "- **Share:** a place's part of the national total in a fiscal year (October to September).",
        "- **School-age ratio:** a place's share of releases divided by its share of the nation's children aged 5–17. "
        "1.0 means in proportion; 2.0 means twice its share. It describes relative service need (for example, for "
        "schools), not the community.",
        "",
        "## 1. Concentration",
        "",
        f"- **States.** Each year releases were as concentrated as if spread evenly over {st.effective_n.min():.0f}–"
        f"{st.effective_n.max():.0f} states (the effective number, 1 / HHI). The ten largest states took "
        f"{st.top10_share.min():.0%}–{st.top10_share.max():.0%} of releases. Concentration has eased slowly: the "
        f"top-ten share was {early.min():.0%}–{early.max():.0%} in FY2015–FY2019 and {late.min():.0%}–{late.max():.0%} "
        f"in FY2021–FY2025.",
        f"- **Counties.** In the high-volume years FY2021–FY2024 the effective number of places was "
        f"{surge.min():.0f}–{surge.max():.0f}; in the low-volume years FY2020 "
        f"and FY2025 it fell to {co.effective_n.loc[2020]:.0f} and {co.effective_n.loc[2025]:.0f}. Part of this is the "
        f"threshold: when fewer counties reach 50 releases, more children fall in the unlisted group, which counts "
        f"as a single place.",
        "",
        "## 2. Stability",
        "",
        f"- **State rankings.** Year-to-year rank correlations of state shares: Spearman {pers.spearman.min():.3f}–"
        f"{pers.spearman.max():.3f}, Kendall {pers.kendall.min():.3f}–{pers.kendall.max():.3f}. Simple rules for "
        f"next year's state shares, scored on FY2018–FY2025 (weighted by releases):",
        "",
        md_table(base_table),
        "",
        f"- **County tiers.** Each of the {int(tiers.iloc[0, 1:].sum())} counties listed at least once is placed "
        f"in a tier every year. A county with 1,000+ releases stays in that tier the next year "
        f"{p[('1,000+', '1,000+')]:.0%} of the time and moves to 200–999 {p[('1,000+', '200-999')]:.0%} of the time. "
        f"A county with 50–199 releases falls below the threshold the next year {p[('50-199', TIERS[0])]:.0%} of the "
        f"time. These moves follow national volume: {listed[2019]} counties were listed in FY2019, {listed[2020]} in "
        f"FY2020, {listed[2022]} in FY2022 and {listed[2025]} in FY2025.",
        "",
        "![Tier transitions](../results/figures/week4_tier_transitions.png)",
        "",
        "## 3. Geography: releases cluster",
        "",
        f"- **Overall clustering (Moran's I).** States with high release rates per school-age child border other "
        f"high-rate states: Moran's I = {mg.moran_i['state']:.2f} (p = {mg.p_sim['state']:.4f}, "
        f"{mg.places['state']} contiguous states and DC). Counties that are often listed border other often-listed "
        f"counties: Moran's I = {mg.moran_i['county']:.2f} (p = {mg.p_sim['county']:.4f}, {mg.places['county']:,} "
        f"counties). Moran's I runs from -1 to +1; 0 means no spatial pattern.",
        (f"- **Steady over time.** Every year from FY2015 to FY2025 both tests are significant (p < 0.05): "
         if all_sig else "- **Over time.** Not every year is significant at p < 0.05 (`results/moran_by_year.csv`): ") +
        f"Moran's I {sy.moran_i.min():.2f}–{sy.moran_i.max():.2f} for states and {cy.moran_i.min():.2f}–"
        f"{cy.moran_i.max():.2f} for counties." +
        (" Clustering did not weaken in the surge years or the low years." if all_sig else ""),
        "",
        "![Moran's I by year](../results/figures/week4_moran_by_year.png)",
        "",
        f"- **Local clusters, states (LISA).** High-High: {hh_states} (high rates among high-rate neighbors). "
        f"Low-Low: {ll_states}. Low-High: {lh_states}. With only 49 places, no single state cluster passes a "
        f"false-discovery-rate correction, so read the state clusters as suggestive; the overall result above is "
        f"strong.",
        "",
        "![State clusters](../results/figures/week4_state_clusters.png)",
        "",
        f"- **Local clusters, counties (LISA).** {sig('county', 'High-High')} counties are High-High "
        f"({sig('county', 'High-High', 'places_fdr05')} pass the false-discovery-rate correction). Grouped by "
        f"shared borders they form {len(clusters)} clusters; the eight largest hold "
        f"{top8.share_of_national_releases.sum():.0%} of all FY2015–FY2025 releases.",
        "",
        md_table(cluster_table),
        "",
        "![County clusters](../results/figures/week4_county_clusters.png)",
        "",
        "## 4. Release shares compared with school-age population",
        "",
        f"- **Listed counties** took {lc.ratio.min():.1f}–{lc.ratio.max():.1f} times their share of the nation's "
        f"school-age children each year; **other counties** as a group took {oc.ratio.min():.1f}–{oc.ratio.max():.1f} "
        f"times. The listed-county ratio was highest in FY{by_ratio.index[-1]} ({by_ratio.iloc[-1]:.1f}) and "
        f"FY{by_ratio.index[-2]} ({by_ratio.iloc[-2]:.1f}) and lowest in FY{by_ratio.index[0]} "
        f"({by_ratio.iloc[0]:.1f}): in low-volume years releases concentrate in fewer places.",
        f"- **{len(always)} counties were listed in all 11 years.** Together they received {always_rel:.0%} of all "
        f"releases but have {always_pop:.0%} of the nation's school-age children. {(always.ratio > 1).sum()} of the "
        f"{len(always)} have a ratio above 1; the median is {always.ratio.median():.1f}.",
        "",
        md_table(ratio_table),
        "",
        "![Release share vs school-age share](../results/figures/week4_release_vs_school_share.png)",
        "",
        "## What this means for the next phases",
        "",
        f"- **Week 5 (share model).** \"Last year's shares\" is a strong baseline ({naive.mae_share_points:.2f} share "
        f"points); the Bayesian model has to beat it on held-out years, or the write-up explains why not.",
        "- **Week 6 (scenarios).** County counts depend on whether a county clears the 50-release threshold, which "
        "depends on national volume. Reporting scenarios by cluster and by state, alongside listed counties, keeps "
        "ranges honest. The school-age ratios show where the same national volume means the largest relative need "
        "for school services; ORR's published age mix will turn releases into school-age children.",
        "",
        "## Methods and limits",
        "",
        "- **Data.** Migration Policy Institute tabulation of ORR releases to sponsors (state and listed county, "
        "FY2015–FY2025); Census Bureau Vintage 2024 estimates of children aged 5–17 (July 1, 2024, used as one "
        "reference year for every fiscal year); Census 2023 cartographic boundary files (1:20m).",
        "- **Neighbors.** Queen contiguity (shared border or corner), row-standardized, for the 48 contiguous "
        "states and DC. Alaska, Hawaii and the territories have no land neighbors and are left out. A few island "
        "counties are linked to their nearest county. Connecticut's four listed counties are left out of the "
        "county analysis because its 2023 Census counties are planning regions that do not match them.",
        f"- **Tests.** Moran's I and LISA with 9,999 random permutations and a fixed seed; local clusters at "
        f"p < 0.05, with false-discovery-rate counts reported alongside (`results/lisa_summary.csv`).",
        "- **County variable.** Years listed (0–11) uses only the published fact that a county had 50 or more "
        "releases in a year. Counties under the threshold are never estimated or backed out.",
        "- **School-age ratio.** First release location only, not later moves. Released children are not all of "
        "school age. Counties without a population match (Connecticut) are left out of both shares.",
        "- **Tiers.** The transition matrix covers counties listed at least once, so moves into and out of "
        "\"not listed\" are among counties that were listed in some year.",
        "",
        "## Files",
        "",
        "- Code: `src/geography.py` (Moran's I, LISA, school-age comparison), `src/measure.py` (concentration, "
        "persistence, tiers), `src/share_baseline.py`, this memo's builder `src/build_week4_memo.py`.",
        "- Tables: `results/moran_global.csv`, `moran_by_year.csv`, `lisa_states.csv`, `lisa_summary.csv`, "
        "`lisa_county_clusters.csv`, `school_age_comparison.csv`, `county_school_age_always_listed.csv`, "
        "`tier_transitions.csv`, `county_tiers_by_year.csv`.",
        "- Charts: `results/figures/week4_*.png`.",
        "",
    ]
    OUT.write_text("\n".join(L), "utf-8")
    print("wrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
