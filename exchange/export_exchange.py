"""Write this project's exchange outbox (contract v1.0, see exchange/EXCHANGE.md).

Reads the Week 1 table (data/processed/releases_by_fy_geo.csv) and publishes release counts and
school-age population as aggregates. Everything here is already public MPI / Census data.

Usage: python exchange/export_exchange.py   (run src/build_dataset.py first)
"""
# ===================================================================================================
# HOW TO READ THIS FILE
# Business purpose: publish this project's numbers for the companion MP (missing children)
# project, as aggregate counts only, in the format both projects agreed on (exchange/EXCHANGE.md).
# The projects never share records; each only reads the other's outbox.
#
# Python ideas: csv.writer, a set to avoid writing the same row twice, json.dumps for the manifest,
# datetime for a timestamp.
# ===================================================================================================
import csv
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTBOX = ROOT / "exchange/outbox"
CONTRACT_VERSION = "1.0"  # both projects check this before reading each other's files
COLUMNS = ["geo_level", "state", "county_key", "county_name", "fiscal_year", "measure", "value", "publishable"]


def main():
    rows = list(csv.DictReader(open(ROOT / "data/processed/releases_by_fy_geo.csv", encoding="utf-8")))
    OUTBOX.mkdir(parents=True, exist_ok=True)
    n = 0
    pop_written = set()  # places that already have a population row (one population figure per place, not per year)
    with open(OUTBOX / "aggregates.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for r in rows:
            w.writerow([r["geo_level"], r["state"], r["county_key"], r["county_name"], r["fiscal_year"],
                        "releases_to_sponsors", r["releases"], "true"])
            n += 1
            key = (r["geo_level"], r["state"], r["county_key"])
            if r["geo_level"] != "other_counties" and r["pop_5_17_2024"] and key not in pop_written:
                w.writerow([r["geo_level"], r["state"], r["county_key"], r["county_name"], "",
                            "census_pop_5_17_2024", r["pop_5_17_2024"], "true"])
                pop_written.add(key)
                n += 1
    # The manifest says who produced the outbox, when, from which sources and under which contract
    # version, so the reader can check compatibility first. publication_threshold is None because these
    # counts are already public (ORR's 50-release county rule was applied before MPI published them).
    manifest = {
        "producer": "UC-Placement",
        "contract_version": CONTRACT_VERSION,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "source": "Migration Policy Institute, Unaccompanied Children Released to Sponsors by State and County, "
                  "FY 2014-2025 (ACF/ORR data); Census Bureau Vintage 2024 county estimates",
        "publication_threshold": None,
        "row_count": n,
        "measures": {
            "releases_to_sponsors": "Unaccompanied children released to sponsors in the fiscal year (first release location)",
            "census_pop_5_17_2024": "Census Bureau July 1, 2024 population aged 5-17",
        },
    }
    (OUTBOX / "manifest.json").write_text(json.dumps(manifest, indent=1), "utf-8")
    print(f"wrote {n} rows to {OUTBOX}")


if __name__ == "__main__":
    main()
