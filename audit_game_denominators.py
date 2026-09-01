import csv
import io
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
    'jamarthrash':'jamarithrash','jamatthrash':'jamarithrash','travisetienne':'travisetiennejr',
    'jjarcegawhiteside':'jjawhiteside','ajbrown':'arthurbrown','cjstroud':'cjstroud',
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

def sleeper_name(record):
    p=record.get('player') or {}
    return (p.get('full_name') or ' '.join(x for x in (p.get('first_name'),p.get('last_name')) if x) or record.get('player_name') or '').strip()

def sleeper_position(record):
    p=record.get('player') or {}
    return p.get('position') or record.get('position') or ''

def resolve_key(target, lookup):
    n=norm_name(target); candidates=[n,ALIASES.get(n),without_suffix(n)]
    if ALIASES.get(n): candidates.append(without_suffix(ALIASES[n]))
    for c in candidates:
        if c and c in lookup: return c
    base=without_suffix(n); matches=[k for k in lookup if without_suffix(k)==base]
    return matches[0] if len(matches)==1 else None

def fetch_bytes(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (Dynasty-Plebs denominator audit)','Accept':'*/*'})
    with urllib.request.urlopen(req,timeout=120) as r: return r.read()

def fetch_json(url):
    return json.loads(fetch_bytes(url).decode('utf-8'))

def read_csv_url(url):
    return csv.DictReader(io.StringIO(fetch_bytes(url).decode('utf-8-sig',errors='replace')))

html=INDEX.read_text(encoding='utf-8')
boards_match=re.search(r'const rookieBoards=(\{.*?\});\nconst nf=',html,re.S)
stats_match=re.search(r'const careerDraftStats=(\{.*?\});\nconst rookieBoards=',html,re.S)
if not boards_match or not stats_match: raise RuntimeError('rookieBoards/careerDraftStats not found')
boards=json.loads(boards_match.group(1)); current=json.loads(stats_match.group(1))
entries=[]
for ys,b in boards.items():
    y=int(ys)
    for rnd in b.get('rounds',[]):
        for p in rnd:
            if p: entries.append((y,p))
entries.append((2025,"Don'te Thornton"))

# Resolve draft names once to nflverse's stable GSIS player id.
players_rows=list(read_csv_url('https://github.com/nflverse/nflverse-data/releases/download/players/players.csv'))
name_to_ids={}
id_to_name={}
for r in players_rows:
    pid=(r.get('gsis_id') or '').strip()
    pos=(r.get('position') or '').strip()
    if not pid or (pos and pos not in OFFENSIVE_POSITIONS): continue
    labels=set()
    for k in ('display_name','football_name','short_name'):
        if r.get(k): labels.add(norm_name(r[k]))
    first=(r.get('common_first_name') or r.get('first_name') or '').strip(); last=(r.get('last_name') or '').strip()
    if first and last: labels.add(norm_name(first+' '+last))
    for lab in labels:
        if lab: name_to_ids.setdefault(lab,set()).add(pid)
    id_to_name[pid]=r.get('display_name') or (first+' '+last).strip()

def resolve_player_id(name):
    n=norm_name(name); candidates=[n,ALIASES.get(n),without_suffix(n)]
    if ALIASES.get(n): candidates.append(without_suffix(ALIASES[n]))
    ids=set()
    for c in candidates:
        if c: ids |= name_to_ids.get(c,set())
    if len(ids)==1: return next(iter(ids))
    base=without_suffix(n)
    for lab,vals in name_to_ids.items():
        if without_suffix(lab)==base: ids |= vals
    return next(iter(ids)) if len(ids)==1 else None

resolved={name:resolve_player_id(name) for _,name in entries}
unresolved=sorted({name for _,name in entries if not resolved[name]})
resolved_ids={pid for pid in resolved.values() if pid}

# Independent appearance source: nflverse official weekly player stats. Each REG row is
# a player-game keyed by GSIS id; count unique game_id values. This handles 0-point games
# and correctly gives 0 games for IR/practice-squad seasons with no appearance.
official_games={}
for season in range(2019,LAST_COMPLETE_SEASON+1):
    games={pid:set() for pid in resolved_ids}
    url=f'https://github.com/nflverse/nflverse-data/releases/download/player_stats/player_stats_{season}.csv'
    for row in read_csv_url(url):
        if (row.get('season_type') or '').upper()!='REG': continue
        pid=(row.get('player_id') or '').strip()
        if pid not in resolved_ids: continue
        game=row.get('game_id') or f"{row.get('week','?')}|{row.get('team','?')}|{row.get('opponent_team','?')}"
        games[pid].add(game)
    official_games[season]={pid:len(gs) for pid,gs in games.items()}
    print('official rows',season,sum(official_games[season].values()))

# Sleeper remains the fantasy-scoring source; its GP/gms_active fields are diagnostic only.
sleeper={}
for season in range(2019,LAST_COMPLETE_SEASON+1):
    lookup={}
    for rec in fetch_json(f'https://api.sleeper.com/stats/nfl/{season}?season_type=regular'):
        name=sleeper_name(rec); pos=sleeper_position(rec)
        if not name or pos not in OFFENSIVE_POSITIONS: continue
        s=rec.get('stats') or {}
        row={'name':name,'pos':pos,'sleeper_gp':int(as_num(s.get('gp') or s.get('gms_active'))),'gp_raw':s.get('gp'),'active_raw':s.get('gms_active'),'points':plebs_points(rec)}
        n=norm_name(name); old=lookup.get(n)
        if old is None or (row['sleeper_gp'],abs(row['points']))>(old['sleeper_gp'],abs(old['points'])): lookup[n]=row
    sleeper[season]=lookup

season_diffs=[]; scoring_missing=[]; rebuilt={}
for draft_year,name in entries:
    pid=resolved.get(name)
    if not pid: continue
    total_points=0.0; total_games=0; played_seasons=0; through=None; pos=''
    for season in range(max(draft_year,2019),LAST_COMPLETE_SEASON+1):
        gp=official_games[season].get(pid,0)
        skey=resolve_key(name,sleeper[season]); srow=sleeper[season].get(skey) if skey else None
        sleeper_gp=srow['sleeper_gp'] if srow else 0
        points=srow['points'] if srow else 0.0
        if srow: pos=pos or srow['pos']
        if sleeper_gp!=gp:
            season_diffs.append((draft_year,name,season,sleeper_gp,gp,points,srow))
        if gp>0:
            total_games += gp; total_points += points; played_seasons += 1; through=season
            if not srow: scoring_missing.append((draft_year,name,season,gp))
    key=f'{draft_year}|{norm_name(name)}'
    if total_games>0:
        rebuilt[key]={'ppg':total_points/total_games,'points':total_points,'games':total_games,'seasons':played_seasons,'through':through,'pos':pos}

career_changes=[]
all_keys=set(current)|set(rebuilt)
for key in sorted(all_keys):
    old=current.get(key); new=rebuilt.get(key)
    if old and old.get('excluded')=='veteran': continue
    if old and new:
        if old.get('games')!=new.get('games') or abs(float(old.get('ppg',0))-new['ppg'])>0.0005:
            career_changes.append((key,old,new))
    elif old or new:
        career_changes.append((key,old,new))

lines=[]
lines.append('Dynasty Plebs rookie career PPG denominator audit — official player-game cross-check')
lines.append('Fantasy points: Sleeper raw regular-season stat totals scored with Plebs rules.')
lines.append('Games: nflverse official weekly player-stats rows, REG only, unique game_id by GSIS player id.')
lines.append('Rule: only games actually appeared in count; zero-game seasons and active-but-no-appearance weeks do not.')
lines.append(f'Draft names resolved to stable GSIS id: {len(resolved_ids)} unique players')
lines.append(f'Unresolved draft names: {len(unresolved)}')
if unresolved:
    for n in unresolved: lines.append('  UNRESOLVED '+n)
lines.append(f'Player-season Sleeper GP vs official-game discrepancies: {len(season_diffs)}')
lines.append(f'Official appearances lacking a matched Sleeper scoring row: {len(scoring_missing)}')
lines.append(f'Career draft events whose games/PPG change: {len(career_changes)}')
lines.append('')
lines.append('SEASON-LEVEL GP DIFFERENCES')
for dy,name,season,sgp,ogp,pts,srow in sorted(season_diffs):
    raw=f"raw gp={srow['gp_raw']!r}, active={srow['active_raw']!r}" if srow else 'no Sleeper row'
    lines.append(f'{dy} pick | {name} | {season}: Sleeper denominator={sgp} ({raw}) -> official games={ogp}; Plebs points={pts:.2f}')
lines.append('')
lines.append('CAREER CHANGES')
for key,old,new in career_changes:
    if old and new:
        lines.append(f"{key}: games {old.get('games')} -> {new['games']}; PPG {float(old.get('ppg',0)):.3f} -> {new['ppg']:.3f}; points {float(old.get('points',0)):.2f} -> {new['points']:.2f}")
    elif new:
        lines.append(f"{key}: NEW official outcome games={new['games']} PPG={new['ppg']:.3f} points={new['points']:.2f}")
    else:
        lines.append(f"{key}: current outcome should be removed (no official regular-season appearances)")
lines.append('')
lines.append('OFFICIAL GAMES WITH NO MATCHED SLEEPER SCORING ROW')
for x in scoring_missing: lines.append(f'{x[0]} pick | {x[1]} | {x[2]}: official games={x[3]}, Sleeper points assumed 0 pending manual check')
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines))
