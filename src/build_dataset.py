"""Week 1: reshape MPI release data to one row per fiscal year x geography, keyed by county FIPS.

Rows:
  national        all releases that fiscal year
  state           state total
  county          a county MPI lists that year (>= 50 releases); suppressed county-years are not rows
  other_counties  state total minus listed counties: the real, unlisted group of smaller counties.
                  Never split further (plan guardrail: no backing out counties under 50).

Census join: July 1, 2024 county estimates (Vintage 2024) as one reference year for every row:
total population and school-age population (ages 5-17).

Inputs : data/raw/mpi/mpi-data-hub_uacsbystate-county-fy2014-fy2025.xlsx
         data/raw/census/cc-est2024-agesex-all.csv
Outputs: data/processed/releases_by_fy_geo.csv
         data/processed/reconciliation.csv      (one row per state x fiscal year)
         data/processed/county_fips_unmatched.csv
Usage  : python src/build_dataset.py
"""
# ===================================================================================================
# HOW TO READ THIS FILE
# Business purpose: the Week 1 dataset. It turns MPI's spreadsheet of children released to sponsors
# into one tidy table: one row per fiscal year and place (nation, state, listed county, "other
# counties"), with the Census population of each place attached. Every later step reads this table.
#
# Guardrail built in here: counties appear only in years ORR published them (50+ releases). The rest
# of a state is one "other counties" row and is never split or estimated.
#
# Python ideas: openpyxl (reading Excel), regular expressions for cleaning names, defaultdict,
# dict comprehensions, csv.DictWriter, reconciliation checks that prove the totals add up.
# ===================================================================================================
import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
MPI = ROOT / "data/raw/mpi/mpi-data-hub_uacsbystate-county-fy2014-fy2025.xlsx"
CENSUS = ROOT / "data/raw/census/cc-est2024-agesex-all.csv"
OUT = ROOT / "data/processed"
FYS = list(range(2014, 2026))
CENSUS_YEAR_CODE = "6"  # July 1, 2024 in Vintage 2024 files

USPS = {  # state name -> two-letter postal code
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
    "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA",
    "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
    "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
    "Puerto Rico": "PR", "Virgin Islands": "VI",  # MPI lists both; national totals include them
}
COLUMNS = ["fiscal_year", "geo_level", "state", "state_name", "county_fips", "county_name", "county_key",  # the output table's columns, in order
           "releases", "listed_counties", "pop_total_2024", "pop_5_17_2024"]


# MPI and the Census spell county names differently (accents, "St." vs "Saint", "County" suffix).
# Cleaning both sides the same way lets them match. re.sub(pattern, replacement, text) is a regular-
# expression find-and-replace.
def norm(name):
    """Comparable county name: no accents, no punctuation, 'saint' for 'st.', no 'county'/'parish'."""
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    n = re.sub(r"\bst\.?\s", "saint ", n)
    n = re.sub(r"[^a-z0-9 ]", "", n)
    n = re.sub(r"\s+(county|parish|borough|census area|municipality)$", "", n.strip())
    return re.sub(r"\s+", " ", n)


def county_key(name, st):
    """Exchange-contract key: lower case, without 'county'/'parish' (see exchange/EXCHANGE.md)."""
    n = re.sub(r"\s+(county|parish|borough|census area|municipality)$", "", name.strip().lower())
    return f"{n}|{st}"


# Read the Census county file: total and school-age (5-17) population per county and per state.
# defaultdict(lambda: [0, 0]) creates a [total, school-age] pair the first time a state appears, so
# the code can add to it without checking whether it exists yet.
def load_census():
    counties, states = {}, defaultdict(lambda: [0, 0])
    for r in csv.DictReader(open(CENSUS, encoding="latin-1")):
        if r["YEAR"] != CENSUS_YEAR_CODE or r["STNAME"] not in USPS:
            continue
        st = USPS[r["STNAME"]]
        total, school = int(r["POPESTIMATE"]), int(r["AGE513_TOT"]) + int(r["AGE1417_TOT"])
        counties[(st, norm(r["CTYNAME"]))] = (r["STATE"] + r["COUNTY"], r["CTYNAME"], total, school)
        states[st][0] += total
        states[st][1] += school
    return counties, states


def num(v):  # unpublished cells become None (missing), never 0
    """MPI cells: an integer, or blank / '-' where the county-year is not published."""
    return v if isinstance(v, (int, float)) else None


# Read the MPI spreadsheet. data_only=True returns the values Excel displays (not formulas);
# iter_rows(values_only=True) gives each row as a tuple. The data starts at row 9 on the States sheet
# and row 8 on the Counties sheet. {f: ... for i, f in enumerate(FYS)} is a dict comprehension that
# maps each fiscal year to its column.
def load_mpi():
    wb = openpyxl.load_workbook(MPI, data_only=True)
    states = {}
    for r in wb["States"].iter_rows(min_row=9, values_only=True):
        if r[0] in USPS or r[0] == "United States":
            states[r[0]] = {f: num(r[1 + i]) for i, f in enumerate(FYS)}
    counties = []
    for r in wb["Counties"].iter_rows(min_row=8, values_only=True):
        if r[0] and r[1]:
            counties.append((r[0].rsplit(",", 1)[0].strip(), r[1].strip(),
                             {f: num(r[2 + i]) for i, f in enumerate(FYS)}))
    return states, counties


# Steps: match MPI counties to Census FIPS codes, build one row per fiscal year and place, check that
# the numbers add up, and write three CSV files.
def main():
    census, census_states = load_census()
    mpi_states, mpi_counties = load_mpi()
    us = mpi_states.pop("United States")
    OUT.mkdir(parents=True, exist_ok=True)

    # Match each MPI county to its Census FIPS code by cleaned name. Names that don't match are written
    # out for review (for example Connecticut, whose newer Census geography uses planning regions).
    fips, unmatched = {}, []
    for name, st, _ in mpi_counties:
        hit = census.get((st, norm(name)))
        if hit:
            fips[(name, st)] = hit
        else:
            unmatched.append((st, name))

    rows, recon = [], []
    for fy in FYS:
        rows.append(dict(fiscal_year=fy, geo_level="national", releases=us[fy] or 0,
                         pop_total_2024=sum(v[0] for v in census_states.values()),
                         pop_5_17_2024=sum(v[1] for v in census_states.values())))
        state_sum = 0
        for st_name, st in USPS.items():
            total = mpi_states[st_name][fy] or 0
            state_sum += total
            spop = census_states[st] if st in census_states else ["", ""]  # VI is not in the county file
            rows.append(dict(fiscal_year=fy, geo_level="state", state=st, state_name=st_name, releases=total,
                             pop_total_2024=spop[0], pop_5_17_2024=spop[1]))
            listed = [(n, s, v[fy]) for n, s, v in mpi_counties if s == st and v[fy]]
            listed_pop = [0, 0]
            for n, s, val in listed:
                f, cname, tot, school = fips.get((n, s), ("", n, "", ""))
                if tot != "":
                    listed_pop[0] += tot
                    listed_pop[1] += school
                rows.append(dict(fiscal_year=fy, geo_level="county", state=st, state_name=st_name, county_fips=f,
                                 county_name=f"{n}, {st}", county_key=county_key(n, st), releases=val,
                                 pop_total_2024=tot, pop_5_17_2024=school))
            # "Other counties" = state total minus the listed counties: a real, published remainder. It is
            # never
            # split further; estimating counties under 50 releases would undo ORR's privacy threshold.
            other = total - sum(v for _, _, v in listed)
            all_matched = all((n, s) in fips for n, s, _ in listed)
            rows.append(dict(fiscal_year=fy, geo_level="other_counties", state=st, state_name=st_name,
                             county_name=f"Other counties, {st}", releases=other, listed_counties=len(listed),
                             pop_total_2024=spop[0] - listed_pop[0] if all_matched and spop[0] != "" else "",
                             pop_5_17_2024=spop[1] - listed_pop[1] if all_matched and spop[1] != "" else ""))
            # Reconciliation: in every state-year the listed counties must not add up to more than the state
            # total,
            # and the states must add up to the national total. Any failure is printed at the end.
            recon.append(dict(fiscal_year=fy, state=st, state_total=total,
                              listed_county_sum=sum(v for _, _, v in listed), other_counties=other,
                              listed_counties=len(listed), ok=other >= 0))
        recon.append(dict(fiscal_year=fy, state="US", state_total=us[fy], listed_county_sum=state_sum,
                          other_counties=(us[fy] or 0) - state_sum, listed_counties="", ok=(us[fy] or 0) == state_sum))

    with open(OUT / "releases_by_fy_geo.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLUMNS)  # DictWriter writes one dict per row; r.get(c, '') leaves a blank where a row has no value
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLUMNS})
    with open(OUT / "reconciliation.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(recon[0]))
        w.writeheader()
        w.writerows(recon)
    with open(OUT / "county_fips_unmatched.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["state", "mpi_county_name"])
        w.writerows(sorted(unmatched))

    bad = [r for r in recon if not r["ok"]]
    print(f"rows: {len(rows)}  (county rows: {sum(r['geo_level'] == 'county' for r in rows)})")
    print(f"MPI counties: {len(mpi_counties)}, matched to FIPS: {len(fips)}, unmatched: {len(unmatched)}")
    print(f"reconciliation: {len(recon)} checks, {len(bad)} failed")
    for r in bad[:10]:
        print("  FAILED:", r)


if __name__ == "__main__":
    main()
