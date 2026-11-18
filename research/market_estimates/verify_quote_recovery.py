"""Verify recovered current grades without fabricating unknown or early prices."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("archive", ROOT / "refresh-trade-archive.py")
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)
parser = argparse.ArgumentParser()
parser.add_argument("--cache", required=True, type=Path)
args = parser.parse_args()
read = lambda path: json.loads(path.read_text())
payload = read(ROOT / "trade-valuations.json")
market = archive.snapshots(args.cache, True, read(ROOT / "trade-value-model.json"))
trades = {trade["id"]: trade for trade in payload["trades"]}
assert len(trades) == 241 and len(market) == 371
assert market[-1].player({"name": "Robert Woods", "fpId": "11610"}) == 0
assert market[-1].player({"name": "Unmatched Player", "fpId": "unknown"}) is None
assert market[0].player({"name": "Tory Horton", "fpId": "26022"}) is None
woods = trades["workbook-109"]
assert woods["timeline"][-1][1:] == [2887, 0]
assert woods["latestZeroEstimates"] == ["Robert Woods"]
fourth = trades["workbook-160"]
assert fourth["timeline"][-1][1:] == [1996, 445]
asset = fourth["sides"][1]["assets"][0]
assert asset["afterDraft"] == 1726683448591
assert "upper bound" in asset["outcomeTimingSource"]
assert fourth["sides"][0]["assets"][0]["resolvedSlot"] == "4.05"
assert "slotKnownAtTrade" not in fourth["sides"][0]["assets"][0]
# Original pick prices cannot change when an eventual selection is replaced.
changed = copy.deepcopy(fourth)
for side in changed["sides"]:
    for pick in side["assets"]:
        pick["outcome"] = {"name": "Unmatched Player"}
        pick["afterDraft"] = 0
snapshot = market[fourth["day"][0]]
assert archive.grade(snapshot, changed, fourth["estimatedAt"], original=True)[0] == fourth["day"][1]
kamara = trades["workbook-122"]
assert kamara["gradeBlocked"] and kamara["day"] is None and kamara["timeline"] == []
assert [pick["season"] for pick in kamara["sides"][1]["assets"]] == [2022, 2022]
print("Verified recovered fourth, conservative selection timing, disclosed zero estimate, unknown identity, no future quote or selection leakage, and unresolved pick-year guard.")
