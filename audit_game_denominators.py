import json
import re
import unicodedata
import urllib.request
from pathlib import Path

INDEX = Path('index.html')
OUT = Path('game_denominator_audit.txt')
LAST_COMPLETE_SEASON = 2025
OFFENSIVE_POSITIONS = {'QB','RB','WR','TE'}


def norm_name(value):
    s = unicodedata.normalize('NFD', str(value or '').lower())
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', s)


def without_suffix(value):
    for suffix in ('junior','senior','jr','sr','iii','ii','iv','v'):
        if value.endswith(suffix) and len(value) > len(suffix) + 3:
            return value[:-len(suffix)]
    return value

ALIASES = {
    'kenwalkeriii':'kennethwalkeriii','nathanieldell':'tankdell','deriusdavis':'dariusdavis',
    'jaelondarden':'jaleondarden','terracemarshall':'terracemarshalljr','brianrobinson':'brianrobinsonjr',
    'zachmoss':'zackmoss','gabrieldavis':'gabedavis','kennethgainwell':'kennygainwell',
    'dwayneeskridge':'deeeskridge','joshpalmer':'joshuapalmer','jamarithrash':'jamarithrash',
    'jamarthrash':'jamarithrash','jamatthrash':'jamarithrash'
}

def as_num(v):
    try: return float(v or 0)
    except (TypeError,ValueError): return 0.0

def plebs_points(record):
    s=record.get('stats') or {}
    return (as_num(s.get('pass_yd'))*.04+as_num(s.get('pass_td'))*6-as_num(s.get('pass_int'))*4+
            as_num(s.get('pass_2pt'))*2+as_num(s.get('rush_yd'))*.1+as_num(s.get('rush_td'))*6+
            as_num(s.get('rush_2pt'))*2+as_num(s.get('rec'))*.5+as_num(s.get('rec_yd'))*.1+
            as_num(s.get('rec_td'))*6+as_num(s.get('rec_2pt'))*2-as_num(s.get('fum_lost'))*2+
            as_num(s.get('fum_rec_td'))*6+(as_num(s.get('st_td')) if as_num(s.get('st_td')) else as_num(s.get('kick_ret_td'))+as_num(s.get('punt_ret_td')))*6)

def player_name(record):
    p=record.get('player') or {}
    return (p.get('full_name') or ' '.join(x for x in (p.get('first_name'),p.get('last_name')) if x) or record.get('player_name') or '').strip()

def player_position(record):
    p=record.get('player') or {}
    return p.get('position') or record.get('position') or ''

def resolve_key(target, lookup):
    n=norm_name(target); candidates=[n,ALIASES.get(n),without_suffix(n)]
    if ALIASES.get(n): candidates.append(without_suffix(ALIASES[n]))
    for c in candidates:
        if c and c in lookup: return c
    base=without_suffix(n); matches=[k for k in lookup if without_suffix(k)==base]
    return matches[0] if len(matches)==1 else None

def fetch_json(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (Dynasty-Plebs denominator audit)','Accept':'application/json,text/plain,*/*'})
    with urllib.request.urlopen(req,timeout=45) as r: return json.load(r)

html=INDEX.read_text(encoding='utf-8')
m=re.search(r'const rookieBoards=(\{.*?\});\nconst nf=',html,re.S)
if not m: raise RuntimeError('rookieBoards not found')
boards=json.loads(m.group(1))

season_data={}
for season in range(2019,LAST_COMPLETE_SEASON+1):
    records=fetch_json(f'https://api.sleeper.com/stats/nfl/{season}?season_type=regular')
    lookup={}
    for rec in records:
        name=player_name(rec); pos=player_position(rec)
        if not name or pos not in OFFENSIVE_POSITIONS: continue
        s=rec.get('stats') or {}
        gp_raw=s.get('gp')
        active_raw=s.get('gms_active')
        # old logic: zero gp falls through to gms_active
        old_games=int(as_num(gp_raw or active_raw))
        # corrected field semantics: an explicit zero gp must stay zero
        fixed_games=int(as_num(gp_raw)) if gp_raw is not None else int(as_num(active_raw))
        row={'name':name,'pos':pos,'gp_raw':gp_raw,'active_raw':active_raw,'old_games':old_games,'fixed_games':fixed_games,'points':plebs_points(rec)}
        n=norm_name(name); prev=lookup.get(n)
        if prev is None or (fixed_games,abs(row['points']))>(prev['fixed_games'],abs(prev['points'])): lookup[n]=row
    season_data[season]=lookup

entries=[]
for ys,b in boards.items():
    y=int(ys)
    for rnd in b.get('rounds',[]):
        for p in rnd:
            if p: entries.append((y,p))
entries.append((2025,"Don'te Thornton"))

affected=[]
season_cases=[]
for draft_year,name in entries:
    old_pts=old_games=fixed_pts=fixed_games=0
    pos=''; diffs=[]
    for season in range(max(draft_year,2019),LAST_COMPLETE_SEASON+1):
        key=resolve_key(name,season_data[season])
        if not key: continue
        row=season_data[season][key]; pos=pos or row['pos']
        if row['old_games']>0:
            old_pts += row['points']; old_games += row['old_games']
        if row['fixed_games']>0:
            fixed_pts += row['points']; fixed_games += row['fixed_games']
        if row['old_games']!=row['fixed_games']:
            diffs.append((season,row))
            season_cases.append((draft_year,name,season,row))
    if diffs:
        affected.append((draft_year,name,pos,old_pts,old_games,fixed_pts,fixed_games,diffs))

lines=[]
lines.append('Dynasty Plebs rookie career PPG denominator audit')
lines.append('Rule: explicit gp=0 must remain 0; do not fall through to gms_active.')
lines.append(f'Affected draft events: {len(affected)}')
lines.append(f'Affected player-seasons: {len(season_cases)}')
lines.append('')
for draft_year,name,pos,old_pts,old_games,fixed_pts,fixed_games,diffs in sorted(affected):
    old_ppg=old_pts/old_games if old_games else None
    fixed_ppg=fixed_pts/fixed_games if fixed_games else None
    lines.append(f'{draft_year} | {name} | {pos} | games {old_games} -> {fixed_games} | PPG {old_ppg:.3f} -> {fixed_ppg:.3f}' if fixed_ppg is not None and old_ppg is not None else f'{draft_year} | {name} | {pos} | games {old_games} -> {fixed_games}')
    for season,row in diffs:
        lines.append(f"  {season}: gp={row['gp_raw']!r}, gms_active={row['active_raw']!r}, old={row['old_games']}, fixed={row['fixed_games']}, points={row['points']:.2f}")
lines.append('')
lines.append('All changed player-seasons above are caused specifically by Python `gp or gms_active` treating an explicit 0 GP as missing.')
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines))
