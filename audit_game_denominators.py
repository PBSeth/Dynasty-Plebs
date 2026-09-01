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

def fetch_bytes(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (Dynasty-Plebs denominator audit)','Accept':'*/*'})
    with urllib.request.urlopen(req,timeout=90) as r: return r.read()

def fetch_json(url):
    return json.loads(fetch_bytes(url).decode('utf-8'))

html=INDEX.read_text(encoding='utf-8')
m=re.search(r'const rookieBoards=(\{.*?\});\nconst nf=',html,re.S)
if not m: raise RuntimeError('rookieBoards not found')
boards=json.loads(m.group(1))

entries=[]
for ys,b in boards.items():
    y=int(ys)
    for rnd in b.get('rounds',[]):
        for p in rnd:
            if p: entries.append((y,p))
entries.append((2025,"Don'te Thornton"))
entry_names={norm_name(p) for _,p in entries}

# Sleeper season totals: scoring source. Keep its raw GP for comparison only.
sleeper={}
for season in range(2019,LAST_COMPLETE_SEASON+1):
    records=fetch_json(f'https://api.sleeper.com/stats/nfl/{season}?season_type=regular')
    lookup={}
    for rec in records:
        name=player_name(rec); pos=player_position(rec)
        if not name or pos not in OFFENSIVE_POSITIONS: continue
        s=rec.get('stats') or {}
        row={'name':name,'pos':pos,'gp':int(as_num(s.get('gp') or s.get('gms_active'))),'gp_raw':s.get('gp'),'active_raw':s.get('gms_active'),'points':plebs_points(rec)}
        n=norm_name(name); prev=lookup.get(n)
        if prev is None or (row['gp'],abs(row['points']))>(prev['gp'],abs(prev['points'])): lookup[n]=row
    sleeper[season]=lookup

# nflverse/PFR snap counts: independent appearance source. Count a regular-season game
# only when the player actually logged an offensive, defensive, or special-teams snap.
snaps={}
for season in range(2019,LAST_COMPLETE_SEASON+1):
    url=f'https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_{season}.csv'
    text=fetch_bytes(url).decode('utf-8-sig',errors='replace')
    reader=csv.DictReader(io.StringIO(text))
    games_by_name={}
    rows_seen=0
    for row in reader:
        gt=(row.get('game_type') or row.get('season_type') or '').upper()
        if gt and gt not in ('REG','R'): continue
        name=row.get('player') or row.get('player_name') or row.get('player_display_name') or ''
        if not name: continue
        n=norm_name(name)
        # Restrict storage to plausible draft-player matches/suffix variants to keep diagnostics clean.
        base=without_suffix(n)
        if n not in entry_names and base not in {without_suffix(x) for x in entry_names}: continue
        snap_total=sum(as_num(row.get(k)) for k in ('offense_snaps','defense_snaps','st_snaps'))
        if snap_total <= 0: continue
        game=row.get('game_id') or row.get('pfr_game_id') or f"{row.get('week','?')}|{row.get('team','?')}|{row.get('opponent','?')}"
        games_by_name.setdefault(n,set()).add(game)
        rows_seen += 1
    snaps[season]={n:len(gs) for n,gs in games_by_name.items()}
    print(f'nflverse snaps {season}: {len(games_by_name)} matched draft-player names / {rows_seen} appearance rows')

# Compare every drafted player's season-level Sleeper GP to independent snap appearances.
discrepancies=[]
unmatched_snap=[]
for draft_year,name in entries:
    for season in range(max(draft_year,2019),LAST_COMPLETE_SEASON+1):
        skey=resolve_key(name,sleeper[season])
        if not skey: continue
        srow=sleeper[season][skey]
        snap_lookup=snaps[season]
        n=norm_name(name)
        candidates=[n,ALIASES.get(n),without_suffix(n)]
        if ALIASES.get(n): candidates.append(without_suffix(ALIASES[n]))
        snap_key=next((c for c in candidates if c and c in snap_lookup),None)
        if snap_key is None:
            base=without_suffix(n); matches=[k for k in snap_lookup if without_suffix(k)==base]
            snap_key=matches[0] if len(matches)==1 else None
        snap_gp=snap_lookup.get(snap_key) if snap_key else None
        if snap_gp is None:
            # If Sleeper claims games but snap source has no matching player row, flag for manual review.
            if srow['gp']>0: unmatched_snap.append((draft_year,name,season,srow))
            continue
        if srow['gp'] != snap_gp:
            discrepancies.append((draft_year,name,season,srow,snap_gp))

# Roll discrepancies into career totals so we can see manager-facing PPG impact.
career_impacts=[]
for draft_year,name in entries:
    old_pts=0.0; old_games=0; snap_games_total=0; found_snap_seasons=0; relevant=[]
    for season in range(max(draft_year,2019),LAST_COMPLETE_SEASON+1):
        skey=resolve_key(name,sleeper[season])
        if not skey: continue
        srow=sleeper[season][skey]
        if srow['gp']>0:
            old_pts += srow['points']; old_games += srow['gp']
        hit=next((d for d in discrepancies if d[0]==draft_year and d[1]==name and d[2]==season),None)
        if hit:
            snap_games_total += hit[4]; found_snap_seasons += 1; relevant.append(hit)
        else:
            # if no discrepancy and Sleeper row exists, treat equal GP as verified
            snap_games_total += srow['gp']; found_snap_seasons += 1
    if relevant and old_games>0 and snap_games_total>0:
        career_impacts.append((draft_year,name,old_pts,old_games,snap_games_total,relevant))

lines=[]
lines.append('Dynasty Plebs rookie career PPG denominator audit')
lines.append('Scoring source: Sleeper raw stat totals. Appearance cross-check: nflverse/PFR snap counts.')
lines.append('Game rule audited: denominator = regular-season games actually appeared in; zero-game seasons contribute 0 games.')
lines.append(f'Sleeper-vs-snap player-season GP discrepancies: {len(discrepancies)}')
lines.append(f'Sleeper rows with GP>0 but no matched snap row (manual review): {len(unmatched_snap)}')
lines.append('')
lines.append('CONFIRMED GP DISCREPANCIES')
for draft_year,name,season,srow,snap_gp in sorted(discrepancies):
    lines.append(f"{draft_year} pick | {name} | {season}: Sleeper GP={srow['gp']} (raw gp={srow['gp_raw']!r}, active={srow['active_raw']!r}) vs snap GP={snap_gp}; Plebs points={srow['points']:.2f}")
lines.append('')
lines.append('CAREER PPG IMPACT FOR AFFECTED DRAFT EVENTS')
for draft_year,name,pts,old_gp,new_gp,relevant in sorted(career_impacts):
    lines.append(f'{draft_year} | {name}: games {old_gp} -> {new_gp}; PPG {pts/old_gp:.3f} -> {pts/new_gp:.3f}; points {pts:.2f}')
lines.append('')
lines.append('MANUAL-REVIEW ROWS (Sleeper GP>0, no snap match)')
for draft_year,name,season,srow in sorted(unmatched_snap):
    lines.append(f"{draft_year} pick | {name} | {season}: Sleeper GP={srow['gp']} raw gp={srow['gp_raw']!r} active={srow['active_raw']!r}; points={srow['points']:.2f}")
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines))
