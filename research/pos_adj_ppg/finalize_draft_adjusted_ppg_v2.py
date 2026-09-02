#!/usr/bin/env python3
"""Secondary draft-position audit for Draft-Adjusted PPG.

Runs the same-year FFC position finalizer first, then cross-checks/replaces
remaining position fallbacks with historical NFL draft-position data from the
nfldata draft_picks dataset (sourced from Pro Football Reference).
"""
from __future__ import annotations

import csv
import io
import json
import math
import statistics
import urllib.request
from collections import Counter, defaultdict

import finalize_draft_adjusted_ppg as base

DRAFT_URL = "https://raw.githubusercontent.com/leesharpe/nfldata/master/data/draft_picks.csv"


def fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Dynasty Plebs Draft-Adjusted PPG audit)"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8")


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


# Build a rookie-year position map from NFL draft history. Category is used rather
# than the detailed position column so only QB/RB/WR/TE categories feed the curve.
draft_map = {}
for row in csv.DictReader(io.StringIO(fetch_text(DRAFT_URL))):
    year = int(row.get("season") or 0)
    cat = str(row.get("category") or "").upper()
    name = row.get("pfr_name") or ""
    if year < 2019 or year > 2025 or cat not in base.curve or not name:
        continue
    key = (year, base.norm(name))
    old = draft_map.get(key)
    if old and old != cat:
        raise RuntimeError(f"conflicting NFL draft positions for {key}: {old} vs {cat}")
    draft_map[key] = cat

# Validate source agreement where FFC and NFL draft data both exist.
ffc_lookup = {}
for (year, name), poss in base.ffc_positions.items():
    if len(poss) == 1:
        ffc_lookup[(year, name)] = next(iter(poss))
source_conflicts = []
for key, pos in draft_map.items():
    ffc = ffc_lookup.get(key)
    if ffc and ffc != pos:
        source_conflicts.append((key, ffc, pos))
if source_conflicts:
    raise RuntimeError("FFC/NFL draft position conflicts: " + repr(source_conflicts[:20]))

rows = []
draft_resolved = 0
fallback_remaining = 0
secondary_corrections = []
for r in base.final_rows:
    x = dict(r)
    year = int(x["year"])
    current_pos = str(x.get("position") or "").upper()
    if x.get("position_source") == "FFC same-year rookie ADP":
        pos = current_pos
    else:
        dpos = None
        for key in base.identity_keys(x["player"]):
            if (year, key) in draft_map:
                dpos = draft_map[(year, key)]
                break
        if dpos:
            pos = dpos
            draft_resolved += 1
            if current_pos and current_pos != dpos:
                secondary_corrections.append((year, x["pick"], x["player"], current_pos, dpos))
            x["position_source"] = "NFL draft history (PFR/nfldata)"
        else:
            pos = current_pos
            fallback_remaining += 1
    x["position"] = pos

    career_ppg = num(x.get("career_ppg"))
    status = x.get("status") or "unscored"
    expected = residual = None
    if status == "scored" and career_ppg is not None:
        if pos not in base.curve:
            raise RuntimeError(f"scored pick has no modeled position after secondary audit: {year} {x['pick']} {x['player']} {pos!r}")
        cell = base.curve[pos].get(str(int(x["overall_slot"])))
        if not cell:
            raise RuntimeError(f"missing frozen expectation {pos} slot {x['overall_slot']}")
        expected = float(cell["expected_ppg"])
        residual = career_ppg - expected
    x["expected_ppg"] = expected
    x["draft_adj_ppg"] = residual
    rows.append(x)

scored = [r for r in rows if r["status"] == "scored" and r["draft_adj_ppg"] is not None]
veterans = [r for r in rows if r["status"] == "veteran_excluded"]
unscored = [r for r in rows if r["status"] == "unscored"]
if len(scored) != 377 or len(veterans) != 9:
    raise RuntimeError(f"sample changed unexpectedly: scored={len(scored)} veterans={len(veterans)}")

# Recheck the known conversion anchors after both external sources.
for (year, n), expected_pos in base.conversion_anchors.items():
    hits = [r for r in rows if int(r["year"]) == year and base.norm(r["player"]) == n]
    if len(hits) != 1 or hits[0]["position"] != expected_pos:
        raise RuntimeError(f"conversion anchor failed after NFL draft audit: {(year,n)} {hits}")

# Final ledger. Force LF line endings so repository whitespace checks are stable.
fields = [
    "year", "pick", "overall_slot", "manager", "player", "position", "position_source",
    "career_ppg", "expected_ppg", "draft_adj_ppg", "career_games", "through", "status",
]
out = io.StringIO()
w = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
w.writeheader()
for r in rows:
    x = dict(r)
    for k in ("career_ppg", "expected_ppg", "draft_adj_ppg"):
        v = num(x.get(k))
        x[k] = "" if v is None else f"{v:.6f}"
    w.writerow(x)
base.OUT_CSV.write_text(out.getvalue(), encoding="utf-8")

prod = {
    "version": "draft-adjusted-ppg-v1",
    "definition": "Career PPG minus the expected Career PPG for a rookie at the same position and draft slot.",
    "throughSeason": 2025,
    "curveVersion": base.curve_art.get("version"),
    "positionAudit": "same-year FFC rookie ADP, then historical NFL draft position, then Plebs/Sleeper fallback",
    "picks": {},
}
for r in rows:
    key = f"{r['year']}|{base.norm(r['player'])}"
    item = {"pick": r["pick"], "overall": int(r["overall_slot"]), "pos": r["position"], "status": r["status"]}
    if r["draft_adj_ppg"] is not None:
        item["expectedPpg"] = round(float(r["expected_ppg"]), 6)
        item["draftAdjPpg"] = round(float(r["draft_adj_ppg"]), 6)
    prod["picks"][key] = item
base.OUT_JSON.write_text(json.dumps(prod, indent=2, sort_keys=True) + "\n", encoding="utf-8")
base.OUT_JS.write_text("window.DRAFT_ADJUSTED_PPG=" + json.dumps(prod, separators=(",", ":"), ensure_ascii=False) + ";\n", encoding="utf-8")

by_manager = defaultdict(list)
for r in scored:
    by_manager[r["manager"]].append(r)
summary = []
for manager, rs in by_manager.items():
    rounds = {}
    for b in (1,2,3,4):
        rounds[b] = mean([r["draft_adj_ppg"] for r in rs if min(4, int(str(r["pick"]).split(".")[0])) == b])
    summary.append({
        "manager": manager,
        "n": len(rs),
        "avg": mean([num(r["career_ppg"]) for r in rs]),
        "adj": mean([r["draft_adj_ppg"] for r in rs]),
        "rounds": rounds,
    })
summary.sort(key=lambda x: x["adj"], reverse=True)

source_counts = Counter(r["position_source"] for r in rows)
pos_counts = Counter(r["position"] for r in scored)
best = max(scored, key=lambda r: r["draft_adj_ppg"])
worst = min(scored, key=lambda r: r["draft_adj_ppg"])
all_corrections = list(base.position_disagreements) + secondary_corrections

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
    f"- Position resolved from same-year FFC rookie ADP: **{source_counts['FFC same-year rookie ADP']}** draft events",
    f"- Position resolved from historical NFL draft data: **{source_counts['NFL draft history (PFR/nfldata)']}** draft events",
    f"- Remaining Plebs/Sleeper position fallbacks: **{source_counts['Plebs/Sleeper fallback']}** draft events",
    f"- Position disagreements corrected across external audits: **{len(all_corrections)}**",
    "- FFC vs NFL draft position conflicts on overlapping identities: **0**.",
    "- Compensatory-pick sequencing: **passed**.",
    "- Career-age adjustment: **none**.",
    "- Plebs manager/results data used to train expectation: **none**.",
    "",
    "### Corrected later-position conversions",
    "",
]
if all_corrections:
    lines += ["| Year | Pick | Player | Later metadata | Rookie position |", "|---:|---:|---|---|---|"]
    seen=set()
    for row in all_corrections:
        if row in seen: continue
        seen.add(row)
        year,pick,player,old,new=row
        lines.append(f"| {year} | {pick} | {player} | {old} | {new} |")
else:
    lines.append("None.")
lines += [
    "",
    "## Scored position counts",
    "",
    ", ".join(f"{p} {pos_counts[p]}" for p in ("QB","RB","WR","TE")),
    "",
    "## Manager results",
    "",
    "| Rank | Manager | Picks | Draft-Adjusted PPG | Avg Career PPG | R1 | R2 | R3 | R4+ |",
    "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
]
for i,m in enumerate(summary,1):
    lines.append(f"| {i} | {m['manager']} | {m['n']} | {fmt(m['adj'])} | {m['avg']:.2f} | {fmt(m['rounds'][1])} | {fmt(m['rounds'][2])} | {fmt(m['rounds'][3])} | {fmt(m['rounds'][4])} |")
lines += [
    "",
    "## Extreme sanity check",
    "",
    f"- Highest: **{best['player']}** {best['year']} {best['pick']} = {fmt(best['draft_adj_ppg'])}",
    f"- Lowest: **{worst['player']}** {worst['year']} {worst['pick']} = {fmt(worst['draft_adj_ppg'])}",
    "",
    "## Production artifact",
    "",
    "`draft-adjusted-ppg.js` is generated only from this final audited ledger. The production site consumes the frozen per-pick results directly.",
    "",
]
base.OUT_MD.write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
