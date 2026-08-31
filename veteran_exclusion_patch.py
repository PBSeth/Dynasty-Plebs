import json
import re
import time
import unicodedata
import urllib.request
from pathlib import Path

INDEX = Path('index.html')
HISTORY_START = 2013
LAST_COMPLETE_SEASON = 2025
OFFENSIVE_POSITIONS = {'QB','RB','WR','TE'}

ALIASES = {
    'kenwalkeriii':'kennethwalkeriii',
    'nathanieldell':'tankdell',
    'deriusdavis':'dariusdavis',
    'jaelondarden':'jaleondarden',
    'terracemarshall':'terracemarshalljr',
    'brianrobinson':'brianrobinsonjr',
    'zachmoss':'zackmoss',
    'gabrieldavis':'gabedavis',
    'kennethgainwell':'kennygainwell',
    'dwayneeskridge':'deeeskridge',
    'joshpalmer':'joshuapalmer',
    'jamarithrash':'jamarithrash',
    'jamarthrash':'jamarithrash',
    'jamatthrash':'jamarithrash',
}

# Known veterans intentionally selected in the league's rookie drafts. These stay
# visible in draft history but must never contribute to rookie-pick PPG or grades.
EXPECTED_VETERANS = {
    (2024,'keenanallen'),
    (2024,'clydeedwardshelaire'),
    (2024,'kennethgainwell'),
    (2024,'vanjefferson'),
    (2024,'colbyparkinson'),
    (2024,'samdarnold'),
    (2025,'khalilherbert'),
    (2026,'jauanjennings'),
    (2026,'jalennailor'),
}

def norm_name(value):
    s=unicodedata.normalize('NFD',str(value or '').lower())
    s=''.join(ch for ch in s if unicodedata.category(ch)!='Mn')
    return re.sub(r'[^a-z0-9]','',s)

def fetch_json(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (Dynasty-Plebs veteran draft audit)','Accept':'application/json,text/plain,*/*'})
    with urllib.request.urlopen(req,timeout=45) as response:
        return json.load(response)

def as_num(value):
    try:return float(value or 0)
    except (TypeError,ValueError):return 0.0

def player_name(record):
    p=record.get('player') or {}
    return (p.get('full_name') or ' '.join(x for x in (p.get('first_name'),p.get('last_name')) if x) or record.get('player_name') or '').strip()

def player_position(record):
    p=record.get('player') or {}
    return p.get('position') or record.get('position') or ''

def player_id(record):
    p=record.get('player') or {}
    value=record.get('player_id') or p.get('player_id') or p.get('id')
    return str(value) if value is not None else ''

def candidate_norms(name):
    n=norm_name(name)
    vals=[n]
    if ALIASES.get(n): vals.append(ALIASES[n])
    return vals

html=INDEX.read_text(encoding='utf-8')
boards_m=re.search(r'const rookieBoards=(\{.*?\});\nconst nf=',html,re.S)
stats_m=re.search(r'const careerDraftStats=(\{.*?\});\nconst rookieBoards=',html,re.S)
if not boards_m or not stats_m:
    raise SystemExit('rookieBoards/careerDraftStats not found')
boards=json.loads(boards_m.group(1))
career=json.loads(stats_m.group(1))

# Permanent ownership regression anchors from the workbook. The user's 2022 note is
# especially useful: Dave owned exactly six Round 2 picks (1, 4, 6, 8, 9, 12).
r2_2022=boards['2022']['ownersByRound'][1]
assert [i+1 for i,o in enumerate(r2_2022) if o=='David Carnes']==[1,4,6,8,9,12]
assert boards['2023']['ownersByRound'][0][0]=='Travis Page'      # Bijan Robinson
assert boards['2023']['ownersByRound'][5][1]=='Travis Page'      # Puka Nacua
assert boards['2025']['ownersByRound'][2][6]=='Bo Tiller'        # Jaxson Dart
assert boards['2024']['ownersByRound'][4][9]=='Travis Page'      # Kenneth Gainwell

entries=[]
for year_text,board in boards.items():
    year=int(year_text)
    for round_players in board.get('rounds',[]):
        for player in round_players:
            if player: entries.append((year,player))

# Build identity-aware Sleeper history. Name-only history can collide across eras
# (Frank Gore vs Frank Gore Jr, multiple Kyle/Antonio Williams), so veteran status is
# determined by the SAME Sleeper player id having a regular-season game before the
# Plebs draft year.
by_season_name={}
id_first={}
id_pos={}
for season in range(HISTORY_START,LAST_COMPLETE_SEASON+1):
    rows=fetch_json(f'https://api.sleeper.com/stats/nfl/{season}?season_type=regular')
    name_map={}
    for rec in rows:
        name=player_name(rec); pos=player_position(rec); pid=player_id(rec)
        if not name or pos not in OFFENSIVE_POSITIONS or not pid: continue
        stats=rec.get('stats') or {}
        gp=int(as_num(stats.get('gp') or stats.get('gms_active')))
        if gp<=0: continue
        n=norm_name(name)
        row={'name':name,'pos':pos,'gp':gp,'id':pid}
        name_map.setdefault(n,[]).append(row)
        if pid not in id_first or season<id_first[pid]: id_first[pid]=season
        id_pos[pid]=pos
    by_season_name[season]=name_map
    time.sleep(.08)

def find_identity(draft_year,name):
    norms=candidate_norms(name)
    # First identify the intended player at/after the Plebs draft year. For a future
    # draft (2026), only a player still recording 2025 NFL games can be a veteran.
    start=min(draft_year,LAST_COMPLETE_SEASON)
    seasons=range(start,LAST_COMPLETE_SEASON+1)
    for season in seasons:
        candidates=[]
        for n in norms:
            candidates.extend(by_season_name.get(season,{}).get(n,[]))
        if candidates:
            candidates.sort(key=lambda r:(r['gp'],r['name']==name),reverse=True)
            return candidates[0]
    return None

veterans={}
for draft_year,player in entries:
    identity=find_identity(draft_year,player)
    if not identity: continue
    first=id_first.get(identity['id'])
    if first is not None and first<draft_year:
        veterans[(draft_year,norm_name(player))]={'player':player,'first':first,'pos':identity['pos'],'id':identity['id']}

found=set(veterans)
missing=EXPECTED_VETERANS-found
unexpected=found-EXPECTED_VETERANS
if missing or unexpected:
    details=[]
    if missing: details.append('missing expected: '+', '.join(f'{y} {n}' for y,n in sorted(missing)))
    if unexpected: details.append('unexpected: '+', '.join(f'{y} {n}' for y,n in sorted(unexpected)))
    raise RuntimeError('Veteran audit mismatch — '+'; '.join(details))

for (year,n),meta in veterans.items():
    career[f'{year}|{n}']={'excluded':'veteran','firstNflSeason':meta['first'],'pos':meta['pos']}

career_json=json.dumps(career,separators=(',',':'),ensure_ascii=False)
html=html[:stats_m.start(1)]+career_json+html[stats_m.end(1):]

start=html.find('function addPick(manager,year,round,slot,player)')
end=html.find('Object.entries(rookieBoards)',start)
if start<0 or end<0: raise RuntimeError('addPick block not found')
new_add="function addPick(manager,year,round,slot,player){const stat=careerDraftStats[`${year}|${normName(player)}`];(rookiePicks[manager]??=[]).push({year,pick:`${round}.${String(slot).padStart(2,'0')}`,player,...(stat||{})})}\n"
html=html[:start]+new_add+html[end:]

old_badge="${Number.isFinite(p.ppg)?`<span class=\"ppg-badge\">Career ${p.ppg.toFixed(1)} PPG</span>`:''}"
new_badge="${p.excluded==='veteran'?`<span class=\"ppg-badge\">Veteran · excluded</span>`:Number.isFinite(p.ppg)?`<span class=\"ppg-badge\">Career ${p.ppg.toFixed(1)} PPG</span>`:''}"
if old_badge in html:
    html=html.replace(old_badge,new_badge,1)
elif 'Veteran · excluded' not in html:
    raise RuntimeError('rookie card PPG badge pattern not found')

base_desc='Complete recovered rookie-draft history with career-to-date Dynasty Plebs scoring.'
veteran_note='Veteran selections stay in the archive but are excluded from rookie-draft grading.'
html,n=re.subn(re.escape(base_desc)+r'(?: '+re.escape(veteran_note)+r')*',base_desc+' '+veteran_note,html,count=1)
if n!=1: raise RuntimeError('Rookie draft description not found')

INDEX.write_text(html,encoding='utf-8')
print(f'Veteran selections excluded from rookie-draft scoring: {len(veterans)}')
for (year,_),meta in sorted(veterans.items()):
    print(f"VETERAN {year}: {meta['player']} (NFL since {meta['first']})")
print('Ownership anchors passed, including Dave = six 2022 Round 2 picks.')
