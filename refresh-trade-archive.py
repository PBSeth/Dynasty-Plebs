"""Build the public trade archive from dated DynastyProcess and Sleeper data."""

import argparse
import csv
import json
import math
import re
import time as clock
import unicodedata
import urllib.request
import urllib.error
from bisect import bisect_right
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parent
LEAGUE = "1312057467684794368"
SLEEPER = "https://api.sleeper.app/v1/"
DYNASTY_PROCESS = "https://raw.githubusercontent.com/dynastyprocess/data/"
COMMIT_HISTORY = "https://api.github.com/repos/dynastyprocess/data/commits"
CENTRAL = ZoneInfo("America/Chicago")
UNRANKED_ZERO_MIN_DAYS = 30
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
            clock.sleep(attempt + 1)


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


def estimate_value(value, model):
    """Apply one independent, monotone curve to dated source rank proxies."""
    if value is None or value <= 0:
        return value
    rank = max(1.0, -math.log(value / model["sourceScale"]) / model["sourceExponent"])
    if rank >= model["replacementRank"]:
        return 0
    distance = rank - 1
    elite = math.exp(-model["eliteDecay"] * distance)
    depth = max(0.0, 1 - distance / (model["replacementRank"] - 1))
    return round(model["scale"] * (model["eliteWeight"] * elite + (1 - model["eliteWeight"]) * depth))


class Snapshot:
    def __init__(self, commit, path, pick_path=None, model=None):
        self.model = model
        self.sha = commit["sha"]
        published = commit["commit"]["committer"]["date"]
        self.date = published[:10]
        self.timestamp = milliseconds(published)
        self.players = {}
        self.player_names = {}
        self.names = {}
        self.picks = {}
        self.pick_policy = "published-legacy"
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
                        self.player_names[fp] = normalize(name)
                    # Keep names usable in the older files that did not store IDs.
                    key = normalize(name)
                    if key in self.names and self.names[key] != value:
                        self.names[key] = None
                    else:
                        self.names[key] = value
        if pick_path and pick_path.exists():
            self.calculator_picks(pick_path)
        if model:
            self.players = {key: estimate_value(value, model) for key, value in self.players.items()}
            self.names = {key: estimate_value(value, model) for key, value in self.names.items()}
            self.picks = {key: estimate_value(value, model) for key, value in self.picks.items()}

    def calculator_picks(self, path):
        """Reproduce the source calculator's 1QB, 12-team default controls.

        Historical high/low pick models are blended at 60% optimism. Values
        are converted before averaging unknown slots, then discounted using
        the 90% future-pick control and the source's seasonal ramp. Player
        quotes stay on the same published 0.0235 exponential value scale.
        Source: dynastyprocess/apps-calculator R/values.R and R/1_ui.R.
        """
        rounds = {}
        source_years = set()
        with path.open(encoding="utf-8-sig", newline="") as data:
            for row in csv.DictReader(data):
                if not row.get("pick", "").isdigit():
                    continue
                high, low = row.get("ecr_high_1qb"), row.get("ecr_low_1qb")
                try:
                    ecr = .60 * float(high) + .40 * float(low)
                    if not math.isfinite(ecr):
                        continue
                    source_date = row["scrape_date"]
                    if source_date > self.date:
                        raise RuntimeError("Pick model was published after its source snapshot")
                    source_years.add(int(source_date[:4]))
                    pick = int(row["pick"])
                    rd, slot = (pick - 1) // 12 + 1, (pick - 1) % 12 + 1
                    rounds.setdefault(rd, {})[slot] = round(10500 * math.exp(-.0235 * ecr))
                except (TypeError, KeyError, ValueError):
                    continue
        if not rounds or any(len(values) != 12 for values in rounds.values()):
            return
        if len(source_years) != 1:
            raise ValueError("Mixed rookie class years in historical pick inputs")
        year = source_years.pop()
        month = int(self.date[5:7])
        factor = .90 if month < 9 else .925 if month <= 10 else .95 if month == 11 else .975
        # Rebuild pick quotes consistently, including unknown-slot rounds.
        self.picks = {}
        for rd, values in rounds.items():
            ordinal = {1: "1st", 2: "2nd", 3: "3rd"}.get(rd, f"{rd}th")
            for slot, value in values.items():
                self.picks[f"{year} Pick {rd}.{slot:02}"] = value
            self.picks[f"{year} {ordinal}"] = round(mean(values.values()))
            for horizon in range(1, 4):
                discount = factor * .90 ** (horizon - 1)
                self.picks[f"{year + horizon} {ordinal}"] = round(mean(values.values()) * discount)
                # Retain slot-specific projections for an offseason whose
                # order is known before the source refreshes its class year.
                for slot, value in values.items():
                    self.picks[f"{year + horizon} Pick {rd}.{slot:02}"] = round(value * discount)
                if horizon == 1:
                    for label, slots in [("Early", range(1, 5)), ("Mid", range(5, 9)), ("Late", range(9, 13))]:
                        self.picks[f"{year + 1} {label} {ordinal}"] = round(mean(values[s] for s in slots) * discount)
        self.pick_policy = "calculator-defaults-60-90"

    def player(self, player):
        if player.get("fpId") in self.players:
            return self.players[player["fpId"]]
        return self.names.get(normalize(player["name"]))

    def pick(self, asset, at=None):
        season, round_number = asset["season"], asset["round"]
        slot = asset.get("slotKnownAtTrade")
        if not slot and (self.timestamp if at is None else at) >= asset.get("slotKnownFrom", float("inf")):
            slot = asset.get("resolvedSlot")
        if slot:
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
        return round(mean(exact_round)) if len(exact_round) == 12 else None


def recover_unranked_quotes(result, model):
    """Estimate sustained unranked value without turning brief outages into zero.

    Only evidence already published at each snapshot is used. A missing player
    stays unavailable until absent for 30 days across at least two broad feeds.
    A reappearance resets the clock; earlier gaps are never backfilled.
    """
    known_ids, known_names, absences = {}, set(), {}
    for snapshot in result:
        observed_ids, observed_names = dict(snapshot.players), set(snapshot.names)
        snapshot.unranked_zero_names = []
        for name in observed_names:
            absences.pop(name, None)
        if model and len(observed_ids) >= model["replacementRank"]:
            zero_names = set()
            for name in known_names - observed_names:
                since, count = absences.get(name, (snapshot.timestamp, 0))
                count += 1
                absences[name] = (since, count)
                if count >= 2 and snapshot.timestamp - since >= UNRANKED_ZERO_MIN_DAYS * 86400000:
                    zero_names.add(name)
                    snapshot.names[name] = 0
            for fp_id, name in known_ids.items():
                if fp_id not in observed_ids and name in zero_names:
                    snapshot.players[fp_id] = 0
            snapshot.unranked_zero_names = sorted(zero_names)
        known_ids.update(snapshot.player_names)
        known_names.update(observed_names)
    return result


def snapshots(cache, offline, model=None):
    unavailable_path = cache / "snapshot-picks" / "unavailable.json"
    unavailable = set(read_json(unavailable_path)) if unavailable_path.exists() else set()
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
        pick_path = cache / "snapshot-picks" / f"{sha}.csv"
        if not pick_path.exists() and sha not in unavailable:
            if offline:
                raise FileNotFoundError(f"Missing historical pick inputs: {sha}")
            try:
                downloaded(f"{DYNASTY_PROCESS}{sha}/files/values-picks.csv", pick_path)
            except urllib.error.HTTPError as error:
                if error.code != 404:
                    raise
                unavailable.add(sha)
        return Snapshot(commit, path, pick_path, model)

    with ThreadPoolExecutor(max_workers=10) as pool:
        result = list(pool.map(load_snapshot, commits))
    recover_unranked_quotes(result, model)
    if not offline:
        unavailable_path.parent.mkdir(parents=True, exist_ok=True)
        unavailable_path.write_text(json.dumps(sorted(unavailable)))
    return result


def sleeper_trades(cache, offline, league_id, outcomes_by_origin=None, outcome_bounds=None):
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
            # A 2024 roster-setup draft cannot supply rookie slots. Its completed
            # player list does prove those documented selections existed by then.
            if outcome_bounds is not None and draft.get("status") == "complete" and draft.get("last_picked"):
                for pick in sleeper(f"draft/{draft['draft_id']}/picks"):
                    outcome_bounds[season, pick["player_id"]] = {
                        "afterDraft": draft["last_picked"], "draftId": draft["draft_id"]}
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
                        if outcomes_by_origin is not None:
                            outcomes_by_origin[season, manager_names[roster_id], round_number] = {
                                **outcomes[season, roster_id, round_number],
                                "draftId": draft["draft_id"],
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


def recover_pick_slots(trade):
    """Recover draft positions independently of the selected player's value.

    The manager confirmed offseason positions were already known. Use January
    1 of the draft year as a conservative, reproducible offseason boundary;
    a pick traded during the prior season remains generic until that boundary.
    Existing explicitly recorded slots keep their original timing. Workbook
    dates that straddle the boundary retain their date-sensitivity treatment.
    """
    at = trade.get("estimatedAt", trade.get("acceptedAt"))
    for side in trade["sides"]:
        for asset in side.get("assets", []):
            if asset["kind"] != "pick" or asset.get("slotKnownAtTrade"):
                continue
            slot = asset.get("outcome", {}).get("slot")
            year = asset.get("season")
            if not slot or not year:
                continue
            if int(slot.split(".")[0]) != asset["round"]:
                raise ValueError(f"Mismatched pick round in {trade['id']}: {slot}")
            boundary = int(datetime(year, 1, 1, tzinfo=CENTRAL).timestamp() * 1000)
            asset["resolvedSlot"] = slot
            asset["slotKnownFrom"] = boundary
            asset["slotResolutionSource"] = (
                f"Sleeper {year} original-roster draft order" if trade["id"].startswith("sleeper-")
                else "Workbook recorded pick slot and draft-outcome table"
            )
            lower = trade.get("dateEstimate", {}).get("earliest")
            order_known = at is not None and at >= boundary
            if trade.get("dateEstimate"):
                order_known = order_known and lower is not None and lower >= f"{year}-01-01"
            if order_known:
                asset["slotKnownAtTrade"] = slot


def grade(snapshot, trade, at, original=False, breakdown=False):
    totals, missing, strengths = [], [], []
    for side in trade["sides"]:
        values = []
        absent = []
        player_values = []
        for asset in side["assets"]:
            if asset["kind"] == "faab":
                continue
            if asset["kind"] == "player":
                value = snapshot.player(asset)
                label = asset["name"]
                player_values.append(value)
            elif asset["kind"] == "pick":
                label = f"{asset['season']} round {asset['round']} ({asset['origin']})"
                if not original and asset.get("afterDraft", float("inf")) <= at:
                    outcome = asset.get("outcome")
                    value = snapshot.player(outcome) if outcome else None
                    if outcome:
                        label = outcome["name"]
                        player_values.append(value)
                else:
                    value = snapshot.pick(asset, at)
            else:
                raise ValueError(f"Unknown asset kind {asset['kind']}")
            values.append(value)
            if value is None:
                absent.append(label)
        totals.append(sum(values) if values and not absent else None)
        missing.append(absent)
        positive = [v for v in values if v is not None and v > 0]
        strengths.append((len(positive), max(positive, default=0),
                          max((v for v in player_values if v is not None), default=0)))
    adjustments = [0] * len(totals)
    if snapshot.model and len(totals) == 2 and all(value is not None for value in totals):
        for side, other in [(0, 1), (1, 0)]:
            count, _, strongest_player = strengths[side]
            other_count, other_best, _ = strengths[other]
            if count < other_count and strongest_player > other_best:
                adjustments[side] = round(strongest_player * snapshot.model["consolidationPerPiece"]
                                          * (other_count - count))
                totals[side] += adjustments[side]
    return (totals, missing, adjustments) if breakdown else (totals, missing)


def value_trade(trade, market, timestamps):
    recover_pick_slots(trade)
    if trade.get("gradeBlocked"):
        trade["day"] = None
        trade["timeline"] = []
        return
    accepted = trade.get("estimatedAt", trade.get("acceptedAt"))
    index = bisect_right(timestamps, accepted) - 1
    if index >= 0:
        market_day = market[index]
        totals, missing, adjustment = grade(market_day, trade, accepted, original=True, breakdown=True)
        trade["day"] = [index, totals, missing]
        if market_day.model:
            trade["dayAdjustments"] = adjustment
    else:
        trade["day"] = None
    timeline, timeline_adjustments = [], []
    for i in range(index + 1, len(market)):
        snapshot = market[i]
        if i < len(market) - 1 and snapshot.date == market[i + 1].date:
            continue
        totals, _, adjustment = grade(snapshot, trade, snapshot.timestamp, breakdown=True)
        timeline.append([i, *totals])
        if snapshot.model and any(adjustment):
            timeline_adjustments.append([i, *adjustment])
    trade["timeline"] = timeline
    if market[-1].model:
        trade["timelineAdjustments"] = timeline_adjustments
    if timeline:
        _, trade["latestMissing"] = grade(market[-1], trade, market[-1].timestamp)
        trade["latestZeroEstimates"] = sorted({
            player["name"] for side in trade["sides"] for asset in side["assets"]
            for player in ([asset] if asset["kind"] == "player" else
                           [asset["outcome"]] if asset.get("outcome") and
                           asset.get("afterDraft", float("inf")) <= market[-1].timestamp else [])
            if normalize(player["name"]) in market[-1].unranked_zero_names
        })
    bounds = trade.get("dateEstimate")
    if bounds and bounds["earliest"] and bounds["latest"]:
        lower = datetime.combine(datetime.fromisoformat(bounds["earliest"]).date(), time.min, CENTRAL).timestamp() * 1000
        upper = datetime.combine(datetime.fromisoformat(bounds["latest"]).date(), time.max, CENTRAL).timestamp() * 1000
        first = max(0, bisect_right(timestamps, lower) - 1)
        last = bisect_right(timestamps, upper) - 1
        margins, leaders = [], set()
        for i in range(first, last + 1):
            values, _ = grade(market[i], trade, market[i].timestamp, original=True)
            if any(value is None for value in values):
                continue
            margins.append([v - max(values[:s] + values[s + 1:]) for s, v in enumerate(values)])
            leaders.add(tuple(s for s, value in enumerate(values) if value == max(values)))
        trade["dateSensitivity"] = {
            "snapshots": last - first + 1,
            "pricedSnapshots": len(margins),
            "marginRanges": [[min(m[s] for m in margins), max(m[s] for m in margins)] for s in range(len(trade["sides"]))] if margins else [],
            "winnerChanges": len(leaders) > 1,
            "completeWindow": len(margins) == last - first + 1,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--league-id", default=LEAGUE, help="Newest Dynasty Plebs Sleeper league ID")
    parser.add_argument("--offline", action="store_true", help="Rebuild using the downloaded inputs")
    parser.add_argument("--source-values", action="store_true", help="Audit baseline: use the original source value curve")
    parser.add_argument("--output", type=Path, default=ROOT / "trade-valuations.json")
    parser.add_argument("--dated-workbook-trades", type=Path, help="Verified archived IDs, dates and asset packages")
    args = parser.parse_args()
    model = None if args.source_values else read_json(ROOT / "trade-value-model.json")
    market = snapshots(args.cache, args.offline, model)
    outcomes_by_origin, outcome_bounds = {}, {}
    archive = sleeper_trades(args.cache, args.offline, args.league_id, outcomes_by_origin, outcome_bounds)
    history_path = ROOT / "trade-history.json"
    history = read_json(history_path) if history_path.exists() else None
    if history:
        for trade in history["trades"]:
            for side in trade["sides"]:
                for asset in side.get("assets", []):
                    if asset["kind"] == "pick" and asset.get("outcome") and not asset.get("afterDraft"):
                        bound = outcome_bounds.get((asset.get("season"), asset["outcome"].get("sleeperId")))
                        if bound:
                            asset["afterDraft"] = bound["afterDraft"]
                            asset["outcomeTimingSource"] = f"Completed Sleeper roster setup {bound['draftId']}; upper bound on selection time, not the rookie draft date."
                    if asset["kind"] != "pick" or asset.get("outcome"):
                        continue
                    key = (asset.get("season"), asset.get("origin"), asset.get("round"))
                    if outcome := outcomes_by_origin.get(key):
                        asset["outcome"] = outcome
                        asset["afterDraft"] = outcome["afterDraft"]
                        asset["outcomeTimingSource"] = f"Completed Sleeper draft {outcome['draftId']}"
        archive.extend(trade for trade in history["trades"] if trade.get("acceptedAt") or trade.get("estimatedAt"))
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
    archive.sort(key=lambda trade: trade.get("estimatedAt", trade.get("acceptedAt", 0)), reverse=True)
    timestamps = [snapshot.timestamp for snapshot in market]
    for trade in archive:
        value_trade(trade, market, timestamps)
    payload = {
        "market": [[snapshot.date, snapshot.sha, snapshot.timestamp] for snapshot in market],
        "trades": archive,
        "pickPolicy": {
            "name": "Dated DynastyProcess pick inputs",
            "format": "1QB, 12 teams",
            "rookieOptimism": .60,
            "futureFactor": .90,
            "unknownSlotAggregation": "mean of source slot values before independent rank-proxy conversion" if model else "mean of slot values",
            "source": "https://github.com/dynastyprocess/apps-calculator/blob/master/R/values.R",
            "legacySnapshots": sum(s.pick_policy == "published-legacy" for s in market),
            "calculatorSnapshots": sum(s.pick_policy != "published-legacy" for s in market),
        },
    }
    if model:
        payload["valueModel"] = model
        payload["playerQuotePolicy"] = {
            "unranked": "Previously quoted players absent for at least 30 days across two or more broad feeds covering at least replacementRank identified players receive an estimated zero. Brief absences, unknown identities and earlier missing quotes remain unavailable; gaps are never backfilled.",
            "minimumAbsentDays": UNRANKED_ZERO_MIN_DAYS,
            "minimumBroadFeeds": 2,
            "latestUnrankedZeroNames": sorted(set(market[-1].unranked_zero_names)),
        }
    if history:
        payload["coverage"] = history["coverage"]
    path = args.output
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"{len(archive)} dated trades priced against {len(market)} source snapshots")


if __name__ == "__main__":
    main()
