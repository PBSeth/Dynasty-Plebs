import csv, io, json, re, unicodedata, urllib.request
from pathlib import Path

INDEX=Path('index.html'); OUT=Path('game_denominator_audit_v6.txt'); YEARS=range(2019,2026); POS={'QB','RB','WR','TE'}
ALIASES={'kenwalkeriii':'kennethwalkeriii','nathanieldell':'tankdell','deriusdavis':'dariusdavis','jaelondarden':'jaleondarden','terracemarshall':'terracemarshalljr','brianrobinson':'brianrobinsonjr','zachmoss':'zackmoss','gabrieldavis':'gabedavis','kennethgainwell':'kennygainwell','dwayneeskridge':'deeeskridge','joshpalmer':'joshuapalmer','travisetienne':'travisetiennejr','marvinmimsjr':'marvinmims','michaelwilson':'michaelwilsonjr','chrisrodriguezjr':'chrisrodriguez','joshdowns':'joshuadowns'}

def norm(v):
 s=unicodedata.normalize('NFD',str(v or '').lower()); s=''.join(c for c in s if unicodedata.category(c)!='Mn'); return re.sub(r'[^a-z0-9]','',s)
def no_suffix(s):
 for x in ('junior','senior','jr','sr','iii','ii','iv','v'):
  if s.endswith(x) and len(s)>len(x)+3:return s[:-len(x)]
 return s
def num(v):
 try:return float(v or 0)
 except:return 0.0
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 Dynasty-Plebs-audit','Accept':'*/*'})
 with urllib.request.urlopen(req,timeout=180) as r:return r.read()
def csv_rows(url):return list(csv.DictReader(io.StringIO(get(url).decode('utf-8-sig',errors='replace'))))
def sname(r):
 p=r.get('player') or {}; return (p.get('full_name') or ' '.join(x for x in (p.get('first_name'),p.get('last_name')) if x) or r.get('player_name') or '').strip()
def spos(r):
 p=r.get('player') or {}; return p.get('position') or r.get('position') or ''
def pts(r):
 s=r.get('stats') or {}; return num(s.get('pass_yd'))*.04+num(s.get('pass_td'))*6-num(s.get('pass_int'))*4+num(s.get('pass_2pt'))*2+num(s.get('rush_yd'))*.1+num(s.get('rush_td'))*6+num(s.get('rush_2pt'))*2+num(s.get('rec'))*.5+num(s.get('rec_yd'))*.1+num(s.get('rec_td'))*6+num(s.get('rec_2pt'))*2-num(s.get('fum_lost'))*2+num(s.get('fum_rec_td'))*6+(num(s.get('st_td')) if num(s.get('st_td')) else num(s.get('kick_ret_td'))+num(s.get('punt_ret_td')))*6
def resolve_key(name,lookup):
 n=norm(name); cs=[n,ALIASES.get(n),no_suffix(n)];
 if ALIASES.get(n):cs.append(no_suffix(ALIASES[n]))
 for c in cs:
  if c and c in lookup:return c
 base=no_suffix(n); ms=[k for k in lookup if no_suffix(k)==base]; return ms[0] if len(ms)==1 else None

html=INDEX.read_text(encoding='utf-8'); bm=re.search(r'const rookieBoards=(\{.*?\});\nconst nf=',html,re.S); cm=re.search(r'const careerDraftStats=(\{.*?\});\nconst rookieBoards=',html,re.S)
boards=json.loads(bm.group(1)); current=json.loads(cm.group(1)); entries=[]
for ys,b in boards.items():
 y=int(ys)
 if y>2025:continue
 for rd in b.get('rounds',[]):
  for p in rd:
   if p:entries.append((y,p))
entries.append((2025,"Don'te Thornton"))

# Name -> nflverse player row -> PFR id where available.
players=csv_rows('https://github.com/nflverse/nflverse-data/releases/download/players/players.csv'); labels={}
for r in players:
 pos=(r.get('position') or '').strip()
 if pos and pos not in POS:continue
 vals=[r.get(k) for k in ('display_name','football_name','short_name') if r.get(k)]; f=(r.get('common_first_name') or r.get('first_name') or '').strip(); l=(r.get('last_name') or '').strip()
 if f and l:vals.append(f+' '+l)
 for v in vals:labels.setdefault(norm(v),[]).append(r)
def prow(name):
 n=norm(name); cs=[n,ALIASES.get(n),no_suffix(n)];
 if ALIASES.get(n):cs.append(no_suffix(ALIASES[n]))
 rows=[]
 for c in cs:
  if c:rows+=labels.get(c,[])
 uniq={((r.get('gsis_id') or ''),(r.get('pfr_id') or ''),(r.get('display_name') or '')):r for r in rows}
 if len(uniq)==1:return next(iter(uniq.values()))
 return None
identity={n:prow(n) for _,n in entries}

# PFR game-level snap counts. No name fallback: only stable PFR IDs are trusted for overrides.
snaps={}
for y in YEARS:
 by={}
 for r in csv_rows(f'https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_{y}.csv'):
  if (r.get('game_type') or '').upper()!='REG':continue
  pid=(r.get('pfr_player_id') or '').strip(); gid=(r.get('game_id') or r.get('pfr_game_id') or f"{y}|{r.get('week')}|{r.get('team')}").strip()
  if pid:by.setdefault(pid,set()).add(gid)
 snaps[y]={k:len(v) for k,v in by.items()}

# Sleeper season rows: fantasy points and raw gp. gms_active is diagnostic only and is NEVER a denominator fallback.
sleeper={}
for y in YEARS:
 lookup={}
 for r in json.loads(get(f'https://api.sleeper.com/stats/nfl/{y}?season_type=regular').decode()):
  name=sname(r); pos=spos(r)
  if not name or pos not in POS:continue
  s=r.get('stats') or {}; raw=s.get('gp'); active=s.get('gms_active'); row={'points':pts(r),'raw_gp':None if raw is None else int(num(raw)),'active':None if active is None else int(num(active)),'pos':pos}
  k=norm(name); old=lookup.get(k)
  rank=(row['raw_gp'] if row['raw_gp'] is not None else -1,abs(row['points']))
  oldrank=((old['raw_gp'] if old and old['raw_gp'] is not None else -1),abs(old['points'])) if old else (-2,-1)
  if old is None or rank>oldrank:lookup[k]=row
 sleeper[y]=lookup

# Proposed denominator: trusted PFR snap-game count when PFR id resolves; otherwise Sleeper raw gp; otherwise zero.
def game_count(name,y,sr):
 r=identity.get(name); pid=(r.get('pfr_id') or '').strip() if r else ''
 if pid and pid in snaps[y]:return snaps[y][pid],'PFR'
 if sr and sr['raw_gp'] is not None:return sr['raw_gp'],'Sleeper raw gp'
 return 0,'zero (no gp / no PFR appearance)'

rebuilt={}; season_changes=[]; pfr_vs_raw=[]; phantom=[]
for dy,name in entries:
 totalp=0.0; totalg=0; seasons=0; through=None; pos=''
 for y in range(max(dy,2019),2026):
  sk=resolve_key(name,sleeper[y]); sr=sleeper[y].get(sk) if sk else None; p=sr['points'] if sr else 0.0; old=(sr['raw_gp'] if sr and sr['raw_gp'] is not None else (sr['active'] if sr and sr['active'] is not None else 0))
  g,source=game_count(name,y,sr)
  if sr:pos=pos or sr['pos']
  if old!=g:season_changes.append((dy,name,y,old,g,p,sr,source))
  if source=='PFR' and sr and sr['raw_gp'] is not None and sr['raw_gp']!=g:pfr_vs_raw.append((dy,name,y,sr['raw_gp'],g))
  if sr and sr['raw_gp'] is None and sr['active'] and g==0:phantom.append((dy,name,y,sr['active']))
  if g>0:totalg+=g; totalp+=p; seasons+=1; through=y
 key=f'{dy}|{norm(name)}'
 if totalg>0:rebuilt[key]={'ppg':totalp/totalg,'points':totalp,'games':totalg,'seasons':seasons,'through':through,'pos':pos}

changes=[]
for key in sorted({f'{dy}|{norm(n)}' for dy,n in entries}):
 old=current.get(key); new=rebuilt.get(key)
 if old and old.get('excluded')=='veteran':continue
 if old and new:
  if old.get('games')!=new['games'] or abs(float(old.get('ppg',0))-new['ppg'])>.0005:changes.append((key,old,new))
 elif old or new:changes.append((key,old,new))

checks=[]
for n,y,e in [('Travis Etienne',2021,0),('Travis Etienne',2022,17),('Travis Etienne',2023,17),('Travis Etienne',2024,15),('Travis Etienne',2025,17),('Joe Burrow',2022,16),("Ja'Marr Chase",2022,12),('Cam Akers',2020,13)]:
 sk=resolve_key(n,sleeper[y]); sr=sleeper[y].get(sk) if sk else None; g,src=game_count(n,y,sr); checks.append((n,y,g,e,src,g==e))

lines=['Dynasty Plebs denominator audit v6 — safe hybrid',
 'Primary appearance source: nflverse/PFR game-level snap counts by stable PFR player ID.',
 'Fallback only when no trusted PFR match: Sleeper raw gp. gms_active is never used as games played.',
 'This removes active/inactive/IR phantom games while preserving real zero-point appearances.',
 f'Completed draft entries audited: {len(entries)} | season denominator changes vs current logic: {len(season_changes)} | career draft-event changes: {len(changes)}',
 f'PFR corrections where Sleeper raw gp itself differs: {len(pfr_vs_raw)} | phantom gms_active-only seasons removed: {len(phantom)}','', 'SANITY CHECKS']
for n,y,g,e,src,ok in checks:lines.append(f'{n} {y}: {g} via {src}; expected {e} => '+('PASS' if ok else 'FAIL'))
lines+=['','PHANTOM GMS_ACTIVE-ONLY SEASONS REMOVED']
for x in sorted(phantom):lines.append(f'{x[0]} pick | {x[1]} | {x[2]}: gms_active={x[3]} -> games=0')
lines+=['','PFR VS SLEEPER RAW-GP CORRECTIONS']
for x in sorted(pfr_vs_raw):lines.append(f'{x[0]} pick | {x[1]} | {x[2]}: raw gp {x[3]} -> PFR {x[4]}')
lines+=['','CAREER CHANGES']
for key,old,new in changes:
 if old and new:lines.append(f"{key}: games {old.get('games')} -> {new['games']}; PPG {float(old.get('ppg',0)):.3f} -> {new['ppg']:.3f}; points {float(old.get('points',0)):.2f} -> {new['points']:.2f}")
 elif new:lines.append(f"{key}: NEW games {new['games']}; PPG {new['ppg']:.3f}; points {new['points']:.2f}")
 else:lines.append(f'{key}: remove scored outcome; no games')
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8'); print('\n'.join(lines))
