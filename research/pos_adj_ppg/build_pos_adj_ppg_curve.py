#!/usr/bin/env python3
"""Build the external position + exact-slot expectation curve for Dynasty Plebs.

The benchmark is deliberately independent of Dynasty Plebs results. Historical
12-team Dynasty Rookie ADP supplies draft cost; Sleeper regular-season stat
lines are rescored with the league's exact scoring rules to supply outcomes.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
import time
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "research" / "pos_adj_ppg"
ADP_YEARS = tuple(range(2014, 2023))
STATS_YEARS = tuple(range(2014, 2026))
LAST_COMPLETE_SEASON = 2025
POSITIONS = ("QB", "RB", "WR", "TE")
MIN_TIMES_DRAFTED = 5
MAX_TRAINING_ADP = 96.0
MAX_CURVE_SLOT = 72
BANDWIDTHS = (3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0)
USER_AGENT = "Mozilla/5.0 (Dynasty-Plebs POS-ADJ-PPG research; reproducible historical benchmark)"

# Existing Dynasty Plebs identity exceptions plus common historical variants.
ALIASES = {
    "kenwalkeriii": "kennethwalkeriii",
    "nathanieldell": "tankdell",
    "deriusdavis": "dariusdavis",
    "jaelondarden": "jaleondarden",
    "terracemarshall": "terracemarshalljr",
    "brianrobinson": "brianrobinsonjr",
    "zachmoss": "zackmoss",
    "gabrieldavis": "gabedavis",
    "kennethgainwell": "kennygainwell",
    "dwayneeskridge": "deeeskridge",
    "joshpalmer": "joshuapalmer",
    "mitchtrubisky": "mitchelltrubisky",
    "hollywoodbrown": "marquisebrown",
}
SUFFIXES = ("junior", "senior", "jr", "sr", "iii", "ii", "iv", "v")

CALIBRATION = (
    (2019, "Kyler Murray", 301.28, 16),
    (2020, "Kyler Murray", 406.74, 16),
    (2021, "Kyler Murray", 328.48, 14),
    (2022, "Kyler Murray", 214.52, 11),
    (2023, "Kyler Murray", 156.36, 8),
    (2019, "A.J. Brown", 191.10, 16),
    (2020, "A.J. Brown", 212.50, 14),
    (2021, "A.J. Brown", 149.40, 13),
    (2022, "A.J. Brown", 255.60, 17),
    (2023, "A.J. Brown", 236.60, 17),
    (2020, "Jonathan Taylor", 234.80, 15),
    (2021, "Jonathan Taylor", 353.10, 17),
    (2022, "Jonathan Taylor", 132.40, 11),
    (2023, "Jonathan Taylor", 146.90, 10),
    (2021, "Kyle Pitts", 142.60, 17),
    (2022, "Kyle Pitts", 61.60, 10),
    (2023, "Kyle Pitts", 110.80, 17),
    (2024, "Kyler Murray", 317.24, 17),
    (2025, "Kyler Murray", 83.78, 5),
    (2024, "A.J. Brown", 183.40, 13),
    (2025, "A.J. Brown", 181.30, 15),
    (2024, "Jonathan Taylor", 235.70, 14),
    (2025, "Jonathan Taylor", 339.30, 17),
    (2024, "Kyle Pitts", 107.70, 17),
    (2025, "Kyle Pitts", 166.80, 17),
)


def norm_name(value: object) -> str:
    s = unicodedata.normalize("NFD", str(value or "").lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s)


def strip_suffix(value: str) -> str:
    for suffix in SUFFIXES:
        if value.endswith(suffix) and len(value) > len(suffix) + 3:
            return value[: -len(suffix)]
    return value


def as_num(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def fetch_bytes(url: str, retries: int = 4) -> bytes:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/plain,*/*"},
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.read()
        except Exception as exc:  # network-only retry wrapper
            last = exc
            time.sleep(1.25 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last}")


def fetch_json_hashed(url: str) -> tuple[object, str, int]:
    raw = fetch_bytes(url)
    return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest(), len(raw)


def player_name(record: dict) -> str:
    p = record.get("player") or {}
    return (
        p.get("full_name")
        or " ".join(x for x in (p.get("first_name"), p.get("last_name")) if x)
        or record.get("player_name")
        or ""
    ).strip()


def player_position(record: dict) -> str:
    p = record.get("player") or {}
    return str(p.get("position") or record.get("position") or "")


def player_id(record: dict) -> str:
    p = record.get("player") or {}
    value = record.get("player_id") or p.get("player_id") or p.get("id")
    return str(value) if value is not None else ""


def plebs_points(record: dict) -> float:
    """Score Sleeper raw stats exactly like the production career PPG build."""
    s = record.get("stats") or {}
    st_td = as_num(s.get("st_td"))
    return (
        as_num(s.get("pass_yd")) * 0.04
        + as_num(s.get("pass_td")) * 6
        - as_num(s.get("pass_int")) * 4
        + as_num(s.get("pass_2pt")) * 2
        + as_num(s.get("rush_yd")) * 0.1
        + as_num(s.get("rush_td")) * 6
        + as_num(s.get("rush_2pt")) * 2
        + as_num(s.get("rec")) * 0.5
        + as_num(s.get("rec_yd")) * 0.1
        + as_num(s.get("rec_td")) * 6
        + as_num(s.get("rec_2pt")) * 2
        - as_num(s.get("fum_lost")) * 2
        + as_num(s.get("fum_rec_td")) * 6
        + (st_td if st_td else as_num(s.get("kick_ret_td")) + as_num(s.get("punt_ret_td"))) * 6
    )


def load_adp() -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    sources: list[dict] = []
    for year in ADP_YEARS:
        url = f"https://fantasyfootballcalculator.com/api/v1/adp/rookie?position=all&teams=12&year={year}"
        payload, sha, size = fetch_json_hashed(url)
        if not isinstance(payload, dict) or payload.get("status") != "Success":
            raise RuntimeError(f"FFC source failed shape/status validation for {year}")
        meta = payload.get("meta") or {}
        if meta.get("type") != "Dynasty Rookie" or int(meta.get("teams") or 0) != 12:
            raise RuntimeError(f"FFC source is not 12-team Dynasty Rookie for {year}: {meta}")
        players = payload.get("players") or []
        if len(players) < 20:
            raise RuntimeError(f"implausibly small FFC player set for {year}: {len(players)}")
        sources.append(
            {
                "kind": "ffc_dynasty_rookie_adp",
                "year": year,
                "url": url,
                "sha256": sha,
                "bytes": size,
                "meta": meta,
                "rows": len(players),
            }
        )
        for p in players:
            name = str(p.get("name") or "").strip()
            pos = str(p.get("position") or "").upper()
            adp = p.get("adp")
            if not name or norm_name(name) == "deleteddeleted" or pos not in POSITIONS:
                continue
            try:
                adp = float(adp)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(adp) or adp <= 0:
                continue
            rows.append(
                {
                    "year": year,
                    "name": name,
                    "position": pos,
                    "adp": adp,
                    "adp_formatted": p.get("adp_formatted"),
                    "times_drafted": int(as_num(p.get("times_drafted") or p.get("timesDrafted"))),
                    "high": p.get("high"),
                    "low": p.get("low"),
                    "stdev": p.get("stdev"),
                }
            )
        time.sleep(0.12)
    return rows, sources


def load_sleeper_stats() -> tuple[dict[int, dict[str, dict]], dict, list[dict]]:
    by_year_pid: dict[int, dict[str, dict]] = {}
    identity_names: dict[str, set[str]] = defaultdict(set)
    identity_positions: dict[str, set[str]] = defaultdict(set)
    first_game_season: dict[str, int] = {}
    display_names: dict[str, str] = {}
    sources: list[dict] = []

    for year in STATS_YEARS:
        url = f"https://api.sleeper.com/stats/nfl/{year}?season_type=regular"
        payload, sha, size = fetch_json_hashed(url)
        if not isinstance(payload, list) or not payload:
            raise RuntimeError(f"Sleeper returned no regular-season stats for {year}")
        sources.append(
            {
                "kind": "sleeper_regular_season_stats",
                "year": year,
                "url": url,
                "sha256": sha,
                "bytes": size,
                "rows": len(payload),
            }
        )
        year_map: dict[str, dict] = {}
        for rec in payload:
            if not isinstance(rec, dict):
                continue
            pid = player_id(rec)
            name = player_name(rec)
            pos = player_position(rec)
            if not pid or not name or pos not in POSITIONS:
                continue
            gp = int(as_num((rec.get("stats") or {}).get("gp") or (rec.get("stats") or {}).get("gms_active")))
            identity_names[pid].add(norm_name(name))
            identity_positions[pid].add(pos)
            display_names.setdefault(pid, name)
            if gp > 0 and (pid not in first_game_season or year < first_game_season[pid]):
                first_game_season[pid] = year
            old = year_map.get(pid)
            candidate = {"record": rec, "games": gp, "points": plebs_points(rec), "name": name, "position": pos}
            if old is None or (candidate["games"], abs(candidate["points"])) > (old["games"], abs(old["points"])):
                year_map[pid] = candidate
        by_year_pid[year] = year_map
        time.sleep(0.12)

    exact: dict[str, set[str]] = defaultdict(set)
    base: dict[str, set[str]] = defaultdict(set)
    for pid, names in identity_names.items():
        for n in names:
            exact[n].add(pid)
            base[strip_suffix(n)].add(pid)
    identity = {
        "names": identity_names,
        "positions": identity_positions,
        "first_game_season": first_game_season,
        "display_names": display_names,
        "exact": exact,
        "base": base,
    }
    return by_year_pid, identity, sources


def resolve_pid(name: str, pos: str, identity: dict) -> str | None:
    n = norm_name(name)
    variants = [n]
    if n in ALIASES:
        variants.append(ALIASES[n])
    # Reverse alias support when a source uses the canonical side.
    variants.extend(k for k, v in ALIASES.items() if v == n)

    def choose(candidates: set[str]) -> str | None:
        if len(candidates) == 1:
            return next(iter(candidates))
        by_pos = {pid for pid in candidates if pos in identity["positions"].get(pid, set())}
        return next(iter(by_pos)) if len(by_pos) == 1 else None

    for v in variants:
        pid = choose(set(identity["exact"].get(v, set())))
        if pid:
            return pid
    for v in variants:
        pid = choose(set(identity["base"].get(strip_suffix(v), set())))
        if pid:
            return pid
    return None


def career_outcome(pid: str, draft_year: int, by_year_pid: dict[int, dict[str, dict]]) -> tuple[float | None, float, int]:
    points = 0.0
    games = 0
    for year in range(draft_year, LAST_COMPLETE_SEASON + 1):
        row = by_year_pid.get(year, {}).get(pid)
        if not row or row["games"] <= 0:
            continue
        points += row["points"]
        games += row["games"]
    return ((points / games) if games else None), points, games


def validate_scoring(by_year_pid: dict[int, dict[str, dict]], identity: dict) -> None:
    failures = []
    for year, name, expected_points, expected_games in CALIBRATION:
        pid = resolve_pid(name, "QB" if name == "Kyler Murray" else "WR" if "Brown" in name else "RB" if "Taylor" in name else "TE", identity)
        row = by_year_pid.get(year, {}).get(pid or "")
        if not row:
            failures.append(f"{year} {name}: missing")
            continue
        if row["games"] != expected_games or abs(row["points"] - expected_points) > 0.11:
            failures.append(
                f"{year} {name}: got {row['points']:.2f}/{row['games']} expected {expected_points:.2f}/{expected_games}"
            )
    if failures:
        raise RuntimeError("Plebs scoring calibration failed:\n" + "\n".join(failures))


def resolve_adp_rows(adp_rows: list[dict], by_year_pid: dict[int, dict[str, dict]], identity: dict) -> tuple[list[dict], list[dict], list[dict]]:
    resolved: list[dict] = []
    unresolved: list[dict] = []
    nonrookies: list[dict] = []
    for row in adp_rows:
        pid = resolve_pid(row["name"], row["position"], identity)
        if not pid:
            unresolved.append(row)
            continue
        first = identity["first_game_season"].get(pid)
        if first is not None and first < row["year"]:
            nonrookies.append({**row, "sleeper_first_game_season": first})
            continue
        ppg, points, games = career_outcome(pid, row["year"], by_year_pid)
        if ppg is None:
            # This matches the site's eligibility rule: no NFL regular-season game,
            # no career-PPG grade yet. Keep it in the audit, not the fitted sample.
            unresolved.append({**row, "reason": "no_regular_season_game_or_identity_outcome"})
            continue
        resolved.append(
            {
                **row,
                "sleeper_player_id": pid,
                "sleeper_first_game_season": first,
                "career_games": games,
                "career_points": round(points, 4),
                "career_ppg": round(ppg, 6),
            }
        )
    return resolved, unresolved, nonrookies


def core_filter(rows: list[dict], min_times: int = MIN_TIMES_DRAFTED, max_year: int = 2022) -> list[dict]:
    return [
        r
        for r in rows
        if r["year"] <= max_year
        and r["times_drafted"] >= min_times
        and r["adp"] <= MAX_TRAINING_ADP
        and r["position"] in POSITIONS
    ]


def kernel_predict(train: list[dict], x: float, bandwidth: float) -> tuple[float, float]:
    weights = []
    ys = []
    for r in train:
        z = (r["adp"] - x) / bandwidth
        w = math.exp(-0.5 * z * z)
        weights.append(w)
        ys.append(r["career_ppg"])
    sw = sum(weights)
    if sw <= 1e-12:
        nearest = min(train, key=lambda r: abs(r["adp"] - x))
        return float(nearest["career_ppg"]), 1.0
    pred = sum(w * y for w, y in zip(weights, ys)) / sw
    sw2 = sum(w * w for w in weights)
    neff = (sw * sw / sw2) if sw2 > 0 else 1.0
    return max(0.0, pred), neff


def select_bandwidth(rows: list[dict], position: str) -> tuple[float, list[dict]]:
    data = [r for r in rows if r["position"] == position]
    years = sorted({r["year"] for r in data})
    if len(years) < 5:
        raise RuntimeError(f"not enough draft classes to cross-validate {position}: {years}")
    results = []
    for bw in BANDWIDTHS:
        year_maes = []
        n_preds = 0
        for holdout in years:
            train = [r for r in data if r["year"] != holdout]
            test = [r for r in data if r["year"] == holdout]
            if not train or not test:
                continue
            errors = [abs(r["career_ppg"] - kernel_predict(train, r["adp"], bw)[0]) for r in test]
            year_maes.append(sum(errors) / len(errors))
            n_preds += len(errors)
        mean_mae = statistics.mean(year_maes)
        se = statistics.stdev(year_maes) / math.sqrt(len(year_maes)) if len(year_maes) > 1 else 0.0
        results.append({"bandwidth": bw, "mean_year_mae": mean_mae, "se": se, "years": len(year_maes), "n": n_preds})
    best = min(results, key=lambda x: x["mean_year_mae"])
    threshold = best["mean_year_mae"] + best["se"]
    # One-standard-error rule: among effectively tied models, prefer the smoother one.
    eligible = [r for r in results if r["mean_year_mae"] <= threshold + 1e-12]
    selected = max(eligible, key=lambda x: x["bandwidth"])["bandwidth"]
    return float(selected), results


def pava_decreasing(values: list[float], weights: list[float]) -> list[float]:
    blocks: list[dict] = []
    for i, (value, weight) in enumerate(zip(values, weights)):
        blocks.append({"start": i, "end": i, "weight": max(weight, 1e-9), "value": value})
        while len(blocks) >= 2 and blocks[-2]["value"] < blocks[-1]["value"] - 1e-12:
            b = blocks.pop()
            a = blocks.pop()
            w = a["weight"] + b["weight"]
            blocks.append(
                {
                    "start": a["start"],
                    "end": b["end"],
                    "weight": w,
                    "value": (a["value"] * a["weight"] + b["value"] * b["weight"]) / w,
                }
            )
    out = [0.0] * len(values)
    for block in blocks:
        for i in range(block["start"], block["end"] + 1):
            out[i] = block["value"]
    return out


def fit_curve(rows: list[dict], selected_bw: dict[str, float]) -> dict[str, dict[str, dict[str, float]]]:
    out: dict[str, dict[str, dict[str, float]]] = {}
    for pos in POSITIONS:
        data = [r for r in rows if r["position"] == pos]
        if not data:
            raise RuntimeError(f"no rows for {pos}")
        raw = []
        supports = []
        for slot in range(1, MAX_CURVE_SLOT + 1):
            pred, neff = kernel_predict(data, float(slot), selected_bw[pos])
            raw.append(pred)
            supports.append(neff)
        monotone = pava_decreasing(raw, supports)
        if any(monotone[i] < monotone[i + 1] - 1e-9 for i in range(len(monotone) - 1)):
            raise RuntimeError(f"monotonicity failed for {pos}")
        out[pos] = {
            str(slot): {
                "expected_ppg": round(monotone[slot - 1], 4),
                "raw_smoothed_ppg": round(raw[slot - 1], 4),
                "effective_n": round(supports[slot - 1], 2),
            }
            for slot in range(1, MAX_CURVE_SLOT + 1)
        }
    return out


def round_bucket(adp: float) -> int:
    return min(4, max(1, int(math.ceil(adp / 12.0))))


def cv_compare(rows: list[dict], selected_bw: dict[str, float]) -> dict[str, dict[str, float]]:
    metrics = {}
    for pos in POSITIONS:
        data = [r for r in rows if r["position"] == pos]
        years = sorted({r["year"] for r in data})
        kernel_errors = []
        round_errors = []
        pos_errors = []
        for holdout in years:
            train = [r for r in data if r["year"] != holdout]
            test = [r for r in data if r["year"] == holdout]
            if not train or not test:
                continue
            pos_mean = statistics.mean(r["career_ppg"] for r in train)
            by_round = defaultdict(list)
            for r in train:
                by_round[round_bucket(r["adp"])].append(r["career_ppg"])
            for r in test:
                kpred = kernel_predict(train, r["adp"], selected_bw[pos])[0]
                bucket_vals = by_round.get(round_bucket(r["adp"])) or [pos_mean]
                rpred = statistics.mean(bucket_vals)
                y = r["career_ppg"]
                kernel_errors.append(abs(y - kpred))
                round_errors.append(abs(y - rpred))
                pos_errors.append(abs(y - pos_mean))
        metrics[pos] = {
            "n": len(kernel_errors),
            "kernel_slot_mae": round(statistics.mean(kernel_errors), 4),
            "position_round_mae": round(statistics.mean(round_errors), 4),
            "position_only_mae": round(statistics.mean(pos_errors), 4),
        }
    return metrics


def curve_values(curve: dict, pos: str, slots=(1, 6, 12, 18, 24, 36, 48, 60, 72)) -> list[tuple[int, float, float]]:
    return [
        (slot, curve[pos][str(slot)]["expected_ppg"], curve[pos][str(slot)]["effective_n"])
        for slot in slots
    ]


def sensitivity(resolved: list[dict], core_curve: dict, core_bw: dict[str, float]) -> list[dict]:
    specs = (
        ("min_mock_selections_3", 3, 2022),
        ("min_mock_selections_10", 10, 2022),
        ("drop_2022_class", MIN_TIMES_DRAFTED, 2021),
    )
    results = []
    for label, min_times, max_year in specs:
        rows = core_filter(resolved, min_times=min_times, max_year=max_year)
        counts = Counter(r["position"] for r in rows)
        if any(counts[p] < 12 for p in POSITIONS):
            results.append({"test": label, "status": "insufficient_sample", "counts": dict(counts)})
            continue
        alt_bw = {}
        for pos in POSITIONS:
            alt_bw[pos] = select_bandwidth(rows, pos)[0]
        alt_curve = fit_curve(rows, alt_bw)
        pos_mad = {}
        for pos in POSITIONS:
            diffs = [
                abs(core_curve[pos][str(slot)]["expected_ppg"] - alt_curve[pos][str(slot)]["expected_ppg"])
                for slot in range(1, 49)
            ]
            pos_mad[pos] = round(statistics.mean(diffs), 4)
        results.append(
            {
                "test": label,
                "status": "ok",
                "counts": dict(counts),
                "selected_bandwidth": alt_bw,
                "mean_abs_curve_difference_slots_1_48": pos_mad,
            }
        )
    return results


def write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    adp_rows, adp_sources = load_adp()
    by_year_pid, identity, sleeper_sources = load_sleeper_stats()
    validate_scoring(by_year_pid, identity)
    resolved, unresolved, nonrookies = resolve_adp_rows(adp_rows, by_year_pid, identity)
    core = core_filter(resolved)
    counts = Counter(r["position"] for r in core)

    minimums = {"QB": 20, "RB": 60, "WR": 80, "TE": 15}
    for pos, floor in minimums.items():
        if counts[pos] < floor:
            raise RuntimeError(f"insufficient {pos} sample: {counts[pos]} < {floor}")
    if len(core) < 225:
        raise RuntimeError(f"insufficient total fitted sample: {len(core)}")

    selected_bw: dict[str, float] = {}
    cv_tables: dict[str, list[dict]] = {}
    for pos in POSITIONS:
        selected_bw[pos], cv_tables[pos] = select_bandwidth(core, pos)

    curve = fit_curve(core, selected_bw)
    comparisons = cv_compare(core, selected_bw)
    sensitivity_results = sensitivity(resolved, curve, selected_bw)

    # A smoothed exact-slot curve need not beat the coarse baseline in every sparse
    # position, but it must not be catastrophically worse. This is an audit guard,
    # not an optimization target.
    for pos, m in comparisons.items():
        if m["kernel_slot_mae"] > m["position_round_mae"] * 1.20:
            raise RuntimeError(f"{pos} exact-slot smoother is >20% worse than coarse position+round baseline: {m}")

    source_eligible = [r for r in adp_rows if r["adp"] <= MAX_TRAINING_ADP]
    match_rate = len([r for r in resolved if r["adp"] <= MAX_TRAINING_ADP]) / max(1, len(source_eligible))
    if match_rate < 0.78:
        raise RuntimeError(f"historical identity/outcome match rate too low: {match_rate:.3f}")

    snapshot = {
        "generated_at": generated_at,
        "description": "Normalized FFC 12-team Dynasty Rookie ADP rows resolved to Plebs-scored Sleeper career outcomes.",
        "training_years": list(ADP_YEARS),
        "last_complete_outcome_season": LAST_COMPLETE_SEASON,
        "rows": resolved,
        "unresolved": unresolved,
        "removed_as_nonrookie": nonrookies,
    }
    manifest = {
        "version": "pos-adj-ppg-research-v1",
        "generated_at": generated_at,
        "independence_rule": "No Dynasty Plebs result or manager data is used to fit expected PPG.",
        "formula": "POS ADJ PPG = career-to-date Plebs PPG - expected Plebs PPG(position, exact 12-team rookie slot)",
        "career_age_adjustment": False,
        "eligibility": "QB/RB/WR/TE true rookies with >=1 NFL regular-season game; production Plebs veterans remain excluded.",
        "scoring": {
            "pass_yd": 0.04,
            "pass_td": 6,
            "pass_int": -4,
            "pass_2pt": 2,
            "rush_yd": 0.1,
            "rush_td": 6,
            "rush_2pt": 2,
            "reception": 0.5,
            "rec_yd": 0.1,
            "rec_td": 6,
            "rec_2pt": 2,
            "fum_lost": -2,
            "fum_rec_td": 6,
            "return_td": 6,
        },
        "adp_source": "Fantasy Football Calculator standard 12-team Dynasty Rookie ADP REST API (separate from FFC 2-QB ADP).",
        "attribution": "ADP data courtesy of Fantasy Football Calculator.",
        "adp_sources": adp_sources,
        "outcome_sources": sleeper_sources,
        "calibration_checks": len(CALIBRATION),
        "source_rows": len(adp_rows),
        "resolved_outcome_rows": len(resolved),
        "nonrookie_rows_removed": len(nonrookies),
        "unresolved_or_no_game_rows": len(unresolved),
        "match_rate_within_adp_96": round(match_rate, 4),
        "core_filter": {
            "years": [min(ADP_YEARS), 2022],
            "min_times_drafted": MIN_TIMES_DRAFTED,
            "max_adp": MAX_TRAINING_ADP,
            "n": len(core),
            "position_counts": dict(counts),
        },
    }
    curve_artifact = {
        "version": "pos-adj-ppg-v1-research",
        "generated_at": generated_at,
        "status": "research_not_production",
        "definition": "Career PPG minus expected career PPG for a rookie of the same position at the exact draft slot.",
        "career_age_adjustment": False,
        "teams": 12,
        "training_adp_years": [2014, 2022],
        "outcomes_through": LAST_COMPLETE_SEASON,
        "min_times_drafted": MIN_TIMES_DRAFTED,
        "max_training_adp": MAX_TRAINING_ADP,
        "max_curve_slot": MAX_CURVE_SLOT,
        "selected_bandwidth": selected_bw,
        "curve": curve,
    }

    write_json(OUT / "adp_snapshot.json", snapshot)
    write_json(OUT / "source_manifest.json", manifest)
    write_json(OUT / "pos_adj_ppg_curve.json", curve_artifact)

    lines = [
        "# POS ADJ PPG validation report",
        "",
        f"Generated: `{generated_at}`",
        "",
        "## Locked definition",
        "",
        "`POS ADJ PPG = career-to-date Dynasty Plebs PPG - expected PPG(position, exact rookie draft slot)`",
        "",
        "No career-age adjustment is applied. No Dynasty Plebs manager or result data is used to fit the expectation curve.",
        "",
        "## Source / identity audit",
        "",
        f"- FFC source rows (QB/RB/WR/TE): **{len(adp_rows)}**",
        f"- Resolved rows with an NFL regular-season outcome: **{len(resolved)}**",
        f"- Historical rows removed because the player had already played before the listed ADP year: **{len(nonrookies)}**",
        f"- Unresolved or zero-game rows (not fitted): **{len(unresolved)}**",
        f"- Match/outcome rate for source rows with ADP <= {int(MAX_TRAINING_ADP)}: **{match_rate:.1%}**",
        f"- Core fitted sample (2014-2022, >= {MIN_TIMES_DRAFTED} human mock selections, ADP <= {int(MAX_TRAINING_ADP)}): **{len(core)}**",
        "- Core position counts: " + ", ".join(f"{p} {counts[p]}" for p in POSITIONS),
        f"- Exact Plebs scoring calibration: **{len(CALIBRATION)}/{len(CALIBRATION)} passed**",
        "",
        "The non-rookie filter is intentional: archived source anomalies such as a prior-year NFL player appearing on a later rookie board cannot leak into the expectation sample.",
        "",
        "## Leave-one-draft-class-out model validation",
        "",
        "Bandwidth is selected independently by position. The one-standard-error rule chooses the smoothest bandwidth whose error is statistically tied with the minimum-error candidate.",
        "",
        "| Pos | N | Selected bandwidth | Exact-slot kernel MAE | Pos+round MAE | Pos-only MAE |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for pos in POSITIONS:
        m = comparisons[pos]
        lines.append(
            f"| {pos} | {m['n']} | {selected_bw[pos]:.1f} | {m['kernel_slot_mae']:.3f} | {m['position_round_mae']:.3f} | {m['position_only_mae']:.3f} |"
        )
    lines += ["", "### Bandwidth grid", ""]
    for pos in POSITIONS:
        lines.append(f"**{pos}**")
        lines.append("")
        lines.append("| Bandwidth | Mean held-out-year MAE | SE |")
        lines.append("|---:|---:|---:|")
        for r in cv_tables[pos]:
            marker = " **selected**" if abs(r["bandwidth"] - selected_bw[pos]) < 1e-9 else ""
            lines.append(f"| {r['bandwidth']:.1f}{marker} | {r['mean_year_mae']:.3f} | {r['se']:.3f} |")
        lines.append("")

    lines += ["## Fitted curve anchors", "", "Expected career PPG at exact overall rookie slots; `n_eff` is the kernel's effective local sample support.", ""]
    for pos in POSITIONS:
        lines.append(f"**{pos}**")
        lines.append("")
        lines.append("| Slot | Expected PPG | n_eff |")
        lines.append("|---:|---:|---:|")
        for slot, expected, neff in curve_values(curve, pos):
            lines.append(f"| {slot} | {expected:.2f} | {neff:.1f} |")
        lines.append("")

    lines += ["## Sensitivity", "", "Mean absolute change in the fitted expectation curve over slots 1-48 versus the core specification.", "", "| Test | Status | QB | RB | WR | TE |", "|---|---|---:|---:|---:|---:|"]
    for test in sensitivity_results:
        diffs = test.get("mean_abs_curve_difference_slots_1_48") or {}
        lines.append(
            f"| {test['test']} | {test['status']} | {diffs.get('QB','—')} | {diffs.get('RB','—')} | {diffs.get('WR','—')} | {diffs.get('TE','—')} |"
        )

    lines += [
        "",
        "## Production gate",
        "",
        "This report does **not** deploy the metric. Before production, audit the unresolved/non-rookie lists, inspect curve stability/support, and test every historical Plebs pick against the frozen table. Production should consume the committed table rather than refit in the browser.",
        "",
    ]
    report = "\n".join(lines)
    (OUT / "validation_report.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
