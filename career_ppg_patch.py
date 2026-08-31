import json
import re
import time
import unicodedata
import urllib.request
from pathlib import Path

INDEX = Path("index.html")
LAST_COMPLETE_SEASON = 2025
SEASONS = range(2019, LAST_COMPLETE_SEASON + 1)


def norm_name(value):
    s = unicodedata.normalize("NFD", str(value or "").lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s)


def without_suffix(value):
    for suffix in ("junior", "senior", "jr", "sr", "iii", "ii", "iv", "v"):
        if value.endswith(suffix) and len(value) > len(suffix) + 3:
            return value[: -len(suffix)]
    return value


ALIASES = {
    "kenwalkeriii": "kennethwalkeriii",
    "nathanieldell": "tankdell",
    "deriusdavis": "dariusdavis",
    "jaelondarden": "jaleondarden",
    "terracemarshall": "terracemarshalljr",
    "brianrobinson": "brianrobinsonjr",
}


def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Dynasty-Plebs historical-stat updater)",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.load(response)


def as_num(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def plebs_points(record):
    # Score Sleeper's raw regular-season stat line directly with the league's rules.
    # This deliberately ignores every precomputed fantasy-points field, so the
    # Fantasy Footballers yardage bonuses that appeared in 2024/2025 cannot leak in.
    s = record.get("stats") or {}
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
        + as_num(s.get("kick_ret_td")) * 6
        + as_num(s.get("punt_ret_td")) * 6
    )


def player_name(record):
    p = record.get("player") or {}
    return (
        p.get("full_name")
        or " ".join(x for x in (p.get("first_name"), p.get("last_name")) if x)
        or record.get("player_name")
        or ""
    ).strip()


def player_position(record):
    p = record.get("player") or {}
    return p.get("position") or record.get("position") or ""


def resolve_key(target, lookup):
    n = norm_name(target)
    candidates = [n, ALIASES.get(n), without_suffix(n)]
    alias = ALIASES.get(n)
    if alias:
        candidates.append(without_suffix(alias))
    for c in candidates:
        if c and c in lookup:
            return c
    base = without_suffix(n)
    matches = [k for k in lookup if without_suffix(k) == base]
    return matches[0] if len(matches) == 1 else None


html = INDEX.read_text(encoding="utf-8")
boards_match = re.search(r"const rookieBoards=(\{.*?\});\nconst nf=", html, re.S)
if not boards_match:
    raise SystemExit("rookieBoards not found in index.html")
boards = json.loads(boards_match.group(1))

# Sleeper is the scoring source of truth. Fantasy Footballers remains an audit source.
season_data = {}
for season in SEASONS:
    url = f"https://api.sleeper.com/stats/nfl/{season}?season_type=regular"
    records = fetch_json(url)
    if not isinstance(records, list) or not records:
        raise RuntimeError(f"Sleeper returned no regular-season stats for {season}")
    lookup = {}
    for rec in records:
        name = player_name(rec)
        if not name:
            continue
        n = norm_name(name)
        stats = rec.get("stats") or {}
        gp = int(as_num(stats.get("gp") or stats.get("gms_active")))
        lookup[n] = {
            "name": name,
            "position": player_position(rec),
            "games": gp,
            "points": plebs_points(rec),
        }
    season_data[season] = lookup
    print(f"Sleeper {season}: {len(lookup)} player stat rows")
    time.sleep(0.15)

# Hard calibration against Dynasty Plebs Sleeper screenshots supplied by the league.
checks = [
    (2019, "Kyler Murray", 301.28, 16),
    (2020, "Kyler Murray", 406.74, 16),
    (2021, "Kyler Murray", 328.48, 14),
    (2022, "Kyler Murray", 214.52, 11),
    (2023, "Kyler Murray", 156.36, 8),
    (2024, "Kyler Murray", 317.24, 17),
    (2025, "Kyler Murray", 83.78, 5),
    (2024, "A.J. Brown", 183.40, 13),
    (2025, "A.J. Brown", 181.30, 15),
    (2024, "Jonathan Taylor", 235.70, 14),
    (2025, "Jonathan Taylor", 339.30, 17),
    (2024, "Kyle Pitts", 107.70, 17),
    (2025, "Kyle Pitts", 166.80, 17),
]
for season, name, expected_points, expected_games in checks:
    key = resolve_key(name, season_data[season])
    if not key:
        raise RuntimeError(f"Calibration player missing: {name} {season}")
    got = season_data[season][key]
    if got["games"] != expected_games or abs(got["points"] - expected_points) > 0.11:
        raise RuntimeError(
            f"Sleeper calibration failed for {name} {season}: "
            f"got {got['points']:.2f}/{got['games']} expected {expected_points:.2f}/{expected_games}"
        )
print(f"Sleeper scoring calibration passed: {len(checks)}/{len(checks)} checks")

# One outcome per league draft event, not merely per NFL player name. A veteran can
# be drafted in multiple league draft classes and each pick starts its clock then.
draft_entries = []
for year_text, board in boards.items():
    draft_year = int(year_text)
    for round_players in board.get("rounds", []):
        for player in round_players:
            if player:
                draft_entries.append((draft_year, player))
draft_entries.append((2025, "Don'te Thornton"))

career = {}
unmatched = []
for draft_year, drafted_name in draft_entries:
    total_points = 0.0
    total_games = 0
    seasons_played = 0
    last_year = None
    position = ""
    matched_any = False
    for season in range(max(draft_year, 2019), LAST_COMPLETE_SEASON + 1):
        lookup = season_data.get(season, {})
        key = resolve_key(drafted_name, lookup)
        if not key:
            continue
        row = lookup[key]
        matched_any = True
        position = position or row["position"]
        if row["games"] > 0:
            total_points += row["points"]
            total_games += row["games"]
            seasons_played += 1
            last_year = season
    stat_key = f"{draft_year}|{norm_name(drafted_name)}"
    if total_games > 0:
        career[stat_key] = {
            "ppg": round(total_points / total_games, 6),
            "points": round(total_points, 2),
            "games": total_games,
            "seasons": seasons_played,
            "through": last_year,
            "pos": position,
        }
    elif matched_any:
        unmatched.append(f"{draft_year} {drafted_name} (0 GP)")
    elif draft_year <= LAST_COMPLETE_SEASON:
        unmatched.append(f"{draft_year} {drafted_name}")

print(f"Career outcomes built: {len(career)} league draft events")
if unmatched:
    print("No scored Sleeper outcome yet for:")
    for item in unmatched:
        print(" -", item)

career_json = json.dumps(career, separators=(",", ":"), ensure_ascii=False)
html, n = re.subn(
    r"const first3PPG=\{.*?\};\n",
    f"const careerDraftStats={career_json};\n",
    html,
    count=1,
    flags=re.S,
)
if n != 1:
    raise RuntimeError("first3PPG constant was not replaced")
html = re.sub(r"const first3ByNorm=.*?;\n", "", html, count=1)

start = html.find("function addPick(manager,year,round,slot,player)")
end = html.find("Object.entries(rookieBoards)", start)
if start < 0 or end < 0:
    raise RuntimeError("addPick block not found")
new_add = """function addPick(manager,year,round,slot,player){const stat=careerDraftStats[`${year}|${normName(player)}`];(rookiePicks[manager]??=[]).push({year,pick:`${round}.${String(slot).padStart(2,'0')}`,player,...(stat?{ppg:stat.ppg,points:stat.points,games:stat.games,seasons:stat.seasons,through:stat.through,pos:stat.pos}:{})})}\n"""
html = html[:start] + new_add + html[end:]

html = html.replace(
    "Complete recovered rookie-draft history, with mature WR/RB outcome intel layered in.",
    "Complete recovered rookie-draft history with career-to-date Dynasty Plebs scoring.",
)
html = html.replace("3Y ${p.ppg.toFixed(1)} PPG", "Career ${p.ppg.toFixed(1)} PPG")

new_intel = r'''function renderDraftIntel(){
 const box=document.getElementById('draftIntel'),allManagers=Object.keys(rookiePicks),getScored=m=>(rookiePicks[m]||[]).filter(p=>Number.isFinite(p.ppg)),scored=getScored(selectedManager);
 if(!scored.length){box.innerHTML=`<div class="intel-note">Career draft intel appears after a pick records an NFL regular-season game.</div>`;return}
 const bucket=p=>Math.min(4,Number(p.pick.split('.')[0])),avg=d=>d.length?d.reduce((a,p)=>a+p.ppg,0)/d.length:null;
 const allScored=allManagers.flatMap(getScored),leagueRound={};[1,2,3,4].forEach(r=>{leagueRound[r]=avg(allScored.filter(p=>bucket(p)===r))});
 const managerMetrics=allManagers.map(m=>{const d=getScored(m);if(!d.length)return null;const rounds={};[1,2,3,4].forEach(r=>rounds[r]=avg(d.filter(p=>bucket(p)===r)));const deltas=d.map(p=>p.ppg-leagueRound[bucket(p)]).filter(Number.isFinite);return{m,avg:avg(d),adj:deltas.length?deltas.reduce((a,v)=>a+v,0)/deltas.length:null,rounds,n:d.length}}).filter(Boolean);
 const me=managerMetrics.find(x=>x.m===selectedManager),rank=(value,values)=>{const valid=values.filter(Number.isFinite).sort((a,b)=>b-a);if(!Number.isFinite(value)||!valid.length)return'';return`Rank ${1+valid.filter(v=>v>value+1e-9).length} of ${valid.length}`};
 const best=[...scored].sort((a,b)=>b.ppg-a.ppg)[0],worst=[...scored].sort((a,b)=>a.ppg-b.ppg)[0],roundCards=[1,2,3,4].map(r=>{const d=scored.filter(p=>bucket(p)===r),value=avg(d),label=r===4?'Round 4+':`Round ${r}`,ranking=rank(value,managerMetrics.map(x=>x.rounds[r]));return`<div class="intel-card"><small>${label} Avg Career PPG</small><b>${value==null?'—':value.toFixed(1)}</b><strong>${ranking||'No scored picks'}</strong><span>${d.length} scored pick${d.length===1?'':'s'}</span></div>`}).join('');
 box.innerHTML=`<div class="intel-card"><small>Avg Career PPG / Pick</small><b>${me.avg.toFixed(1)}</b><strong>${rank(me.avg,managerMetrics.map(x=>x.avg))}</strong><span>${me.n} scored picks</span></div><div class="intel-card"><small>Round-Adjusted PPG</small><b>${me.adj==null?'—':(me.adj>=0?'+':'')+me.adj.toFixed(1)}</b><strong>${rank(me.adj,managerMetrics.map(x=>x.adj))}</strong><span>vs league avg at same round</span></div><div class="intel-card"><small>Best Pick</small><strong>${best.player}</strong><span>${best.year} · ${best.pick} · ${best.ppg.toFixed(1)} PPG · ${best.games} G</span></div><div class="intel-card"><small>Worst Pick</small><strong>${worst.player}</strong><span>${worst.year} · ${worst.pick} · ${worst.ppg.toFixed(1)} PPG · ${worst.games} G</span></div>${roundCards}<div class="intel-note">Career PPG uses every NFL regular-season game from that league draft year through 2025, under Dynasty Plebs scoring. New seasons roll into the same totals and retroactively update these draft outcomes.</div>`;
}'''

intel_start = html.find("function renderDraftIntel(){")
rookie_start = html.find("function renderRookies(){", intel_start)
if intel_start < 0 or rookie_start < 0:
    raise RuntimeError("renderDraftIntel/renderRookies boundary not found")
html = html[:intel_start] + new_intel + "\n" + html[rookie_start:]

INDEX.write_text(html, encoding="utf-8")
print("index.html updated with Sleeper-scored career draft intel")
