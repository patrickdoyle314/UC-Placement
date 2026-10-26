"""Tests for the Week 4 code: county tiers, Moran's I, cluster grouping and the school-age ratio."""
# ===================================================================================================
# HOW TO READ THIS FILE
# Business purpose: the Week 4 memo rests on a few calculations; these tests check each one on tiny
# made-up inputs whose answers are known, plus one check on the real data (tier counts must match the
# published county rows exactly, so no county-year is invented or lost).
#
# Python ideas: building small DataFrames by hand, libpysal's lat2W (a ready-made grid of neighbors),
# np.tile and np.indices for patterns, pytest.approx, reusing the needs_data marker.
# ===================================================================================================
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from libpysal.weights import lat2W

from src import geography, measure

ROOT = Path(__file__).resolve().parent.parent
needs_data = pytest.mark.skipif(not (ROOT / "data/processed/releases_by_fy_geo.parquet").exists(),
                                reason="run src/build_dataset.py and src/measure.py first")


def county_rows(values: dict) -> pd.DataFrame:
    """values: {county_key: {fiscal_year: releases}} -> rows shaped like the Week 1 table."""
    return pd.DataFrame([{"geo_level": "county", "county_key": k, "fiscal_year": fy, "releases": v}
                         for k, years in values.items() for fy, v in years.items()])


# --------------------------------------------------------------------------- tiers

def test_tier_codes_unlisted_years_are_tier_zero():
    df = county_rows({"a|TX": {2015: 60, 2016: 250, 2017: 1200}, "b|TX": {2016: 50}})
    codes = measure.tier_codes(df)
    assert codes.loc["a|TX", [2015, 2016, 2017]].tolist() == [1, 2, 3]
    assert codes.loc["b|TX", 2015] == 0 and codes.loc["b|TX", 2016] == 1  # absent = not listed, never estimated


def test_tier_transition_rows_sum_to_one():
    df = county_rows({"a|TX": {2015: 60, 2016: 250, 2017: 1200}, "b|TX": {2016: 50, 2019: 300}})
    trans = measure.tier_transitions(measure.tier_codes(df))
    sums = trans.groupby("from_tier").probability.sum()
    assert np.allclose(sums[sums > 0], 1.0, atol=0.002)  # each row is a set of shares (rounded to 3 places)
    n_pairs = 2 * (len(measure.FISCAL_YEARS) - 1)  # two counties x ten year-to-year pairs
    assert trans.county_years.sum() == n_pairs


@needs_data
def test_tier_counts_match_published_county_rows():
    df = measure.load()
    by_year = measure.tiers_by_year(measure.tier_codes(df)).set_index("fiscal_year")
    listed = by_year.drop(columns=measure.TIERS[0]).sum(axis=1)
    published = df[(df.geo_level == "county") & df.fiscal_year.isin(measure.FISCAL_YEARS)].groupby("fiscal_year").size()
    assert (listed == published).all()


# --------------------------------------------------------------------------- spatial statistics

def test_moran_positive_for_blocks_negative_for_checkerboard():
    w = lat2W(6, 6)  # a 6 x 6 grid; rook neighbors (shared edges)
    w.transform = "r"
    halves = np.repeat([0, 1], 18)  # left half 0, right half 1: like values sit together
    checker = (np.indices((6, 6)).sum(axis=0) % 2).ravel()  # every neighbor differs
    assert geography.global_moran(halves, w)["moran_i"] > 0.5
    assert geography.global_moran(halves, w)["p_sim"] < 0.01
    assert geography.global_moran(checker, w)["moran_i"] == pytest.approx(-1.0)


def test_connected_groups_splits_separate_blocks():
    w = lat2W(5, 5)
    members = np.array([0, 1, 5, 23, 24])  # cells 0, 1, 5 touch; 23 and 24 touch; the two groups don't
    group = geography.connected_groups(members, w)
    assert group[0] == group[1] == group[5]
    assert group[23] == group[24] != group[0]
    assert len(set(group.values())) == 2


# --------------------------------------------------------------------------- school-age comparison

def test_school_age_ratio_is_share_over_share():
    years = geography.FISCAL_YEARS
    nat = pd.DataFrame({"geo_level": "national", "fiscal_year": years, "releases": 1000, "pop_5_17_2024": 100000.0})
    county = pd.DataFrame({"geo_level": "county", "fiscal_year": years, "releases": 100, "pop_5_17_2024": 5000.0,
                           "county_fips": "48201", "county_name": "Harris County, TX"})
    other = pd.DataFrame({"geo_level": "other_counties", "fiscal_year": years, "releases": 900,
                          "pop_5_17_2024": 95000.0})
    per_year, always = geography.school_age_comparison(pd.concat([nat, county, other], ignore_index=True))
    listed = per_year[per_year.group == "listed counties"].iloc[0]
    assert listed.ratio == pytest.approx(0.10 / 0.05)  # 10% of releases, 5% of school-age children -> 2.0
    assert always.ratio.iloc[0] == pytest.approx(2.0)
    assert always.per_1000_school_age.iloc[0] == pytest.approx(1000 * 100 * len(years) / 5000)
