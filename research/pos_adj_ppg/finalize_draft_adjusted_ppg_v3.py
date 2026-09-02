#!/usr/bin/env python3
"""Final eligibility gate for Dynasty Plebs Draft-Adjusted PPG.

V2 performs the independent position-at-draft audit. This final pass enforces
the already-locked scoring eligibility rule: a rookie must have played at least
one NFL regular-season game to receive Career PPG or Draft-Adjusted PPG.

A numeric 0.0 PPG attached to a zero-game metadata row is therefore *not* a
scored outcome. The pick remains a true rookie pick, but is unscored until an
NFL regular-season game is recorded.
"""
from __future__ import annotations

import csv
import io
import json
import math
import statistics
from collections import Counter, defaultdict

import finalize_draft_adjusted_ppg_v2 as v2

base = v2.base


def num(value):
    if value in (None, ""):
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def mean(values):
    vals = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return statistics.mean(vals) if vals else None


def fmt(value, digits=2):
    if value is None:
        return "—"
    return f"{value:+.{digits}f}" if value != 0 else f"{value:.{digits}f}"


rows = list(csv.DictReader(base.OUT_CSV.read_text(encoding="utf-8").splitlines()))
zero_game_demotions = []

for row in rows:
    games = num(row.get("career_games"))
    if row.get("status") == "scored" and not (games is not None and games > 0):
        zero_game_demotions.append((int(row["year"]), row["pick"], row["manager"], row["player"], games))
        row["status"] = "unscored"
        row["expected_ppg"] = ""
        row["draft_adj_ppg"] = ""

# Frank Gore Jr. is the concrete regression that exposed this gate. Fail closed
# if he ever reappears as scored without an NFL game.
frank = [r for r in rows if int(r["year"]) == 2024 and base.norm(r["player"]) == "frankgorejr"]
if len(frank) != 1:
    raise RuntimeError(f"Frank Gore Jr. audit row missing/duplicated: {frank}")
if frank[0]["status"] != "unscored" or (num(frank[0].get("career_games")) or 0) > 0:
    raise RuntimeError(f"Frank Gore Jr. zero-game eligibility gate failed: {frank[0]}")

scored = [r for r in rows if r.get("status") == "scored" and num(r.get("draft_adj_ppg")) is not None]
veterans = [r for r in rows if r.get("status") == "veteran_excluded"]
unscored = [r for r in rows if r.get("status") == "unscored"]

if len(veterans) != 9:
    raise RuntimeError(f"veteran count changed unexpectedly: {len(veterans)}")
if any((num(r.get("career_games")) or 0) <= 0 for r in scored):
    raise RuntimeError("zero-game row survived as a scored Draft-Adjusted PPG outcome")
if any(int(r["year"]) >= 2026 for r in scored):
    raise RuntimeError("2026 rookie outcome leaked into through-2025 results")

# The previously audited Seth totals are an explicit regression gate: 48 true
# rookie selections through 2025, of which 47 have a qualifying NFL game.
seth_rookies = [r for r in rows if r["manager"] == "Seth Miller" and int(r["year"]) <= 2025 and r["status"] != "veteran_excluded"]
seth_scored = [r for r in seth_rookies if r["status"] == "scored" and num(r.get("draft_adj_ppg")) is not None]
if len(seth_rookies) != 48 or len(seth_scored) != 47:
    raise RuntimeError(f"Seth rookie-count regression: rookies={len(seth_rookies)} scored={len(seth_scored)}")

# Rewrite the final ledger with LF line endings and cleared expectation/residual
# for every ineligible zero-game pick.
fields = [
    "year", "pick", "overall_slot", "manager", "player", "position", "position_source",
    "career_ppg", "expected_ppg", "draft_adj_ppg", "career_games", "through", "status",
]
out = io.StringIO()
w = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
w.writeheader()
for row in rows:
    w.writerow({k: row.get(k, "") for k in fields})
base.OUT_CSV.write_text(out.getvalue(), encoding="utf-8")

prod = {
    "version": "draft-adjusted-ppg-v2",
    "definition": "Career PPG minus the expected Career PPG for a rookie at the same position and draft slot.",
    "throughSeason": 2025,
    "curveVersion": base.curve_art.get("version"),
    "positionAudit": "same-year FFC rookie ADP, then historical NFL draft position, then Plebs/Sleeper fallback",
    "eligibility": "at least one NFL regular-season game",
    "picks": {},
}
for row in rows:
    key = f"{row['year']}|{base.norm(row['player'])}"
    item = {
        "pick": row["pick"],
        "overall": int(row["overall_slot"]),
        "pos": row.get("position") or "",
        "status": row["status"],
    }
    expected = num(row.get("expected_ppg"))
    residual = num(row.get("draft_adj_ppg"))
    career_ppg = num(row.get("career_ppg"))
    games = num(row.get("career_games"))
    if row["status"] == "scored" and expected is not None and residual is not None and games and games > 0:
        item["expectedPpg"] = round(expected, 6)
        item["draftAdjPpg"] = round(residual, 6)
        item["careerPpg"] = round(career_ppg if career_ppg is not None else expected + residual, 6)
        item["games"] = int(games)
    prod["picks"][key] = item

base.OUT_JSON.write_text(json.dumps(prod, indent=2, sort_keys=True) + "\n", encoding="utf-8")
base.OUT_JS.write_text("window.DRAFT_ADJUSTED_PPG=" + json.dumps(prod, separators=(",", ":"), ensure_ascii=False) + ";\n", encoding="utf-8")

by_manager = defaultdict(list)
for row in scored:
    by_manager[row["manager"]].append(row)
summary = []
for manager, rs in by_manager.items():
    rounds = {}
    for b in (1, 2, 3, 4):
        vals = [num(r.get("draft_adj_ppg")) for r in rs if min(4, int(str(r["pick"]).split(".")[0])) == b]
        rounds[b] = mean(vals)
    summary.append({
        "manager": manager,
        "n": len(rs),
        "avg": mean([num(r.get("career_ppg")) for r in rs]),
        "adj": mean([num(r.get("draft_adj_ppg")) for r in rs]),
        "rounds": rounds,
    })
summary.sort(key=lambda x: x["adj"], reverse=True)

source_counts = Counter(r.get("position_source") or "" for r in rows)
pos_counts = Counter(r.get("position") or "" for r in scored)
best = max(scored, key=lambda r: num(r.get("draft_adj_ppg")))
worst = min(scored, key=lambda r: num(r.get("draft_adj_ppg")))
seth_summary = next(x for x in summary if x["manager"] == "Seth Miller")

lines = [
    "# Dynasty Plebs Draft-Adjusted PPG final audit",
    "",
    "## Locked public definition",
    "",
    "**Career PPG minus the expected Career PPG for a rookie at the same position and draft slot.**",
    "",
    "## Final integrity gates",
    "",
    f"- Frozen curve: `{base.curve_art.get('version')}`",
    f"- Scored rookie picks: **{len(scored)}**",
    f"- Veteran selections excluded: **{len(veterans)}**",
    f"- Unscored/future rookie picks: **{len(unscored)}**",
    f"- Zero-game rows demoted from scored: **{len(zero_game_demotions)}**",
    "- Zero-game rows graded: **0**.",
    "- Eligibility: **at least one NFL regular-season game**.",
    f"- Seth true rookie picks through 2025: **{len(seth_rookies)}**",
    f"- Seth scored rookie picks through 2025: **{len(seth_scored)}**",
    f"- Position resolved from same-year FFC rookie ADP: **{source_counts['FFC same-year rookie ADP']}** draft events",
    f"- Position resolved from historical NFL draft data: **{source_counts['NFL draft history (PFR/nfldata)']}** draft events",
    f"- Remaining Plebs/Sleeper position fallbacks: **{source_counts['Plebs/Sleeper fallback']}** draft events",
    "- FFC vs NFL draft position conflicts on overlapping identities: **0**.",
    "- Compensatory-pick sequencing: **passed**.",
    "- Career-age adjustment: **none**.",
    "- Plebs manager/results data used to train expectation: **none**.",
    "",
    "### Zero-game eligibility corrections",
    "",
]
if zero_game_demotions:
    lines += ["| Year | Pick | Manager | Player | Games |", "|---:|---:|---|---|---:|"]
    for year, pick, manager, player, games in zero_game_demotions:
        lines.append(f"| {year} | {pick} | {manager} | {player} | {int(games or 0)} |")
else:
    lines.append("None.")

lines += [
    "",
    "## Scored position counts",
    "",
    ", ".join(f"{p} {pos_counts[p]}" for p in ("QB", "RB", "WR", "TE")),
    "",
    "## Manager results",
    "",
    "| Rank | Manager | Scored Picks | Draft-Adjusted PPG | Avg Career PPG | R1 | R2 | R3 | R4+ |",
    "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
]
for i, m in enumerate(summary, 1):
    lines.append(
        f"| {i} | {m['manager']} | {m['n']} | {fmt(m['adj'])} | {m['avg']:.2f} | "
        f"{fmt(m['rounds'][1])} | {fmt(m['rounds'][2])} | {fmt(m['rounds'][3])} | {fmt(m['rounds'][4])} |"
    )
lines += [
    "",
    "## Seth regression anchor",
    "",
    f"- Draft-Adjusted PPG: **{fmt(seth_summary['adj'])}** across **{seth_summary['n']}** scored picks.",
    f"- Round 1: **{fmt(seth_summary['rounds'][1])}**; Round 2: **{fmt(seth_summary['rounds'][2])}**; Round 3: **{fmt(seth_summary['rounds'][3])}**; Round 4+: **{fmt(seth_summary['rounds'][4])}**.",
    "",
    "## Extreme sanity check",
    "",
    f"- Highest: **{best['player']}** {best['year']} {best['pick']} = {fmt(num(best.get('draft_adj_ppg')))}",
    f"- Lowest: **{worst['player']}** {worst['year']} {worst['pick']} = {fmt(num(worst.get('draft_adj_ppg')))}",
    "",
    "## Production artifact",
    "",
    "`draft-adjusted-ppg.js` is generated only from this final audited ledger. The production site consumes the frozen per-pick results directly.",
    "",
]
base.OUT_MD.write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
