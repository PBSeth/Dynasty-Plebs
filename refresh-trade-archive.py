"""Build the public trade archive from dated DynastyProcess and Sleeper data."""

import argparse
import csv
import json
import re
import time
import unicodedata
import urllib.request
from bisect import bisect_right
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parent
LEAGUE = "1312057467684794368"
SLEEPER = "https://api.sleeper.app/v1/"
DYNASTY_PROCESS = "https://raw.githubusercontent.com/dynastyprocess/data/"
COMMIT_HISTORY = "https://api.github.com/repos/dynastyprocess/data/commits"
CENTRAL = ZoneInfo("America/Chicago")
HANDLES = {
    "abagueros": "Alex Agueros", "clawdaddy69": "Matt Clawson",
    "imjustluke": "Luke Miller", "justintreyreed": "Bo Tiller",
    "matthewmetz1985": "Matt Metz", "mcnutted86": "Jordan Martin",
    "mrplows": "Clint Hudson", "pbseth": "Seth Miller", "peedawg": "Payton Docheff",
    "rjlipkin": "Ryan Lipkin", "shuturmuth": "Dave Carnes", "tomahawkchop6": "Travis Page",
}


def downloaded(url, path, refresh=False):
    if path.exists() and not refresh:
        return path
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Dynasty-Plebs-Trade-Archive"})
            with urllib.request.urlopen(request, timeout=30) as response:
                contents = response.read()
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_suffix(".tmp")
            temp.write_bytes(contents)
            temp.replace(path)
            return path
        except OSError:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def read_json(path):
    return json.loads(path.read_text())


def milliseconds(iso):
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000)


def local_date(ms):
    return datetime.fromtimestamp(ms / 1000, CENTRAL).date().isoformat()


def normalize(name):
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = re.sub(r"\s+(?:Jr\.?|Sr\.?|II|III|IV)$", "", ascii_name, flags=re.I)
    return re.sub(r"[^a-z0-9]", "", name.lower())


class Snapshot:
    def __init__(self, commit, path):
        self.sha = commit["sha"]
        published = commit["commit"]["committer"]["date"]
        self.date = published[:10]
        self.timestamp = milliseconds(published)
        self.players = {}
        self.names = {}
        self.picks = {}
        with path.open(encoding="utf-8-sig", newline="") as data:
            for row in csv.DictReader(data):
                name = row.get("player") or row.get("mergename")
                value = row.get("value_1qb") or row.get("1QBValue")
                if not name or not (value or "").isdigit():
                    continue
                value = int(value)
                if row.get("pos") == "PICK":
                    self.picks[name] = value
                else:
                    fp = row.get("fp_id")
                    if fp and fp != "NA":
                        self.players[fp] = value
                    # Keep names usable in the older files that did not store IDs.
                    key = normalize(name)
                    if key in self.names and self.names[key] != value:
                        self.names[key] = None
                    else:
                        self.names[key] = value

    def player(self, player):
        if player.get("fpId") in self.players:
            return self.players[player["fpId"]]
        return self.names.get(normalize(player["name"]))

    def pick(self, asset):
        season, round_number = asset["season"], asset["round"]
        if slot := asset.get("slotKnownAtTrade"):
            round_pick = int(slot.split(".")[1])
            exact = f"{season} Pick {slot}"
            overall = f"{season} Pick {(round_number - 1) * 12 + round_pick}"
            if exact in self.picks or overall in self.picks:
                return self.picks.get(exact, self.picks.get(overall))
        ordinal = {1: "1st", 2: "2nd", 3: "3rd"}.get(round_number, f"{round_number}th")
        for label in (f"{season} {ordinal}", f"{season} Mid {ordinal}"):
            if label in self.picks:
                return self.picks[label]
        exact_round = []
        for slot in range(1, 13):
            exact = f"{season} Pick {round_number}.{slot:02}"
            overall = f"{season} Pick {(round_number - 1) * 12 + slot}"
            value = self.picks.get(exact, self.picks.get(overall))
            if value is not None:
                exact_round.append(value)
        return round(median(exact_round)) if len(exact_round) == 12 else None


def snapshots(cache, offline):
    commits = {}
    for page in range(1, 100):
        path = cache / f"dp-commits-{page}"
        if offline and not path.exists():
            break
        if not offline:
            query = f"?path=files/values.csv&per_page=100&since=2019-01-01T00:00:00Z&page={page}"
            downloaded(COMMIT_HISTORY + query, path, refresh=True)
        batch = read_json(path)
        commits.update((row["sha"], row) for row in batch)
        if len(batch) < 100:
            break
    commits = sorted(commits.values(), key=lambda row: row["commit"]["committer"]["date"])
    if not commits or not commits[0]["commit"]["committer"]["date"].startswith("2019-"):
        raise ValueError("DynastyProcess archive must contain 2019 history")

    def load_snapshot(commit):
        sha = commit["sha"]
        path = cache / "snapshots" / f"{sha}.csv"
        if not offline:
            downloaded(f"{DYNASTY_PROCESS}{sha}/files/values.csv", path)
        return Snapshot(commit, path)

    with ThreadPoolExecutor(max_workers=10) as pool:
        return list(pool.map(load_snapshot, commits))


def sleeper_trades(cache, offline, league_id):
    def sleeper(route):
        path = cache / "sleeper" / (route.replace("/", "-") + ".json")
        if not offline:
            downloaded(SLEEPER + route, path, refresh=True)
        return read_json(path)

    players_path = cache / "sleeper-players"
    ids_path = cache / "dp-playerids.csv"
    if not offline:
        downloaded(SLEEPER + "players/nfl", players_path, refresh=True)
        downloaded(DYNASTY_PROCESS + "master/files/db_playerids.csv", ids_path, refresh=True)
    players = read_json(players_path)
    with ids_path.open(newline="") as data:
        fp_ids = {
            row["sleeper_id"]: row["fantasypros_id"] for row in csv.DictReader(data)
            if row["sleeper_id"].isdigit() and row["fantasypros_id"].isdigit()
        }

    def player(player_id):
        original = players[player_id]
        name = original.get("full_name") or f"{original['first_name']} {original['last_name']}"
        asset = {"kind": "player", "name": name, "sleeperId": player_id}
        if fp_id := fp_ids.get(player_id):
            asset["fpId"] = fp_id
        return asset

    contexts = []
    outcomes = {}
    finished_drafts = {}
    while league_id and league_id != "0":
        league = sleeper(f"league/{league_id}")
        if league["name"] != "Dynasty Plebs":
            raise ValueError(f"Unexpected league for {league_id}")
        season = int(league["season"])
        users = {row["user_id"]: row["display_name"] for row in sleeper(f"league/{league_id}/users")}
        roster_owners = {
            row["roster_id"]: row["owner_id"] for row in sleeper(f"league/{league_id}/rosters")
        }
        manager_names = {rid: HANDLES.get(users[uid].lower(), users[uid]) for rid, uid in roster_owners.items()}
        with ThreadPoolExecutor(max_workers=8) as pool:
            rounds = pool.map(sleeper, [f"league/{league_id}/transactions/{week}" for week in range(19)])
            trades = {
                trade["transaction_id"]: trade for week in rounds for trade in week
                if trade["type"] == "trade" and trade["status"] == "complete"
            }
        contexts.append((league_id, season, manager_names, trades))

        # 2024's live drafts were roster setup drafts after the ESPN rookie draft.
        for draft in sleeper(f"league/{league_id}/drafts"):
            if season < 2025 or draft["status"] != "complete" or draft["type"] != "linear":
                continue
            order = draft.get("draft_order") or {}
            if len(order) != len(roster_owners) or not draft.get("last_picked"):
                continue
            finished_drafts[season] = draft["last_picked"]
            results = sleeper(f"draft/{draft['draft_id']}/picks")
            by_slot = {(pick["round"], pick["draft_slot"]): pick["player_id"] for pick in results}
            if len(by_slot) != len(results):
                raise ValueError(f"Duplicate pick slots in {draft['draft_id']}")
            for roster_id, owner in roster_owners.items():
                for round_number in range(1, draft["settings"]["rounds"] + 1):
                    slot = order[owner]
                    if player_id := by_slot.get((round_number, slot)):
                        outcomes[season, roster_id, round_number] = {
                            **player(player_id), "slot": f"{round_number}.{slot:02}",
                            "afterDraft": draft["last_picked"],
                        }
        league_id = league.get("previous_league_id")

    archive = []
    for league_id, season, managers, trades in contexts:
        for trade_id, trade in trades.items():
            sides = {
                rid: {"manager": managers[rid], "assets": []}
                for rid in sorted(trade["roster_ids"])
            }
            for player_id, rid in (trade.get("adds") or {}).items():
                sides[rid]["assets"].append(player(player_id))
            for pick in trade.get("draft_picks") or ():
                year, origin, round_number = int(pick["season"]), pick["roster_id"], pick["round"]
                asset = {"kind": "pick", "season": year, "round": round_number,
                         "origin": managers[origin], "originRosterId": origin}
                if year in finished_drafts:
                    asset["afterDraft"] = finished_drafts[year]
                if outcome := outcomes.get((year, origin, round_number)):
                    asset["outcome"] = outcome
                sides[pick["owner_id"]]["assets"].append(asset)
            for cash in trade.get("waiver_budget") or ():
                sides[cash["receiver"]]["assets"].append({"kind": "faab", "amount": cash["amount"]})
            accepted = trade["status_updated"]
            archived = {"id": f"sleeper-{trade_id}", "leagueId": league_id, "season": season,
                        "date": local_date(accepted), "acceptedAt": accepted, "sides": list(sides.values())}
            if len(sides) < 2 or not all(side["assets"] for side in sides.values()):
                raise ValueError(f"Missing trade package in {trade_id}")
            archive.append(archived)
    return archive


def grade(snapshot, trade, at, original=False):
    totals, missing = [], []
    for side in trade["sides"]:
        values = []
        absent = []
        for asset in side["assets"]:
            if asset["kind"] == "faab":
                continue
            if asset["kind"] == "player":
                value = snapshot.player(asset)
                label = asset["name"]
            elif asset["kind"] == "pick":
                label = f"{asset['season']} round {asset['round']} ({asset['origin']})"
                if not original and asset.get("afterDraft", float("inf")) <= at:
                    outcome = asset.get("outcome")
                    value = snapshot.player(outcome) if outcome else None
                    if outcome:
                        label = outcome["name"]
                else:
                    value = snapshot.pick(asset)
            else:
                raise ValueError(f"Unknown asset kind {asset['kind']}")
            values.append(value)
            if value is None:
                absent.append(label)
        totals.append(sum(values) if values and not absent else None)
        missing.append(absent)
    return totals, missing


def value_trade(trade, market, timestamps):
    if trade.get("gradeBlocked"):
        trade["day"] = None
        trade["timeline"] = []
        return
    accepted = trade["acceptedAt"]
    index = bisect_right(timestamps, accepted) - 1
    if index >= 0:
        market_day = market[index]
        totals, missing = grade(market_day, trade, accepted, original=True)
        trade["day"] = [index, totals, missing]
    else:
        trade["day"] = None
    timeline = []
    for i in range(index + 1, len(market)):
        snapshot = market[i]
        if i < len(market) - 1 and snapshot.date == market[i + 1].date:
            continue
        totals, _ = grade(snapshot, trade, snapshot.timestamp)
        timeline.append([i, *totals])
    trade["timeline"] = timeline
    if timeline:
        _, trade["latestMissing"] = grade(market[-1], trade, market[-1].timestamp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--league-id", default=LEAGUE, help="Newest Dynasty Plebs Sleeper league ID")
    parser.add_argument("--offline", action="store_true", help="Rebuild using the downloaded inputs")
    parser.add_argument("--dated-workbook-trades", type=Path, help="Verified archived IDs, dates and asset packages")
    args = parser.parse_args()
    market = snapshots(args.cache, args.offline)
    archive = sleeper_trades(args.cache, args.offline, args.league_id)
    history_path = ROOT / "trade-history.json"
    history = read_json(history_path) if history_path.exists() else None
    if history:
        archive.extend(trade for trade in history["trades"] if trade.get("acceptedAt"))
    if args.dated_workbook_trades:
        legacy = read_json(ROOT / "trade-workbook-archive.json")["ledger"]
        rows = {f"workbook-{row}": sides for row, sides, _, _ in legacy}
        for trade in read_json(args.dated_workbook_trades):
            sides = rows[trade["id"]]
            if {m for m, _ in sides} != {side["manager"] for side in trade["sides"]} or not trade["dateSource"]:
                raise ValueError(f"{trade['id']} needs verified managers and a dated source")
            trade["date"] = local_date(trade["acceptedAt"])
            trade.setdefault("season", int(trade["date"][:4]))
            archive.append(trade)
    if len({trade["id"] for trade in archive}) != len(archive):
        raise ValueError("Duplicate trade IDs")
    archive.sort(key=lambda trade: trade["acceptedAt"], reverse=True)
    timestamps = [snapshot.timestamp for snapshot in market]
    for trade in archive:
        value_trade(trade, market, timestamps)
    payload = {
        "market": [[snapshot.date, snapshot.sha, snapshot.timestamp] for snapshot in market],
        "trades": archive,
    }
    if history:
        payload["coverage"] = history["coverage"]
    path = ROOT / "trade-valuations.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"{len(archive)} dated trades priced against {len(market)} source snapshots")


if __name__ == "__main__":
    main()
