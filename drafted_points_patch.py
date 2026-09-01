import json
import re
import unicodedata
import urllib.request
from pathlib import Path

INDEX = Path('index.html')
LAST_COMPLETE_SEASON = 2025
NAME_ALIASES = {
    'kennethgainwell': 'kennygainwell',
}


def norm_name(value):
    s = unicodedata.normalize('NFD', str(value or '').lower())
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', s)


def as_num(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def plebs_points(record):
    s = record.get('stats') or {}
    return (
        as_num(s.get('pass_yd')) * 0.04
        + as_num(s.get('pass_td')) * 6
        - as_num(s.get('pass_int')) * 4
        + as_num(s.get('pass_2pt')) * 2
        + as_num(s.get('rush_yd')) * 0.1
        + as_num(s.get('rush_td')) * 6
        + as_num(s.get('rush_2pt')) * 2
        + as_num(s.get('rec')) * 0.5
        + as_num(s.get('rec_yd')) * 0.1
        + as_num(s.get('rec_td')) * 6
        + as_num(s.get('rec_2pt')) * 2
        - as_num(s.get('fum_lost')) * 2
        + as_num(s.get('fum_rec_td')) * 6
        + (as_num(s.get('st_td')) if as_num(s.get('st_td')) else as_num(s.get('kick_ret_td')) + as_num(s.get('punt_ret_td'))) * 6
    )


def player_name(record):
    p = record.get('player') or {}
    return (
        p.get('full_name')
        or ' '.join(x for x in (p.get('first_name'), p.get('last_name')) if x)
        or record.get('player_name')
        or ''
    ).strip()


def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Dynasty-Plebs drafted-points patch)', 'Accept': 'application/json,text/plain,*/*'},
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.load(response)


html = INDEX.read_text(encoding='utf-8')
boards_m = re.search(r'const rookieBoards=(\{.*?\});\nconst nf=', html, re.S)
stats_m = re.search(r'const careerDraftStats=(\{.*?\});\nconst rookieBoards=', html, re.S)
if not boards_m or not stats_m:
    raise RuntimeError('rookieBoards/careerDraftStats not found')
boards = json.loads(boards_m.group(1))
career = json.loads(stats_m.group(1))

# All-time Drafted Points includes every selection made in a completed draft class,
# even the occasional veteran selected in the rookie draft. Rookie-only grading still
# excludes those veterans elsewhere. Rehydrate their post-draft fantasy points here
# because veteran_exclusion_patch intentionally strips them from rookie grading data.
veteran_events = []
for key, stat in career.items():
    if stat.get('excluded') != 'veteran':
        continue
    year_text, name_norm = key.split('|', 1)
    year = int(year_text)
    if year <= LAST_COMPLETE_SEASON:
        veteran_events.append((year, name_norm, key))

candidate_to_canonical = {}
for _, name_norm, _ in veteran_events:
    candidate_to_canonical[name_norm] = name_norm
    alias = NAME_ALIASES.get(name_norm)
    if alias:
        candidate_to_canonical[alias] = name_norm

season_points = {}
for season in range(2019, LAST_COMPLETE_SEASON + 1):
    rows = fetch_json(f'https://api.sleeper.com/stats/nfl/{season}?season_type=regular')
    lookup = {}
    for rec in rows:
        seen_norm = norm_name(player_name(rec))
        canonical = candidate_to_canonical.get(seen_norm)
        if not canonical:
            continue
        pts = plebs_points(rec)
        old = lookup.get(canonical)
        if old is None or abs(pts) > abs(old):
            lookup[canonical] = pts
    season_points[season] = lookup

for draft_year, name_norm, key in veteran_events:
    total = 0.0
    matched = False
    for season in range(draft_year, LAST_COMPLETE_SEASON + 1):
        if name_norm in season_points[season]:
            total += season_points[season][name_norm]
            matched = True
    if not matched:
        raise RuntimeError(f'No Sleeper scoring row found for completed veteran draft event {key}')
    career[key]['points'] = round(total, 2)

career_json = json.dumps(career, separators=(',', ':'), ensure_ascii=False)
html = html[:stats_m.start(1)] + career_json + html[stats_m.end(1):]

# Verify the completed-class selection count directly from the canonical board archive.
def manager_pick_count(manager, through=LAST_COMPLETE_SEASON):
    count = 0
    by_year = {}
    for year_text, board in boards.items():
        year = int(year_text)
        if year > through:
            continue
        n = sum(owner == manager for owners in board.get('ownersByRound', []) for owner in owners)
        by_year[year] = n
        count += n
    return count, by_year

seth_count, seth_by_year = manager_pick_count('Seth Miller')
print('Seth completed draft-pick count:', seth_count, seth_by_year)
if seth_count != 50:
    raise RuntimeError(f'Expected Seth Miller to have 50 draft selections from 2019-2025, found {seth_count}: {seth_by_year}')

# 2026 is deliberately excluded until that NFL regular season has a completed outcome.
new_metrics = r'''const completedDraftPicks=m=>(rookiePicks[m]||[]).filter(p=>p.year<=2025),draftedPointTotal=m=>completedDraftPicks(m).reduce((a,p)=>a+(Number.isFinite(p.points)?p.points:0),0),draftPickCount=m=>completedDraftPicks(m).length,draftedAvgPoints=m=>draftPickCount(m)?draftedPointTotal(m)/draftPickCount(m):0;
const metrics={wins:{label:'Wins',get:x=>x.w,fmt:v=>nf.format(v),sub:x=>`${x.w}-${x.l}`},pct:{label:'Win %',get:x=>x.p,fmt:v=>winDec(v),sub:x=>`${x.w}-${x.l}`},pf:{label:'Points For',get:x=>x.pf,fmt:v=>nf.format(v),sub:x=>`${x.s} seasons`},pa:{label:'Points Against',get:x=>x.pa,fmt:v=>nf.format(v),sub:x=>`${x.s} seasons`},rookiePts:{label:'Drafted Points',get:x=>draftedPointTotal(x.m),fmt:v=>nf.format(v),sub:x=>`${draftPickCount(x.m)} draft picks`},rookieAvg:{label:'Avg Pts / Draft Pick',get:x=>draftedAvgPoints(x.m),fmt:v=>nf.format(v),sub:x=>`${draftPickCount(x.m)} draft picks`}};let metric='wins';'''
html, n = re.subn(
    r"const completedRookiePicks=.*?;let metric='wins';",
    new_metrics,
    html,
    count=1,
    flags=re.S,
)
if n != 1:
    raise RuntimeError(f'Drafted metrics replacement count={n}')

INDEX.write_text(html, encoding='utf-8')
print(f'Rehydrated post-draft points for {len(veteran_events)} completed veteran draft events')
print('All-Time metrics renamed to Drafted Points / Avg Pts per Draft Pick; 2026 excluded')
