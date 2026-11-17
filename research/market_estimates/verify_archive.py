"""Verify archive integrity and safeguards against the captured baseline."""

import argparse
import copy
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("archive", ROOT / "refresh-trade-archive.py")
ARCHIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ARCHIVE)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--benchmarks", type=Path, required=True)
    args = parser.parse_args()
    read = lambda p: json.loads(p.read_text())
    old, new = read(args.baseline), read(ROOT / "trade-valuations.json")
    assert len(old["trades"]) == len(new["trades"]) == 241
    assert new["market"] == old["market"] and len(new["market"]) == 371
    for before, after in zip(old["trades"], new["trades"]):
        for key, value in before.items():
            if key not in ["day", "timeline", "dateSensitivity"]:
                assert after.get(key) == value, (after["id"], key)
        if before.get("gradeBlocked"):
            assert after["day"] is None and after["timeline"] == []
        if after["day"]:
            index = after["day"][0]
            assert new["market"][index][2] <= after.get("estimatedAt", after.get("acceptedAt"))
            assert [v is None for v in before["day"][1]] == [v is None for v in after["day"][1]]
        assert len(before["timeline"]) == len(after["timeline"])
        for a, b in zip(before["timeline"], after["timeline"]):
            assert [v is None for v in a] == [v is None for v in b]

    model = read(ROOT / "trade-value-model.json")
    values = [ARCHIVE.estimate_value(10500 * math.exp(-.0235 * rank), model)
              for rank in range(1, 600)]
    assert all(a >= b >= 0 for a, b in zip(values, values[1:]))
    assert values[model["replacementRank"] - 1] == 0
    markets = ARCHIVE.snapshots(args.cache, True, model)
    snapshot = markets[-1]
    trade = next(t for t in new["trades"] if t["id"] == "sleeper-1412868254434676736")
    original = ARCHIVE.grade(snapshot, trade, snapshot.timestamp, original=True)[0]
    changed = copy.deepcopy(trade)
    for side in changed["sides"]:
        for asset in side["assets"]:
            if asset["kind"] == "pick":
                asset["outcome"] = {"name": "Jaxon Smith-Njigba", "kind": "player"}
                asset["afterDraft"] = snapshot.timestamp - 1
    assert ARCHIVE.grade(snapshot, changed, snapshot.timestamp, original=True)[0] == original
    assert ARCHIVE.grade(snapshot, changed, snapshot.timestamp, original=False)[0] != original

    missing = {"sides": [{"assets": [{"kind": "player", "name": "No Published Quote"}]}, trade["sides"][1]]}
    totals, _, adjustments = ARCHIVE.grade(snapshot, missing, snapshot.timestamp, breakdown=True)
    assert totals[0] is None and adjustments == [0, 0]
    picks_only = {"sides": [{"assets": [{"kind": "pick", "season": 2027, "round": 1, "origin": "Test"}]},
                            {"assets": [{"kind": "pick", "season": 2027, "round": 2, "origin": "Test"}]}]}
    assert ARCHIVE.grade(snapshot, picks_only, snapshot.timestamp, breakdown=True)[2] == [0, 0]

    sources = read(args.benchmarks)["sources"]
    quotes = [s["quotes"] for s in sources
              if s["id"] in ["fantasycalc-2026-11-17", "ktc-crowdsourced-2026-11-17"]]
    walker = snapshot.player({"name": "Kenneth Walker III"})
    comparisons = {}
    for name in ["2027 Early 1st", "2027 Mid 1st", "2027 Late 1st", "2027 Mid 2nd", "2027 Mid 3rd"]:
        ratio = snapshot.picks[name] / walker
        observed = [q[name] / q["Kenneth Walker III"] for q in quotes]
        assert min(observed) <= ratio <= max(observed), (name, ratio, observed)
        comparisons[name] = round(100 * ratio, 1)
    print("Passed archive, missing-data, original-pick, monotonicity, and five market-ratio checks.")
    print("Current pick values as % of Walker:", comparisons)


if __name__ == "__main__":
    main()
