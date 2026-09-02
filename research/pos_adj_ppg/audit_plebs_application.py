#!/usr/bin/env python3
"""Apply the frozen POS ADJ PPG curve to every Dynasty Plebs rookie pick.

This is an audit only. It reads the site's recovered draft boards and existing
careerDraftStats, calculates the exact pick-level residual, and emits a complete
pick ledger + manager summary. It never refits the external expectation curve.
"""
from __future__ import annotations

import csv
import io
import json
import math
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "research" / "pos_adj_ppg"
INDEX = ROOT / "index.html"
CURVE_PATH = HERE / "pos_adj_ppg_curve.json"
OUT_CSV = HERE / "plebs_application_audit.csv"
OUT_MD = HERE / "plebs_application_report.md"


def norm_name(value: object) -> str:
    s = unicodedata.normalize("NFD", str(value or "").lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s)


def mean(values):
    vals = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return statistics.mean(vals) if vals else None


def extract_json_constant(html: str, name: str, next_marker: str) -> dict:
    pattern = rf"const {re.escape(name)}=(\{{.*?\}});\n{re.escape(next_marker)}"
    m = re.search(pattern, html, re.S)
    if not m:
        raise RuntimeError(f"could not extract {name} from index.html")
    return json.loads(m.group(1))


def fmt(value, digits=2):
    if value is None:
        return "—"
    return f"{value:+.{digits}f}" if value != 0 else f"{value:.{digits}f}"


html = INDEX.read_text(encoding="utf-8")
boards = extract_json_constant(html, "rookieBoards", "const nf=")
career = extract_json_constant(html, "careerDraftStats", "const rookieBoards=")
curve_art = json.loads(CURVE_PATH.read_text(encoding="utf-8"))
curve = curve_art["curve"]
max_slot = int(curve_art.get("max_curve_slot") or 72)

if curve_art.get("career_age_adjustment") is not False:
    raise RuntimeError("career-age adjustment unexpectedly enabled")
if "v4" not in str(curve_art.get("version")):
    raise RuntimeError(f"expected audited V4 curve, found {curve_art.get('version')}")

# Anchors cross-checked against the recovered league history / QB-TE entry sheet.
anchors = {
    (2019, 2, 3): ("Kyler Murray", "Seth Miller"),
    (2021, 1, 6): ("Kyle Pitts", "Seth Miller"),
    (2023, 3, 1): ("Sam LaPorta", "Seth Miller"),
    (2024, 3, 12): ("Bo Nix", "Seth Miller"),
    (2025, 1, 6): ("Cam Ward", "Clint Hudson"),
}

ledger = []
shape_errors = []
owner_errors = []
anchor_seen = {}

for year_text, board in sorted(boards.items(), key=lambda kv: int(kv[0])):
    year = int(year_text)
    rounds = board.get("rounds") or []
    owners = board.get("ownersByRound") or []
    if len(rounds) != len(owners):
        shape_errors.append(f"{year}: {len(rounds)} player rounds vs {len(owners)} owner rounds")
        continue
    for r_idx, players in enumerate(rounds, start=1):
        owner_row = owners[r_idx - 1]
        if len(players) != len(owner_row):
            shape_errors.append(f"{year} R{r_idx}: {len(players)} players vs {len(owner_row)} owners")
            continue
        if len(players) != 12:
            shape_errors.append(f"{year} R{r_idx}: expected 12 slots, found {len(players)}")
        for s_idx, player in enumerate(players, start=1):
            if not player:
                continue
            owner = owner_row[s_idx - 1] if s_idx - 1 < len(owner_row) else None
            if not owner:
                owner_errors.append(f"{year} {r_idx}.{s_idx:02d} {player}: missing owner")
                owner = "UNKNOWN"
            overall = (r_idx - 1) * 12 + s_idx
            if overall > max_slot:
                raise RuntimeError(f"curve stops at {max_slot}, but league has {year} {r_idx}.{s_idx:02d}")
            key = f"{year}|{norm_name(player)}"
            stat = career.get(key) or {}
            excluded = stat.get("excluded") == "veteran"
            ppg = stat.get("ppg")
            pos = str(stat.get("pos") or "").upper()
            expected = None
            residual = None
            status = "unscored"
            if excluded:
                status = "veteran_excluded"
            elif isinstance(ppg, (int, float)) and math.isfinite(float(ppg)):
                if pos not in curve:
                    raise RuntimeError(f"eligible scored pick lacks modeled position: {year} {player} pos={pos!r}")
                c = curve[pos].get(str(overall))
                if not c:
                    raise RuntimeError(f"missing curve cell {pos} slot {overall}")
                expected = float(c["expected_ppg"])
                residual = float(ppg) - expected
                status = "scored"
            ledger.append(
                {
                    "year": year,
                    "round": r_idx,
                    "slot_in_round": s_idx,
                    "pick": f"{r_idx}.{s_idx:02d}",
                    "overall_slot": overall,
                    "manager": owner,
                    "player": player,
                    "position": pos or stat.get("pos") or "",
                    "career_ppg": float(ppg) if isinstance(ppg, (int, float)) else None,
                    "expected_ppg": expected,
                    "pos_adj_ppg": residual,
                    "career_games": stat.get("games"),
                    "through": stat.get("through"),
                    "status": status,
                }
            )
            if (year, r_idx, s_idx) in anchors:
                anchor_seen[(year, r_idx, s_idx)] = (player, owner)

if shape_errors:
    raise RuntimeError("draft-board shape audit failed:\n" + "\n".join(shape_errors))
if owner_errors:
    raise RuntimeError("draft ownership audit failed:\n" + "\n".join(owner_errors))
for key, expected_anchor in anchors.items():
    if anchor_seen.get(key) != expected_anchor:
        raise RuntimeError(f"league-history anchor mismatch {key}: got {anchor_seen.get(key)}, expected {expected_anchor}")

scored = [r for r in ledger if r["status"] == "scored"]
veterans = [r for r in ledger if r["status"] == "veteran_excluded"]
unscored = [r for r in ledger if r["status"] == "unscored"]
if len(veterans) != 9:
    raise RuntimeError(f"expected exactly 9 known veteran selections, found {len(veterans)}")
if not scored:
    raise RuntimeError("no scored rookie picks found")

# Every scored residual must be exactly actual minus frozen external expectation.
for row in scored:
    check = row["career_ppg"] - row["expected_ppg"]
    if abs(check - row["pos_adj_ppg"]) > 1e-10:
        raise RuntimeError(f"residual arithmetic mismatch: {row}")

# 2026 rookie outcomes should not leak into a benchmark/results snapshot that is
# explicitly scored only through the last complete 2025 NFL season.
if any(r["status"] == "scored" for r in ledger if r["year"] >= 2026):
    raise RuntimeError("2026 rookie result leaked into through-2025 career outcomes")

by_manager = defaultdict(list)
for row in scored:
    by_manager[row["manager"]].append(row)
manager_summary = []
for manager, rows in by_manager.items():
    vals = [r["pos_adj_ppg"] for r in rows]
    round_values = {}
    for bucket in (1, 2, 3, 4):
        subset = [r["pos_adj_ppg"] for r in rows if min(4, r["round"]) == bucket]
        round_values[bucket] = mean(subset)
    manager_summary.append(
        {
            "manager": manager,
            "n": len(rows),
            "avg_career_ppg": mean([r["career_ppg"] for r in rows]),
            "pos_adj_ppg": mean(vals),
            "round_values": round_values,
            "best": max(rows, key=lambda r: r["pos_adj_ppg"]),
            "worst": min(rows, key=lambda r: r["pos_adj_ppg"]),
        }
    )
manager_summary.sort(key=lambda r: r["pos_adj_ppg"], reverse=True)

# The manager metric must equal the mean of pick-level residuals, with no manager
# baseline or current-league state entering the expectation calculation.
for m in manager_summary:
    direct = statistics.mean(r["career_ppg"] - r["expected_ppg"] for r in by_manager[m["manager"]])
    if abs(direct - m["pos_adj_ppg"]) > 1e-10:
        raise RuntimeError(f"manager aggregation mismatch for {m['manager']}")

columns = [
    "year", "pick", "overall_slot", "manager", "player", "position",
    "career_ppg", "expected_ppg", "pos_adj_ppg", "career_games", "through", "status",
]
out = io.StringIO()
writer = csv.DictWriter(out, fieldnames=columns, extrasaction="ignore")
writer.writeheader()
for row in ledger:
    writable = dict(row)
    for key in ("career_ppg", "expected_ppg", "pos_adj_ppg"):
        if writable.get(key) is not None:
            writable[key] = f"{writable[key]:.6f}"
    writer.writerow(writable)
OUT_CSV.write_text(out.getvalue(), encoding="utf-8")

pos_counts = Counter(r["position"] for r in scored)
round_counts = Counter(min(4, r["round"]) for r in scored)
best_overall = max(scored, key=lambda r: r["pos_adj_ppg"])
worst_overall = min(scored, key=lambda r: r["pos_adj_ppg"])

lines = [
    "# Dynasty Plebs POS ADJ PPG application audit",
    "",
    f"Curve: `{curve_art.get('version')}`",
    "",
    "## Definition",
    "",
    "**POS ADJ PPG = Career PPG − expected Career PPG for a rookie of the same position at that exact 12-team draft slot.**",
    "",
    "The expectation table is frozen before this script reads any Dynasty Plebs manager/result data. Managers only enter after the pick-level residual exists, for aggregation and display.",
    "",
    "## Integrity gates",
    "",
    f"- Draft years present: **{min(int(y) for y in boards)}–{max(int(y) for y in boards)}**",
    "- Every recovered draft round contains exactly **12 slots** and has a parallel owner row.",
    f"- Historical pick anchors passed: **{len(anchors)}/{len(anchors)}**.",
    f"- Known veteran selections excluded: **{len(veterans)}**.",
    f"- Eligible scored rookie picks: **{len(scored)}**.",
    f"- Unscored rookie picks: **{len(unscored)}** (includes future/zero-game players; they do not affect manager grades).",
    "- 2026 rookie outcomes in through-2025 results: **0**.",
    "- Pick-level residual arithmetic and manager mean re-aggregation: **passed**.",
    "",
    "## Scored sample",
    "",
    "Position counts: " + ", ".join(f"{p} {pos_counts[p]}" for p in ("QB", "RB", "WR", "TE")),
    "",
    "Display-round counts: " + ", ".join(f"R{r if r < 4 else '4+'} {round_counts[r]}" for r in (1, 2, 3, 4)),
    "",
    "## Manager results",
    "",
    "| Rank | Manager | Picks | POS ADJ PPG | Avg Career PPG | R1 | R2 | R3 | R4+ | Best | Worst |",
    "|---:|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
]
for rank, m in enumerate(manager_summary, start=1):
    b, w = m["best"], m["worst"]
    lines.append(
        f"| {rank} | {m['manager']} | {m['n']} | {fmt(m['pos_adj_ppg'])} | {m['avg_career_ppg']:.2f} | "
        f"{fmt(m['round_values'][1])} | {fmt(m['round_values'][2])} | {fmt(m['round_values'][3])} | {fmt(m['round_values'][4])} | "
        f"{b['player']} {b['pick']} ({fmt(b['pos_adj_ppg'])}) | {w['player']} {w['pick']} ({fmt(w['pos_adj_ppg'])}) |"
    )

lines += [
    "",
    "## Extreme pick sanity check",
    "",
    f"- Highest residual: **{best_overall['player']}**, {best_overall['manager']} {best_overall['year']} {best_overall['pick']}: Career {best_overall['career_ppg']:.2f} − Expected {best_overall['expected_ppg']:.2f} = **{fmt(best_overall['pos_adj_ppg'])}**.",
    f"- Lowest residual: **{worst_overall['player']}**, {worst_overall['manager']} {worst_overall['year']} {worst_overall['pick']}: Career {worst_overall['career_ppg']:.2f} − Expected {worst_overall['expected_ppg']:.2f} = **{fmt(worst_overall['pos_adj_ppg'])}**.",
    "",
    "## Production rule",
    "",
    "The website should consume the frozen curve and calculate the same pick residuals. It must not construct peer groups from current or historical Plebs managers. Round 4+ is a display bucket only; each pick retains its exact overall-slot expectation.",
    "",
]
OUT_MD.write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
