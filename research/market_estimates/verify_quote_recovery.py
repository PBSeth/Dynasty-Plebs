"""Verify recovered current grades without fabricating unknown or early prices."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

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
# A one-week ranking omission is unavailable, never an artificial zero.
coker = {"name": "Jalen Coker"}
quotes = {s.date: s.player(coker) for s in market}
assert quotes["2024-10-11"] is None
assert quotes["2024-10-18"] > 0

def fake_snapshot(day, included=False, broad=True):
    names = {"filler": 10, **({"example": 100} if included else {})}
    players = {"filler": 10, **({"example-id": 100} if included else {})} if broad else {}
    return SimpleNamespace(date=day, timestamp=archive.milliseconds(day + "T12:00:00Z"),
                           names=names, players=players,
                           player_names={"example-id": "example"} if included else {})

synthetic = [fake_snapshot("2020-01-01", True), fake_snapshot("2020-01-08"),
             fake_snapshot("2020-01-15", True), fake_snapshot("2020-01-22"),
             fake_snapshot("2020-02-15", broad=False), fake_snapshot("2020-02-22")]
archive.recover_unranked_quotes(synthetic, {"replacementRank": 1})
assert "example" not in synthetic[1].names
assert "example" not in synthetic[3].names  # Reappearance resets absence age.
assert "example" not in synthetic[4].names  # A narrow feed cannot confirm zero.
assert synthetic[5].names["example"] == 0
assert synthetic[5].players["example-id"] == 0
assert "example" in synthetic[5].unranked_zero_names
# No future observation or later zero may fill an earlier gap.
assert all("example" not in synthetic[i].names for i in [1, 3, 4])
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
assert not kamara.get("gradeBlocked") and kamara["day"] and kamara["timeline"]
assert [pick["season"] for pick in kamara["sides"][1]["assets"]] == [2023, 2023]
assert [pick["outcome"]["name"] for pick in kamara["sides"][1]["assets"]] == ["Quentin Johnston", "Marvin Mims"]
assert kamara["timeline"][-1][1:] == [5321, 4376]
assert all("slotKnownAtTrade" not in pick for pick in kamara["sides"][1]["assets"])
assert trades["workbook-98"]["sides"][1]["assets"][0]["season"] == 2023
# A different contradictory record stays blocked; resolving one case cannot
# disable the historical guards for every trade.
assert trades["workbook-131"]["gradeBlocked"]
print("Verified sustained-zero estimates, brief omission gaps, reappearance reset, broad-feed guard, no backward filling, recovered fourth, selection timing, unknown identities, Kamara/Godwin corrections, and remaining pick-year guard.")
