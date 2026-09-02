#!/usr/bin/env python3
"""Finalize the Dynasty Plebs Draft-Adjusted PPG application.

The base application audit proves ownership, veteran exclusion, chronological
pick sequencing (including compensatory picks), and Career PPG arithmetic.
This finalizer locks the *rookie-time position* used for the external benchmark.

Priority for position-at-draft:
1. Same-year Fantasy Football Calculator dynasty-rookie ADP position.
2. Existing Plebs/Sleeper position only when no same-year FFC identity exists.

This prevents later NFL position conversions (for example a drafted WR later
listed as TE) from changing the historical expectation applied to the pick.
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

HERE = Path(__file__).resolve().parent
BASE_CSV = HERE / "plebs_application_audit.csv"
SNAPSHOT = HERE / "adp_snapshot.json"
CURVE = HERE / "pos_adj_ppg_curve.json"
OUT_CSV = HERE / "draft_adjusted_ppg_audit.csv"
OUT_JSON = HERE / "draft_adjusted_ppg.json"
OUT_JS = HERE / "draft-adjusted-ppg.js"
OUT_MD = HERE / "draft_adjusted_ppg_report.md"

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
    "jamarithrash": "jamarithrash",
    "jamarthrash": "jamarithrash",
    "jamatthrash": "jamarithrash",
}


def norm(value: object) -> str:
    s = unicodedata.normalize("NFD", str(value or "").lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s)


def identity_keys(name: str):
    n = norm(name)
    vals = [n]
    if ALIASES.get(n):
        vals.append(ALIASES[n])
    for k, v in ALIASES.items():
        if v == n:
            vals.append(k)
    return list(dict.fromkeys(vals))


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


snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
curve_art = json.loads(CURVE.read_text(encoding="utf-8"))
curve = curve_art["curve"]

# Index every same-year historical rookie ADP position. Multiple FFC observations
# for the same player/year must agree on position or the build fails closed.
ffc_positions = defaultdict(set)
for row in snapshot.get("rows", []):
    year = int(row.get("year") or 0)
    pos = str(row.get("position") or "").upper()
    if year and pos in curve:
        ffc_positions[(year, norm(row.get("name")))].add(pos)
for row in snapshot.get("unresolved_or_zero_game", []):
    year = int(row.get("year") or 0)
    pos = str(row.get("position") or "").upper()
    if year and pos in curve:
        ffc_positions[(year, norm(row.get("name")))].add(pos)
for key, poss in ffc_positions.items():
    if len(poss) > 1:
        raise RuntimeError(f"conflicting FFC rookie positions for {key}: {sorted(poss)}")

base_rows = list(csv.DictReader(BASE_CSV.read_text(encoding="utf-8").splitlines()))
final_rows = []
position_disagreements = []
position_coverage = Counter()

for row in base_rows:
    year = int(row["year"])
    player = row["player"]
    base_pos = str(row.get("position") or "").upper()
    ffc_pos = None
    matched_key = None
    for key in identity_keys(player):
        poss = ffc_positions.get((year, key))
        if poss:
            ffc_pos = next(iter(poss))
            matched_key = key
            break
    if ffc_pos:
        pos = ffc_pos
        pos_source = "FFC same-year rookie ADP"
        position_coverage["ffc"] += 1
        if base_pos and base_pos != pos:
            position_disagreements.append((year, row["pick"], player, base_pos, pos))
    else:
        pos = base_pos
        pos_source = "Plebs/Sleeper fallback"
        position_coverage["fallback"] += 1

    career_ppg = num(row.get("career_ppg"))
    status = row.get("status") or "unscored"
    expected = residual = None
    if status == "scored" and career_ppg is not None:
        if pos not in curve:
            raise RuntimeError(f"scored pick has no modeled rookie position: {year} {row['pick']} {player} {pos!r}")
        overall = int(row["overall_slot"])
        cell = curve[pos].get(str(overall))
        if not cell:
            raise RuntimeError(f"missing frozen expectation {pos} slot {overall}")
        expected = float(cell["expected_ppg"])
        residual = career_ppg - expected

    final_rows.append({
        **row,
        "position": pos,
        "position_source": pos_source,
        "expected_ppg": expected,
        "draft_adj_ppg": residual,
    })

scored = [r for r in final_rows if r["status"] == "scored" and r["draft_adj_ppg"] is not None]
veterans = [r for r in final_rows if r["status"] == "veteran_excluded"]
unscored = [r for r in final_rows if r["status"] == "unscored"]
if len(scored) != 377:
    raise RuntimeError(f"expected 377 scored rookie picks from base audit, found {len(scored)}")
if len(veterans) != 9:
    raise RuntimeError(f"expected 9 veteran exclusions, found {len(veterans)}")
if any(int(r["year"]) >= 2026 for r in scored):
    raise RuntimeError("2026 rookie outcome leaked into through-2025 results")

# Known conversion anchors. These must be rookie-time WRs even if modern metadata
# lists a later position.
conversion_anchors = {
    (2019, "nkealharry"): "WR",
    (2019, "hakeembutler"): "WR",
}
for key, expected_pos in conversion_anchors.items():
    hits = [r for r in final_rows if int(r["year"]) == key[0] and norm(r["player"]) == key[1]]
    if len(hits) != 1 or hits[0]["position"] != expected_pos:
        raise RuntimeError(f"rookie-position conversion anchor failed for {key}: {hits}")

# Re-aggregate from final pick residuals only.
by_manager = defaultdict(list)
for row in scored:
    by_manager[row["manager"]].append(row)
summary = []
for manager, rows in by_manager.items():
    vals = [r["draft_adj_ppg"] for r in rows]
    round_vals = {}
    for b in (1, 2, 3, 4):
        subset = [r["draft_adj_ppg"] for r in rows if min(4, int(str(r["pick"]).split(".")[0])) == b]
        round_vals[b] = mean(subset)
    summary.append({
        "manager": manager,
        "n": len(rows),
        "avg_career_ppg": mean([num(r["career_ppg"]) for r in rows]),
        "draft_adj_ppg": mean(vals),
        "rounds": round_vals,
        "best": max(rows, key=lambda r: r["draft_adj_ppg"]),
        "worst": min(rows, key=lambda r: r["draft_adj_ppg"]),
    })
summary.sort(key=lambda r: r["draft_adj_ppg"], reverse=True)

# Write exact final ledger.
fields = [
    "year", "pick", "overall_slot", "manager", "player", "position", "position_source",
    "career_ppg", "expected_ppg", "draft_adj_ppg", "career_games", "through", "status",
]
out = io.StringIO()
w = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
w.writeheader()
for row in final_rows:
    x = dict(row)
    for k in ("career_ppg", "expected_ppg", "draft_adj_ppg"):
        v = num(x.get(k))
        x[k] = "" if v is None else f"{v:.6f}"
    w.writerow(x)
OUT_CSV.write_text(out.getvalue(), encoding="utf-8")

# Compact production map: one immutable audited row per real Plebs draft event.
prod = {
    "version": "draft-adjusted-ppg-v1",
    "definition": "Career PPG minus the expected Career PPG for a rookie at the same position and draft slot.",
    "throughSeason": 2025,
    "curveVersion": curve_art.get("version"),
    "picks": {},
}
for r in final_rows:
    key = f"{r['year']}|{norm(r['player'])}"
    item = {
        "pick": r["pick"],
        "overall": int(r["overall_slot"]),
        "pos": r["position"],
        "status": r["status"],
    }
    if r["draft_adj_ppg"] is not None:
        item["expectedPpg"] = round(float(r["expected_ppg"]), 6)
        item["draftAdjPpg"] = round(float(r["draft_adj_ppg"]), 6)
    prod["picks"][key] = item
OUT_JSON.write_text(json.dumps(prod, indent=2, sort_keys=True) + "\n", encoding="utf-8")
OUT_JS.write_text("window.DRAFT_ADJUSTED_PPG=" + json.dumps(prod, separators=(",", ":"), ensure_ascii=False) + ";\n", encoding="utf-8")

pos_counts = Counter(r["position"] for r in scored)
best = max(scored, key=lambda r: r["draft_adj_ppg"])
worst = min(scored, key=lambda r: r["draft_adj_ppg"])
lines = [
    "# Dynasty Plebs Draft-Adjusted PPG final audit",
    "",
    "## Locked public definition",
    "",
    "**Career PPG minus the expected Career PPG for a rookie at the same position and draft slot.**",
    "",
    "## Final integrity gates",
    "",
    f"- Frozen curve: `{curve_art.get('version')}`",
    f"- Scored rookie picks: **{len(scored)}**",
    f"- Veteran selections excluded: **{len(veterans)}**",
    f"- Unscored/future rookie picks: **{len(unscored)}**",
    f"- Position resolved from same-year FFC rookie ADP: **{position_coverage['ffc']}** draft events",
    f"- Position fallback to Plebs/Sleeper: **{position_coverage['fallback']}** draft events",
    f"- Position disagreements corrected: **{len(position_disagreements)}**",
    "- Compensatory-pick sequencing is inherited from and already passed by the base application audit.",
    "- Career-age adjustment: **none**.",
    "- Current/historical Plebs manager results used to train expectation: **none**.",
    "",
    "### Corrected later-position conversions",
    "",
]
if position_disagreements:
    lines += ["| Year | Pick | Player | Later metadata | Rookie position |", "|---:|---:|---|---|---|"]
    for year, pick, player, old, new in position_disagreements:
        lines.append(f"| {year} | {pick} | {player} | {old} | {new} |")
else:
    lines.append("No same-year FFC/Plebs position disagreements were found.")
lines += [
    "",
    "## Scored position counts",
    "",
    ", ".join(f"{p} {pos_counts[p]}" for p in ("QB", "RB", "WR", "TE")),
    "",
    "## Manager results",
    "",
    "| Rank | Manager | Picks | Draft-Adjusted PPG | Avg Career PPG | R1 | R2 | R3 | R4+ |",
    "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
]
for i, m in enumerate(summary, 1):
    lines.append(
        f"| {i} | {m['manager']} | {m['n']} | {fmt(m['draft_adj_ppg'])} | {m['avg_career_ppg']:.2f} | "
        f"{fmt(m['rounds'][1])} | {fmt(m['rounds'][2])} | {fmt(m['rounds'][3])} | {fmt(m['rounds'][4])} |"
    )
lines += [
    "",
    "## Extreme sanity check",
    "",
    f"- Highest: **{best['player']}** {best['year']} {best['pick']} = {fmt(best['draft_adj_ppg'])}",
    f"- Lowest: **{worst['player']}** {worst['year']} {worst['pick']} = {fmt(worst['draft_adj_ppg'])}",
    "",
    "## Production artifact",
    "",
    "`draft-adjusted-ppg.js` is generated only from this audited ledger. The website should consume it directly; the browser must not rebuild peer groups or refit the historical model.",
    "",
]
OUT_MD.write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
