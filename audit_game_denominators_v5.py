import csv, io, json, re, unicodedata, urllib.request
from pathlib import Path

INDEX=Path('index.html'); OUT=Path('game_denominator_audit_v5.txt')
YEARS=range(2019,2026); POS={'QB','RB','WR','TE'}
ALIASES={
 'kenwalkeriii':'kennethwalkeriii','nathanieldell':'tankdell','deriusdavis':'dariusdavis',
 'jaelondarden':'jaleondarden','terracemarshall':'terracemarshalljr','brianrobinson':'brianrobinsonjr',
 'zachmoss':'zackmoss','gabrieldavis':'gabedavis','kennethgainwell':'kennygainwell',
 'dwayneeskridge':'deeeskridge','joshpalmer':'joshuapalmer','travisetienne':'travisetiennejr',
 'marvinmimsjr':'marvinmims','michaelwilson':'michaelwilsonjr','chrisrodriguezjr':'chrisrodriguez',
 'joshdowns':'joshuadowns','dontethornton':'dontaythorntonjr','dontevianwicks':'dontayvionwicks',
}

def norm(v):
 s=unicodedata.normalize('NFD',str(v or '').lower()); s=''.join(c for c in s if unicodedata.category(c)!='Mn')
 return re.sub(r'[^a-z0-9]','',s)

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
def sleeper_name(r):
 p=r.get('player') or {}; return (p.get('full_name') or ' '.join(x for x in (p.get('first_name'),p.get('last_name')) if x) or r.get('player_name') or '').strip()
def sleeper_pos(r):
 p=r.get('player') or {}; return p.get('position') or r.get('position') or ''
def plebs(r):
 s=r.get('stats') or {}
 return (num(s.get('pass_yd'))*.04+num(s.get('pass_td'))*6-num(s.get('pass_int'))*4+num(s.get('pass_2pt'))*2+
  num(s.get('rush_yd'))*.1+num(s.get('rush_td'))*6+num(s.get('rush_2pt'))*2+num(s.get('rec'))*.5+
  num(s.get('rec_yd'))*.1+num(s.get('rec_td'))*6+num(s.get('rec_2pt'))*2-num(s.get('fum_lost'))*2+
  num(s.get('fum_rec_td'))*6+(num(s.get('st_td')) if num(s.get('st_td')) else num(s.get('kick_ret_td'))+num(s.get('punt_ret_td')))*6)

def resolve_key(name,lookup):
 n=norm(name); cs=[n,ALIASES.get(n),no_suffix(n)]
 if ALIASES.get(n):cs.append(no_suffix(ALIASES[n]))
 for c in cs:
  if c and c in lookup:return c
 base=no_suffix(n); ms=[k for k in lookup if no_suffix(k)==base]
 return ms[0] if len(ms)==1 else None

html=INDEX.read_text(encoding='utf-8')
bm=re.search(r'const rookieBoards=(\{.*?\});\nconst nf=',html,re.S); cm=re.search(r'const careerDraftStats=(\{.*?\});\nconst rookieBoards=',html,re.S)
if not bm or not cm:raise RuntimeError('index constants missing')
boards=json.loads(bm.group(1)); current=json.loads(cm.group(1))
entries=[]
for ys,b in boards.items():
 y=int(ys)
 if y>2025:continue
 for rd in b.get('rounds',[]):
  for p in rd:
   if p:entries.append((y,p))
entries.append((2025,"Don'te Thornton"))

# Resolve league draft names to stable PFR IDs from nflverse players.csv.
players=csv_rows('https://github.com/nflverse/nflverse-data/releases/download/players/players.csv')
name_rows={}
for r in players:
 pos=(r.get('position') or '').strip()
 if pos and pos not in POS:continue
 vals=[]
 for k in ('display_name','football_name','short_name'):
  if r.get(k):vals.append(r[k])
 f=(r.get('common_first_name') or r.get('first_name') or '').strip(); l=(r.get('last_name') or '').strip()
 if f and l:vals.append(f+' '+l)
 for v in vals:name_rows.setdefault(norm(v),[]).append(r)

def player_row(name):
 n=norm(name); candidates=[n,ALIASES.get(n),no_suffix(n)]
 if ALIASES.get(n):candidates.append(no_suffix(ALIASES[n]))
 rows=[]
 for c in candidates:
  if c:rows.extend(name_rows.get(c,[]))
 # dedupe by gsis/pfr identity
 uniq={((r.get('gsis_id') or ''),(r.get('pfr_id') or ''),(r.get('display_name') or '')):r for r in rows}
 if len(uniq)==1:return next(iter(uniq.values()))
 base=no_suffix(n); rows=[]
 for k,rs in name_rows.items():
  if no_suffix(k)==base:rows.extend(rs)
 uniq={((r.get('gsis_id') or ''),(r.get('pfr_id') or ''),(r.get('display_name') or '')):r for r in rows}
 return next(iter(uniq.values())) if len(uniq)==1 else None

identity={name:player_row(name) for _,name in entries}

# PFR snap counts are game-level rows. A REG row means the player actually appeared in that game.
snap_games={}; snap_name_games={}
for y in YEARS:
 rows=csv_rows(f'https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_{y}.csv')
 by_id={}; by_name={}
 for r in rows:
  if (r.get('game_type') or '').upper()!='REG':continue
  gid=(r.get('game_id') or r.get('pfr_game_id') or f"{y}|{r.get('week')}|{r.get('team')}").strip()
  pid=(r.get('pfr_player_id') or '').strip(); name=norm(r.get('player'))
  if pid:by_id.setdefault(pid,set()).add(gid)
  if name:by_name.setdefault(name,set()).add(gid)
 snap_games[y]={k:len(v) for k,v in by_id.items()}; snap_name_games[y]={k:len(v) for k,v in by_name.items()}
 print('snap rows',y,len(rows),'players',len(by_id))

# Sleeper is scoring source only. Its gp/gms_active are retained for comparison diagnostics.
sleeper={}
for y in YEARS:
 rows=json.loads(get(f'https://api.sleeper.com/stats/nfl/{y}?season_type=regular').decode())
 lookup={}
 for r in rows:
  name=sleeper_name(r); pos=sleeper_pos(r)
  if not name or pos not in POS:continue
  s=r.get('stats') or {}; row={'points':plebs(r),'gp':int(num(s.get('gp') or s.get('gms_active'))),'rawgp':s.get('gp'),'active':s.get('gms_active'),'pos':pos}
  k=norm(name); old=lookup.get(k)
  if old is None or (row['gp'],abs(row['points']))>(old['gp'],abs(old['points'])):lookup[k]=row
 sleeper[y]=lookup

def official_gp(name,y):
 r=identity.get(name); pfr=(r.get('pfr_id') or '').strip() if r else ''
 if pfr and pfr in snap_games[y]:return snap_games[y][pfr],'pfr:'+pfr
 # fallback to normalized snap player name, useful for missing crosswalk IDs
 n=norm(name); cs=[n,ALIASES.get(n),no_suffix(n)]
 if ALIASES.get(n):cs.append(no_suffix(ALIASES[n]))
 for c in cs:
  if c and c in snap_name_games[y]:return snap_name_games[y][c],'name:'+c
 base=no_suffix(n); ms=[k for k in snap_name_games[y] if no_suffix(k)==base]
 if len(ms)==1:return snap_name_games[y][ms[0]],'name:'+ms[0]
 return 0,'none'

season_diffs=[]; rebuilt={}; unresolved_identity=[]
for dy,name in entries:
 r=identity.get(name)
 if not r:unresolved_identity.append(name)
 pts=0.0; gp=0; seasons=0; through=None; pos=''; any_official=False
 for y in range(max(dy,2019),2026):
  ogp,method=official_gp(name,y); any_official|=ogp>0
  sk=resolve_key(name,sleeper[y]); sr=sleeper[y].get(sk) if sk else None
  sgp=sr['gp'] if sr else 0; p=sr['points'] if sr else 0.0
  if sr:pos=pos or sr['pos']
  if sgp!=ogp:season_diffs.append((dy,name,y,sgp,ogp,p,sr,method))
  if ogp>0:
   gp+=ogp; pts+=p; seasons+=1; through=y
 key=f'{dy}|{norm(name)}'
 if gp>0:rebuilt[key]={'ppg':pts/gp,'points':pts,'games':gp,'seasons':seasons,'through':through,'pos':pos}

changes=[]
for key in sorted({f'{dy}|{norm(n)}' for dy,n in entries}):
 old=current.get(key); new=rebuilt.get(key)
 if old and old.get('excluded')=='veteran':continue
 if old and new:
  if old.get('games')!=new['games'] or abs(float(old.get('ppg',0))-new['ppg'])>.0005:changes.append((key,old,new))
 elif old or new:changes.append((key,old,new))

# High-value sanity checks independent of career math.
checks=[]
for name,year,expected in [('Travis Etienne',2021,0),('Travis Etienne',2022,17),('Travis Etienne',2023,17),('Travis Etienne',2024,15),('Travis Etienne',2025,17),('Joe Burrow',2022,16),("Ja'Marr Chase",2022,12)]:
 got,_=official_gp(name,year); checks.append((name,year,got,expected,got==expected))

lines=['Dynasty Plebs denominator audit — PFR game-level snap counts',
 'Points: Sleeper raw regular-season stats scored with Plebs rules.',
 'Games: nflverse/PFR snap_counts, REG only, unique game_id per PFR player id (name fallback only when needed).',
 'Rule: only actual regular-season appearances count; IR/inactive/practice-squad weeks and 0-game seasons do not.',
 f'Completed draft entries audited: {len(entries)} | unresolved players.csv identities: {len(set(unresolved_identity))}',
 f'Player-season denominator differences: {len(season_diffs)} | career draft-event changes: {len(changes)}','']
lines.append('SANITY CHECKS')
for n,y,g,e,ok in checks:lines.append(f'{n} {y}: {g} expected {e} => '+('PASS' if ok else 'FAIL'))
lines.append('')
if unresolved_identity:
 lines.append('UNRESOLVED PLAYERS.CSV IDENTITIES (snap-name fallback still attempted)'); lines += ['  '+x for x in sorted(set(unresolved_identity))]; lines.append('')
lines.append('SEASON DIFFERENCES')
for dy,n,y,sgp,ogp,p,sr,method in sorted(season_diffs):
 raw=f"raw gp={sr['rawgp']!r}, active={sr['active']!r}" if sr else 'no Sleeper row'
 lines.append(f'{dy} pick | {n} | {y}: Sleeper denom {sgp} ({raw}) -> PFR games {ogp} via {method}; Plebs pts {p:.2f}')
lines.append(''); lines.append('CAREER CHANGES')
for key,old,new in changes:
 if old and new:lines.append(f"{key}: games {old.get('games')} -> {new['games']}; PPG {float(old.get('ppg',0)):.3f} -> {new['ppg']:.3f}; points {float(old.get('points',0)):.2f} -> {new['points']:.2f}")
 elif new:lines.append(f"{key}: NEW games {new['games']}; PPG {new['ppg']:.3f}; points {new['points']:.2f}")
 else:lines.append(f'{key}: current outcome should be removed; 0 PFR regular-season appearances')
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8'); print('\n'.join(lines))
