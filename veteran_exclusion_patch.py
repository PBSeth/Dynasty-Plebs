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

def without_suffix(value):
    for suffix in ('junior','senior','jr','sr','iii','ii','iv','v'):
        if value.endswith(suffix) and len(value)>len(suffix)+3:
            return value[:-len(suffix)]
    return value

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

def resolve_key(target,lookup):
    n=norm_name(target)
    candidates=[n,ALIASES.get(n),without_suffix(n)]
    alias=ALIASES.get(n)
    if alias:candidates.append(without_suffix(alias))
    for c in candidates:
        if c and c in lookup:return c
    base=without_suffix(n)
    matches=[k for k in lookup if without_suffix(k)==base]
    return matches[0] if len(matches)==1 else None

html=INDEX.read_text(encoding='utf-8')
boards_m=re.search(r'const rookieBoards=(\{.*?\});\nconst nf=',html,re.S)
stats_m=re.search(r'const careerDraftStats=(\{.*?\});\nconst rookieBoards=',html,re.S)
if not boards_m or not stats_m:
    raise SystemExit('rookieBoards/careerDraftStats not found')
boards=json.loads(boards_m.group(1))
career=json.loads(stats_m.group(1))

entries=[]
for year_text,board in boards.items():
    year=int(year_text)
    for round_players in board.get('rounds',[]):
        for player in round_players:
            if player:entries.append((year,player))

# Independent veteran audit: a player is a veteran selection if he recorded an NFL
# regular-season game before the Dynasty Plebs draft year. This keeps veteran names
# in the draft archive while removing them from every rookie-draft PPG/grade metric.
lookups={}
for season in range(HISTORY_START,LAST_COMPLETE_SEASON+1):
    rows=fetch_json(f'https://api.sleeper.com/stats/nfl/{season}?season_type=regular')
    lookup={}
    for rec in rows:
        name=player_name(rec); pos=player_position(rec)
        if not name or pos not in OFFENSIVE_POSITIONS:continue
        gp=int(as_num((rec.get('stats') or {}).get('gp') or (rec.get('stats') or {}).get('gms_active')))
        if gp<=0:continue
        n=norm_name(name)
        old=lookup.get(n)
        if old is None or gp>old['gp']:
            lookup[n]={'name':name,'pos':pos,'gp':gp}
    lookups[season]=lookup
    time.sleep(.08)

veterans={}
for draft_year,player in entries:
    first=None; pos=''
    for season in range(HISTORY_START,min(draft_year,LAST_COMPLETE_SEASON+1)):
        key=resolve_key(player,lookups.get(season,{}))
        if key:
            first=season; pos=lookups[season][key]['pos']; break
    if first is not None and first<draft_year:
        veterans[(draft_year,norm_name(player))]={'player':player,'first':first,'pos':pos}

missing_expected=EXPECTED_VETERANS-set(veterans)
if missing_expected:
    raise RuntimeError('Expected veteran selections were not detected: '+', '.join(f'{y} {n}' for y,n in sorted(missing_expected)))

for (year,n),meta in veterans.items():
    career[f'{year}|{n}']={'excluded':'veteran','firstNflSeason':meta['first'],'pos':meta['pos']}

career_json=json.dumps(career,separators=(',',':'),ensure_ascii=False)
html=html[:stats_m.start(1)]+career_json+html[stats_m.end(1):]

start=html.find('function addPick(manager,year,round,slot,player)')
end=html.find('Object.entries(rookieBoards)',start)
if start<0 or end<0:raise RuntimeError('addPick block not found')
new_add="function addPick(manager,year,round,slot,player){const stat=careerDraftStats[`${year}|${normName(player)}`];(rookiePicks[manager]??=[]).push({year,pick:`${round}.${String(slot).padStart(2,'0')}`,player,...(stat||{})})}\n"
html=html[:start]+new_add+html[end:]

old_badge="${Number.isFinite(p.ppg)?`<span class=\"ppg-badge\">Career ${p.ppg.toFixed(1)} PPG</span>`:''}"
new_badge="${p.excluded==='veteran'?`<span class=\"ppg-badge\">Veteran · excluded</span>`:Number.isFinite(p.ppg)?`<span class=\"ppg-badge\">Career ${p.ppg.toFixed(1)} PPG</span>`:''}"
if old_badge not in html:
    raise RuntimeError('rookie card PPG badge pattern not found')
html=html.replace(old_badge,new_badge,1)

html=html.replace(
    'Complete recovered rookie-draft history with career-to-date Dynasty Plebs scoring.',
    'Complete recovered rookie-draft history with career-to-date Dynasty Plebs scoring. Veteran selections stay in the archive but are excluded from rookie-draft grading.',
    1,
)

INDEX.write_text(html,encoding='utf-8')
print(f'Veteran selections excluded from rookie-draft scoring: {len(veterans)}')
for (year,_),meta in sorted(veterans.items()):
    print(f"VETERAN {year}: {meta['player']} (NFL since {meta['first']})")
