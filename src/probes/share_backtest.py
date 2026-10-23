"""Probe: how predictable are next year's release shares? (feasibility check for the Week 5 share model)

For each held-out fiscal year, predict each state's share of national releases (and each county's
share within its state, with "other counties" as one category) from earlier years only:
  naive      last year's shares (the plan's baseline)
  mean3      average of the last three years' shares
  pooled     all earlier years pooled (total releases / total)
Scored with mean absolute error (share points) and log score per release (higher is better).

Usage: python src/probes/share_backtest.py   (needs data/processed/releases_by_fy_geo.csv)
"""
import csv
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EPS = 1e-4
HELD_OUT = range(2017, 2026)  # need at least three earlier years for mean3


def shares(counts):
    tot = sum(counts.values())
    return {k: v / tot for k, v in counts.items()} if tot else {}


def score(pred, actual_counts):
    keys = set(pred) | set(actual_counts)
    act = shares(actual_counts)
    norm = sum(pred.get(k, 0) + EPS for k in keys)
    p = {k: (pred.get(k, 0) + EPS) / norm for k in keys}
    mae = sum(abs(p[k] - act.get(k, 0)) for k in keys) / len(keys)
    n = sum(actual_counts.values())
    log = sum(v * math.log(p[k]) for k, v in actual_counts.items()) / n
    return mae, log


def methods(history, fy):
    prev = [history[y] for y in range(fy - 3, fy) if y in history]
    pooled = defaultdict(int)
    for y, c in history.items():
        if y < fy:
            for k, v in c.items():
                pooled[k] += v
    keys = set().union(*prev)
    mean3 = {k: sum(shares(c).get(k, 0) for c in prev) / len(prev) for k in keys}
    return {"naive": shares(history[fy - 1]), "mean3": mean3, "pooled": shares(pooled)}


def run(label, groups):
    """groups: {group_id: {fy: {category: releases}}}; results averaged over groups and held-out years."""
    agg = defaultdict(lambda: [0.0, 0.0, 0])
    for g, history in groups.items():
        for fy in HELD_OUT:
            if fy not in history or not all(y in history for y in range(fy - 3, fy)):
                continue
            for name, pred in methods(history, fy).items():
                mae, log = score(pred, history[fy])
                w = sum(history[fy].values())  # weight by releases in the group-year
                agg[name][0] += mae * w
                agg[name][1] += log * w
                agg[name][2] += w
    print(f"\n{label}")
    print(f"  {'method':8s} {'MAE (share pts)':>16s} {'log score/release':>18s}")
    for name, (m, l, w) in agg.items():
        print(f"  {name:8s} {100 * m / w:16.3f} {l / w:18.4f}")


def main():
    rows = list(csv.DictReader(open(ROOT / "data/processed/releases_by_fy_geo.csv", encoding="utf-8")))
    nat = {"US": defaultdict(dict)}
    within = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        fy, v = int(r["fiscal_year"]), int(r["releases"])
        if r["geo_level"] == "state" and r["state"] not in ("PR", "VI"):
            nat["US"][fy][r["state"]] = v
        elif r["geo_level"] in ("county", "other_counties"):
            within[r["state"]][fy][r["county_key"] or "other"] = v
    run("State shares of national releases (50 states + DC)", nat)
    big = {s: h for s, h in within.items() if sum(sum(c.values()) for c in h.values()) > 20000}
    run(f"County shares within state ({len(big)} states with > 20,000 releases, other counties as one category)", big)


if __name__ == "__main__":
    main()
