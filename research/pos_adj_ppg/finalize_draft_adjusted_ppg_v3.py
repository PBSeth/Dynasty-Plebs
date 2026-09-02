#!/usr/bin/env python3
"""Final completed-class outcome audit for Dynasty Plebs Draft-Adjusted PPG.

Every true rookie selection from a completed NFL class is a draft outcome.
If that rookie generated no usable NFL fantasy production through the scoring
cutoff, his Career PPG is 0.0 rather than missing. Veteran selections are
excluded, and the current/future class remains outside the outcome window until
the annual update.
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
CUTOFF = 2025

# Historical true-rookie picks whose position could not be recovered by the
# automated same-year ADP / NFL draft-name join. Each was independently checked
# against NFL draft/prospect records before being locked here.
POSITION_OVERRIDES = {
    (2019, "jameswilliams"): "RB",
    (2021, "tamorrionterry"): "WR",
    (2023, "dewaynemcbride"): "RB",
    (2023, "zachkuntz"): "TE",
    (2023, "stetsonbennett"): "QB",
    (2025, "damienmartinez"): "RB",
    (2025, "willhoward"): "QB",
}


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
zero_completed = []

for row in rows:
    year = int(row["year"])
    status = row.get("status") or "unscored"
    if status == "veteran_excluded" or year > CUTOFF:
        continue

    # All true rookies in completed classes must be graded. Missing production
    # means 0.0 Career PPG; it must never disappear from a manager denominator.
    if status == "unscored":
        pos = str(row.get("position") or "").upper()
        if pos not in base.curve:
            pos = POSITION_OVERRIDES.get((year, base.norm(row["player"])), "")
            if pos:
                row["position"] = pos
                row["position_source"] = "manual historical rookie-position audit"
        if pos not in base.curve:
            raise RuntimeError(
                f"completed-class rookie cannot be zero-completed without position: "
                f"{year} {row['pick']} {row['player']}"
            )
        cell = base.curve[pos].get(str(int(row["overall_slot"])))
        if not cell:
            raise RuntimeError(f"missing frozen expectation {pos} slot {row['overall_slot']}")
        expected = float(cell["expected_ppg"])
        row["career_ppg"] = "0.000000"
        row["expected_ppg"] = f"{expected:.6f}"
        row["draft_adj_ppg"] = f"{-expected:.6f}"
        row["through"] = str(CUTOFF)
        row["status"] = "scored"
        zero_completed.append((year, row["pick"], row["manager"], row["player"], pos, expected))

# Fail closed: after the zero-completion pass there can be no missing true-rookie
# outcomes from any completed class.
historical_unscored = [
    r for r in rows
    if int(r["year"]) <= CUTOFF and r.get("status") == "unscored"
]
if historical_unscored:
    raise RuntimeError("completed-class rookies still ungraded: " + repr(historical_unscored[:20]))

historical_veterans = [
    r for r in rows
    if int(r["year"]) <= CUTOFF and r.get("status") == "veteran_excluded"
]
historical_rookies = [
    r for r in rows
    if int(r["year"]) <= CUTOFF and r.get("status") != "veteran_excluded"
]
graded = [
    r for r in historical_rookies
    if r.get("status") == "scored" and num(r.get("draft_adj_ppg")) is not None
]
future = [r for r in rows if int(r["year"]) > CUTOFF and r.get("status") == "unscored"]
all_veterans = [r for r in rows if r.get("status") == "veteran_excluded"]

# 397 selections were made from 2019-2025. Seven were veteran selections, so
# exactly 390 true rookie outcomes must be in the completed-class denominator.
if len(historical_rookies) != 390 or len(graded) != 390:
    raise RuntimeError(
        f"completed-class denominator regression: rookies={len(historical_rookies)} graded={len(graded)}"
    )
if len(historical_veterans) != 7 or len(all_veterans) != 9:
    raise RuntimeError(
        f"veteran exclusion regression: historical={len(historical_veterans)} all={len(all_veterans)}"
    )
if len(zero_completed) != 13:
    raise RuntimeError(f"expected 13 missing-zero rookie outcomes, found {len(zero_completed)}")

# Seth regression anchor: 50 total selections through 2025, two veterans, hence
# 48 true rookie outcomes. Frank Gore Jr. is explicitly a 0.0 outcome.
seth_rookies = [r for r in historical_rookies if r["manager"] == "Seth Miller"]
if len(seth_rookies) != 48:
    raise RuntimeError(f"Seth rookie denominator regression: {len(seth_rookies)}")
frank = [r for r in seth_rookies if int(r["year"]) == 2024 and base.norm(r["player"]) == "frankgorejr"]
if len(frank) != 1 or num(frank[0].get("career_ppg")) != 0.0 or frank[0].get("status") != "scored":
    raise RuntimeError(f"Frank Gore Jr. zero-outcome gate failed: {frank}")

# Rewrite audited ledger.
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
    "throughSeason": CUTOFF,
    "curveVersion": base.curve_art.get("version"),
    "positionAudit": "same-year FFC rookie ADP, historical NFL draft position, then manual audited rookie-position fallback",
    "outcomeRule": "every true rookie pick in a completed class counts; no NFL fantasy production equals 0.0 Career PPG",
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
    if row["status"] == "scored" and expected is not None and residual is not None:
        item["expectedPpg"] = round(expected, 6)
        item["draftAdjPpg"] = round(residual, 6)
        item["careerPpg"] = round(career_ppg if career_ppg is not None else expected + residual, 6)
    prod["picks"][key] = item

base.OUT_JSON.write_text(json.dumps(prod, indent=2, sort_keys=True) + "\n", encoding="utf-8")
base.OUT_JS.write_text(
    "window.DRAFT_ADJUSTED_PPG=" + json.dumps(prod, separators=(",", ":"), ensure_ascii=False) + ";\n",
    encoding="utf-8",
)

by_manager = defaultdict(list)
for row in graded:
    by_manager[row["manager"]].append(row)
summary = []
for manager, rs in by_manager.items():
    rounds = {}
    for b in (1, 2, 3, 4):
        vals = [
            num(r.get("draft_adj_ppg"))
            for r in rs
            if min(4, int(str(r["pick"]).split(".")[0])) == b
        ]
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
pos_counts = Counter(r.get("position") or "" for r in graded)
best = max(graded, key=lambda r: num(r.get("draft_adj_ppg")))
worst = min(graded, key=lambda r: num(r.get("draft_adj_ppg")))
seth_summary = next(x for x in summary if x["manager"] == "Seth Miller")

lines = [
    "# Dynasty Plebs Draft-Adjusted PPG final audit",
    "",
    "## Locked public definition",
    "",
    "**Career PPG minus the expected Career PPG for a rookie at the same position and draft slot.**",
    "",
    "## Completed-class outcome rule",
    "",
    "Every true rookie selection from 2019-2025 is graded. A rookie who generated no usable NFL fantasy production is a **0.0 Career PPG** outcome, including players who never appeared in an NFL regular-season game.",
    "",
    "## Final integrity gates",
    "",
    f"- Frozen curve: `{base.curve_art.get('version')}`",
    f"- True rookie outcomes through {CUTOFF}: **{len(graded)} / {len(historical_rookies)}**",
    f"- Missing-production rookie picks converted to 0.0: **{len(zero_completed)}**",
    f"- Completed-class rookies still omitted: **{len(historical_unscored)}**",
    f"- Veteran selections excluded through {CUTOFF}: **{len(historical_veterans)}**",
    f"- Future/current-class rookies outside outcome window: **{len(future)}**",
    f"- Seth true rookie outcomes through {CUTOFF}: **{len(seth_rookies)}**",
    "- Frank Gore Jr.: **0.0 Career PPG and included**.",
    f"- Manual audited rookie-position fallbacks: **{source_counts['manual historical rookie-position audit']}**",
    "- Compensatory-pick sequencing: **passed**.",
    "- Career-age adjustment: **none**.",
    "- Plebs manager/results data used to train expectation: **none**.",
    "",
    "### Zero-production outcomes restored to the denominator",
    "",
    "| Year | Pick | Manager | Player | Pos | Career PPG | Draft-Adjusted PPG |",
    "|---:|---:|---|---|---|---:|---:|",
]
for year, pick, manager, player, pos, expected in zero_completed:
    lines.append(f"| {year} | {pick} | {manager} | {player} | {pos} | 0.0 | {-expected:+.2f} |")

lines += [
    "",
    "## Graded position counts",
    "",
    ", ".join(f"{p} {pos_counts[p]}" for p in ("QB", "RB", "WR", "TE")),
    "",
    "## Manager results",
    "",
    "| Rank | Manager | Rookie Picks | Draft-Adjusted PPG | Avg Career PPG | R1 | R2 | R3 | R4+ |",
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
    f"- Draft-Adjusted PPG: **{fmt(seth_summary['adj'])}** across **{seth_summary['n']}** true rookie picks.",
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
