import csv, gzip, io, json, re, unicodedata, urllib.request
from pathlib import Path

INDEX=Path('index.html'); OUT=Path('game_denominator_audit_v4.txt')
YEARS=range(2019,2026); POS={'QB','RB','WR','TE'}
ALIASES={
 'kenwalkeriii':'kennethwalkeriii','nathanieldell':'tankdell','deriusdavis':'dariusdavis',
 'jaelondarden':'jaleondarden','terracemarshall':'terracemarshalljr','brianrobinson':'brianrobinsonjr',
 'zachmoss':'zackmoss','gabrieldavis':'gabedavis','kennethgainwell':'kennygainwell',
 'dwayneeskridge':'deeeskridge','joshpalmer':'joshuapalmer','travisetienne':'travisetiennejr',
 'cjstroud':'cjstroudjr','marvinmimsjr':'marvinmims','michaelwilson':'michaelwilsonjr',
 'chrisrodriguezjr':'chrisrodriguez','joshdowns':'joshuadowns','tyjaespears':'tyjaespears',
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

def csv_rows(url,gz=False):
 raw=get(url); raw=gzip.decompress(raw) if gz else raw
 return list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig',errors='replace'))))

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

def resolve_name(name,lookup):
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
 for rd in b.get('rounds',[]):
  for p in rd:
   if p:entries.append((y,p))
entries.append((2025,"Don'te Thornton"))

# Stable identity map from nflverse players release.
players=csv_rows('https://github.com/nflverse/nflverse-data/releases/download/players/players.csv')
labels={}
for r in players:
 pid=(r.get('gsis_id') or '').strip(); pos=(r.get('position') or '').strip()
 if not pid or (pos and pos not in POS):continue
 vals=[]
 for k in ('display_name','football_name','short_name'):
  if r.get(k):vals.append(r[k])
 first=(r.get('common_first_name') or r.get('first_name') or '').strip(); last=(r.get('last_name') or '').strip()
 if first and last:vals.append(first+' '+last)
 for v in vals:labels.setdefault(norm(v),set()).add(pid)

def resolve_id(name):
 n=norm(name); ids=set(); cs=[n,ALIASES.get(n),no_suffix(n)]
 if ALIASES.get(n):cs.append(no_suffix(ALIASES[n]))
 for c in cs:
  if c:ids|=labels.get(c,set())
 if len(ids)==1:return next(iter(ids))
 base=no_suffix(n)
 for lab,vals in labels.items():
  if no_suffix(lab)==base:ids|=vals
 return next(iter(ids)) if len(ids)==1 else None

resolved={name:resolve_id(name) for _,name in entries}; ids={x for x in resolved.values() if x}; unresolved=sorted({n for _,n in entries if not resolved[n]})

# Official player-game rows, all seasons in one nflverse release. One REG game_id = one actual appearance.
allstats=csv_rows('https://github.com/nflverse/nflverse-data/releases/download/player_stats/player_stats.csv.gz',gz=True)
games={(y,pid):set() for y in YEARS for pid in ids}
for r in allstats:
 try:y=int(r.get('season') or 0)
 except:y=0
 if y not in YEARS or (r.get('season_type') or '').upper()!='REG':continue
 pid=(r.get('player_id') or '').strip()
 if pid not in ids:continue
 gid=(r.get('game_id') or '').strip() or f"{y}|{r.get('week')}|{r.get('team')}|{r.get('opponent_team')}"
 games[(y,pid)].add(gid)
official={(y,pid):len(gs) for (y,pid),gs in games.items()}

# Sleeper remains the scoring source; its GP fields are audited, not trusted as denominator.
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

season_diffs=[]; rebuilt={}; missing_score=[]
for dy,name in entries:
 pid=resolved.get(name)
 if not pid:continue
 pts=0.0; gp=0; seasons=0; through=None; pos=''
 for y in range(max(dy,2019),2026):
  ogp=official.get((y,pid),0); sk=resolve_name(name,sleeper[y]); sr=sleeper[y].get(sk) if sk else None
  sgp=sr['gp'] if sr else 0; p=sr['points'] if sr else 0.0
  if sr:pos=pos or sr['pos']
  if sgp!=ogp:season_diffs.append((dy,name,y,sgp,ogp,p,sr))
  if ogp>0:
   gp+=ogp; pts+=p; seasons+=1; through=y
   if sr is None:missing_score.append((dy,name,y,ogp))
 key=f'{dy}|{norm(name)}'
 if gp>0:rebuilt[key]={'ppg':pts/gp,'points':pts,'games':gp,'seasons':seasons,'through':through,'pos':pos}

changes=[]
for key in sorted(set(current)|set(rebuilt)):
 old=current.get(key); new=rebuilt.get(key)
 if old and old.get('excluded')=='veteran':continue
 if old and new:
  if old.get('games')!=new['games'] or abs(float(old.get('ppg',0))-new['ppg'])>.0005:changes.append((key,old,new))
 elif old or new:changes.append((key,old,new))

lines=['Dynasty Plebs denominator audit — stable GSIS identity + official player-game rows',
 'Points: Sleeper raw regular-season stats scored with Plebs rules.',
 'Games: nflverse weekly player_stats, REG only, unique game_id by GSIS player_id.',
 'Rule: only actual regular-season appearances count; IR/inactive/practice-squad weeks and 0-game seasons do not.',
 f'Draft entries: {len(entries)} | resolved unique player ids: {len(ids)} | unresolved names: {len(unresolved)}',
 f'Player-season denominator differences: {len(season_diffs)} | career draft-event changes: {len(changes)} | official appearances with no matched Sleeper row: {len(missing_score)}','']
if unresolved:
 lines.append('UNRESOLVED NAMES'); lines += ['  '+x for x in unresolved]; lines.append('')
lines.append('SEASON DIFFERENCES')
for dy,n,y,sgp,ogp,p,sr in sorted(season_diffs):
 raw=f"raw gp={sr['rawgp']!r}, active={sr['active']!r}" if sr else 'no Sleeper row'
 lines.append(f'{dy} pick | {n} | {y}: Sleeper denom {sgp} ({raw}) -> official {ogp}; Plebs pts {p:.2f}')
lines.append(''); lines.append('CAREER CHANGES')
for key,old,new in changes:
 if old and new:lines.append(f"{key}: games {old.get('games')} -> {new['games']}; PPG {float(old.get('ppg',0)):.3f} -> {new['ppg']:.3f}; points {float(old.get('points',0)):.2f} -> {new['points']:.2f}")
 elif new:lines.append(f"{key}: NEW games {new['games']}; PPG {new['ppg']:.3f}; points {new['points']:.2f}")
 else:lines.append(f'{key}: current outcome should be removed; 0 official appearances')
lines.append(''); lines.append('MISSING SLEEPER SCORING ROWS FOR OFFICIAL APPEARANCES')
for x in missing_score:lines.append(f'{x[0]} pick | {x[1]} | {x[2]} official games={x[3]}')
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8'); print('\n'.join(lines))
