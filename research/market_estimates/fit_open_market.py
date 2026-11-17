"""Fit and validate a small independent curve against CC0 completed trades.

Run with --cache pointing to the existing plebs-trade-import captures. This
research build never downloads restricted calculator histories or publishes
another provider's value dataset. Requires numpy, scipy and pyarrow.
"""

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import re
from bisect import bisect_right
from collections import Counter
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parent
REPLACEMENT_RANK = 444  # 12 * (30 roster positions + 3 taxi + 4 reserve slots)
SPEC = importlib.util.spec_from_file_location("archive", ROOT.parents[1] / "refresh-trade-archive.py")
ARCHIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ARCHIVE)


def prepare(cache):
    market = ARCHIVE.snapshots(cache, True)
    times = [s.timestamp for s in market]
    with (cache / "dp-playerids.csv").open() as f:
        ids = {r["mfl_id"]: r for r in csv.DictReader(f) if r["mfl_id"]}
    records, seen, counts = [], set(), Counter()
    for season in [2019, 2020, 2021]:
        leagues = pq.read_table(cache / "open-market" / f"league-{season}.parquet").to_pandas()
        leagues = leagues[(leagues.qb_type == "1QB") & (leagues.franchise_count == 12)
                          & leagues.league_name.str.contains("Dynasty", case=False)
                          & ~leagues.idp & ~leagues.best_ball & ~leagues.salary_cap
                          & (leagues.player_copies == 1)]
        allowed = set(leagues.league_id.astype(int))
        rows = pq.read_table(cache / "open-market" / f"transactions-{season}.parquet").to_pandas()
        rows = rows[(rows.type_desc == "traded_away") & rows.league_id.isin(allowed)]
        for (league, timestamp), trade in rows.groupby(["league_id", "timestamp"]):
            signature = (int(league), timestamp.isoformat(), tuple(sorted(zip(trade.franchise_id, trade.player_id))))
            if signature in seen:
                continue
            seen.add(signature)
            counts["uniqueTrades"] += 1
            at = int(timestamp.timestamp() * 1000)
            index = bisect_right(times, at) - 1
            if index < 0 or at - times[index] > 45 * 86400000:
                counts["noFreshPriorRanks"] += 1
                continue
            snapshot = market[index]
            sides = []
            bad = False
            for _, side in trade.groupby("franchise_id"):
                assets = []
                for row in side.to_dict("records"):
                    player_id = row["player_id"]
                    is_pick = False
                    horizon = 0
                    if player_id.isdigit():
                        meta = ids.get(player_id, {})
                        name = meta.get("name")
                        if not name:
                            parts = (row["player_name"] or "").split(", ", 1)
                            name = " ".join(reversed(parts))
                        value = snapshot.player({"name": name, "fpId": meta.get("fantasypros_id")})
                    elif pick := re.fullmatch(r"FP_\d+_(\d{4})_(\d+)", player_id):
                        year, rd = map(int, pick.groups())
                        # FP asset IDs encode a future year/round, not its
                        # eventual rookie or a guessed current-year slot.
                        value = snapshot.pick({"season": year, "round": rd})
                        is_pick = True
                        horizon = max(0, year - int(snapshot.date[:4]) - 1)
                    else:
                        # Explicit draft-slot IDs and budget tokens require
                        # extra context. Exclude the entire incomplete trade.
                        value = None
                    if value is None or value <= 0:
                        bad = True
                        break
                    rank = max(1.0, -math.log(value / 10500) / .0235)
                    assets.append([rank, int(is_pick), horizon])
                sides.append(assets)
            if bad or len(sides) != 2 or not all(0 < len(s) <= 8 for s in sides):
                counts["incompleteOrUnsupported"] += 1
                continue
            split = int(hashlib.sha256(str(league).encode()).hexdigest()[:8], 16) % 5
            records.append({"split": split, "date": timestamp.date().isoformat(), "sides": sides})
    counts["completeTrades"] = len(records)
    return records, dict(counts)


def arrays(records):
    # Padding has an explicit validity mask and never adds a spurious asset.
    result = np.zeros((len(records), 2, 8, 4))
    for i, trade in enumerate(records):
        for side, assets in enumerate(trade["sides"]):
            for j, asset in enumerate(assets):
                result[i, side, j] = [*asset, 1]
    return result


def totals(parameters, inputs):
    weight, elite_decay, premium_per_piece = parameters
    rank = np.maximum(0, inputs[..., 0] - 1)
    elite = np.exp(-elite_decay * rank)
    depth = np.maximum(0, 1 - rank / (REPLACEMENT_RANK - 1))
    values = np.where(rank < REPLACEMENT_RANK - 1, weight * elite + (1 - weight) * depth, 0)
    values *= inputs[..., 3]
    sums = np.sum(values, axis=2)
    counts = np.sum(values > 0, axis=2)
    best = np.max(values, axis=2)
    best_player = np.max(values * (1 - inputs[..., 1]), axis=2)
    for side, other in [(0, 1), (1, 0)]:
        applies = (counts[:, side] < counts[:, other]) & (best_player[:, side] > best[:, other])
        sums[:, side] += np.where(applies, best_player[:, side] * premium_per_piece
                                  * (counts[:, other] - counts[:, side]), 0)
    return sums


def errors(parameters, inputs):
    sums = totals(parameters, inputs)
    return np.log(np.maximum(sums[:, 0], 1e-12) / np.maximum(sums[:, 1], 1e-12))


def summary(values):
    return {"n": len(values), "medianAbsoluteLogGap": float(np.median(np.abs(values))),
            "within25Percent": float(np.mean(np.abs(values) <= math.log(1.25))),
            "within50Percent": float(np.mean(np.abs(values) <= math.log(1.5)))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--benchmarks", type=Path, required=True,
                        help="Small manually checked player/pick comparison fixture, not a bulk calculator feed")
    args = parser.parse_args()
    data, counts = prepare(args.cache)
    training = [t for t in data if t["split"] != 0 and t["date"] < "2021-01-01"]
    held_out = [t for t in data if t["split"] == 0 and t["date"] < "2021-01-01"]
    future = [t for t in data if t["date"] >= "2021-01-01"]
    benchmarks = json.loads(args.benchmarks.read_text())
    sources = [s for s in benchmarks["sources"]
               if s["id"] in ["fantasycalc-2026-11-17", "ktc-crowdsourced-2026-11-17"]]
    source_snapshot = ARCHIVE.snapshots(args.cache, True)[-1]
    names = [*benchmarks["players"], *[f"2027 {tier} {rd}" for rd in ["1st", "2nd", "3rd"]
                                      for tier in ["Early", "Mid", "Late"]]]
    proxies = {name: max(0, -math.log((source_snapshot.picks.get(name) if name.startswith("2027")
                                    else source_snapshot.player({"name": name})) / 10500) / .0235 - 1)
               for name in names}
    def shaped(p, rank):
        weight, decay = p
        return weight * math.exp(-decay * rank) + (1 - weight) * max(0, 1 - rank / (REPLACEMENT_RANK - 1))
    anchor = "Jaxon Smith-Njigba"
    def shape_errors(p):
        reference = shaped(p, proxies[anchor])
        return [math.log(shaped(p, proxies[name]) / reference)
                - math.log(source["quotes"][name] / source["quotes"][anchor])
                for source in sources for name in names if name != anchor]
    # Fix the value curve from independent market comparisons first. Jointly
    # fitting a flat value curve and a per-piece bonus to trade equality alone
    # is not identifiable and can reward a meaningless count-only model.
    shape = least_squares(shape_errors, [.6, .035], bounds=([.01, .005], [.99, .3]),
                          loss="soft_l1", f_scale=.3)
    training_inputs = arrays(training)
    fitted = least_squares(lambda p: errors([*shape.x, p[0]], training_inputs), [.15],
                           bounds=([0], [.75]), loss="soft_l1", f_scale=.3)
    parameters = [*shape.x.tolist(), float(fitted.x[0])]
    # The original source's exponential curve is a separate baseline.
    def original(inputs):
        values = np.exp(-.0235 * inputs[..., 0]) * inputs[..., 3]
        sums = values.sum(axis=2)
        return np.log(sums[:, 0] / sums[:, 1])
    report = {"source": "CC0 SafeLeagues completed trades; historical DynastyProcess inputs",
              "counts": counts, "format": "12-team 1QB dynasty; source leagues use full PPR",
              "parameters": {**dict(zip(["eliteWeight", "eliteDecay", "consolidationPerPiece"], parameters)),
                             "replacementRank": REPLACEMENT_RANK},
              "marketSpotChecks": {"families": ["FantasyCalc", "KeepTradeCut"], "assets": len(names),
                                   "quoteDate": "2026-11-17", "rankInputDate": source_snapshot.date,
                                   "role": "Broad curve calibration; not a licensed historical feed or exact quote reproduction"},
              "splits": {name: {"candidate": summary(errors(parameters, arrays(rows))),
                                "publishedCurve": summary(original(arrays(rows)))}
                         for name, rows in [("training", training), ("unseenLeagues", held_out), ("laterDates", future)]},
              "limitations": ["Trade equality is not a community winner label; this is a market-clearing diagnostic.",
                              "Not a half-PPR-specific training sample.",
                              "Historical reconstructions are estimates, not archived quotes from another calculator."]}
    (ROOT / "open-market-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    model = {
        "id": "plebs-market-estimate-v1", "name": "Plebs estimated market values",
        "versionDate": "2026-11-17", "estimated": True,
        "scale": 10000, "sourceScale": 10500, "sourceExponent": .0235,
        **report["parameters"],
        "inputPolicy": "Dated 1QB DynastyProcess inputs; original unmade picks remain picks",
        "fitSource": "https://github.com/dynastyprocess/data-mfl_public",
        "fitLicense": "CC0-1.0", "inputSource": "https://github.com/DynastyProcess/data",
        "inputLicense": "GPL-3.0", "trainingTrades": len(training),
        "unseenLeagueTrades": len(held_out), "laterDateTrades": len(future),
        "interpretation": "Independent retrospective estimates, not archived KTC or FantasyCalc quotes",
        "aggregation": "Asset values plus independently fitted consolidation allowance for two-sided, unequal-size packages whose smaller side receives the strongest player",
        "scoringCaveat": "Underlying training leagues and expert ranks use PPR; not a half-PPR-specific fit",
        "closeTradeBand": .10,
    }
    (ROOT.parents[1] / "trade-value-model.json").write_text(json.dumps(model, indent=2) + "\n")
    (args.cache / "open-market" / "complete-features.json").write_text(json.dumps(data, separators=(",", ":")))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
