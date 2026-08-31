import base64,gzip,json,re,unicodedata,urllib.request
from pathlib import Path

DATA=json.loads(gzip.decompress(base64.b64decode(Path('ballers_exports_2019_2023.json.gz.b64').read_text())).decode())
POSITIONS={'QB','RB','WR','TE'}
ALIASES={
 'gabrieldavis':'gabedavis','dwayneeskridge':'deeeskridge','joshpalmer':'joshuapalmer',
 'kenwalkeriii':'kennethwalkeriii','nathanieldell':'tankdell','terracemarshall':'terracemarshalljr',
 'brianrobinson':'brianrobinsonjr','jaelondarden':'jaleondarden','devontasmith':'devontasmith',
 'laviskashenault':'laviskashenaultjr','irvsmith':'irvsmithjr','mikewilliams':'mikewilliams',
 'odellbeckham':'odellbeckhamjr','djchark':'djcharkjr','marvinjones':'marvinjonesjr',
 'ronaldjones':'ronaldjonesii','melvingordon':'melvingordoniii','willfuller':'willfullerv',
}

def norm(x):
 s=unicodedata.normalize('NFD',str(x or '').lower())
 s=''.join(c for c in s if unicodedata.category(c)!='Mn')
 return re.sub(r'[^a-z0-9]','',s)

def strip_suffix(n):
 for suf in ('junior','senior','jr','sr','iii','ii','iv','v'):
  if n.endswith(suf) and len(n)>len(suf)+3:return n[:-len(suf)]
 return n

def num(x):
 try:return float(x or 0)
 except:return 0.0

def raw_ffb(s):
 # Historical Fantasy Footballers exports used half-PPR, 4-point passing TDs and -1 INT.
 # Score only from Sleeper raw stats so this is an independent check of our formula.
 special=num(s.get('st_td'))
 if not special:
  special=num(s.get('kick_ret_td'))+num(s.get('punt_ret_td'))
 return (
  num(s.get('pass_yd'))*.04+num(s.get('pass_td'))*4-num(s.get('pass_int'))+num(s.get('pass_2pt'))*2+
  num(s.get('rush_yd'))*.1+num(s.get('rush_td'))*6+num(s.get('rush_2pt'))*2+
  num(s.get('rec'))*.5+num(s.get('rec_yd'))*.1+num(s.get('rec_td'))*6+num(s.get('rec_2pt'))*2-
  num(s.get('fum_lost'))*2+num(s.get('fum_rec_td'))*6+special*6
 )

def fetch(year):
 req=urllib.request.Request(f'https://api.sleeper.com/stats/nfl/{year}?season_type=regular',headers={'User-Agent':'Mozilla/5.0 Dynasty-Plebs audit'})
 return json.load(urllib.request.urlopen(req,timeout=45))

def pname(r):
 p=r.get('player') or {}
 return (p.get('full_name') or ' '.join(x for x in (p.get('first_name'),p.get('last_name')) if x) or r.get('player_name') or '').strip()

def ppos(r):
 p=r.get('player') or {}
 return (p.get('position') or r.get('position') or '').upper()

def build_lookup(rows):
 out={}
 for r in rows:
  if ppos(r) not in POSITIONS:continue
  name=pname(r)
  if not name:continue
  k=norm(name); score=raw_ffb(r.get('stats') or {})
  # Same named player can appear in stale/duplicate Sleeper rows. Keep the row with more GP,
  # then more absolute fantasy output.
  gp=num((r.get('stats') or {}).get('gp') or (r.get('stats') or {}).get('gms_active'))
  old=out.get(k)
  if old is None or (gp,abs(score))>(old['gp'],abs(old['score'])):
   out[k]={'record':r,'name':name,'pos':ppos(r),'score':score,'gp':gp}
 return out

def resolve(name,pos,lookup):
 n=norm(name); candidates=[n,ALIASES.get(n),strip_suffix(n)]
 if ALIASES.get(n): candidates.append(strip_suffix(ALIASES[n]))
 for c in candidates:
  if c in lookup and lookup[c]['pos']==pos:return lookup[c]
 base=strip_suffix(n)
 matches=[v for k,v in lookup.items() if v['pos']==pos and strip_suffix(k)==base]
 return matches[0] if len(matches)==1 else None

total=matched=exact=near=0; absdiff=0.0; diffs=[]; unmatch=[]
for year in range(2019,2024):
 lookup=build_lookup(fetch(year))
 print(f'\n=== {year} ===')
 for pos in ('QB','RB','WR','TE'):
  rows=DATA[str(year)][pos]; ymatch=yexact=0; yabs=0.0; yd=[]
  for x in rows:
   total+=1
   hit=resolve(x['player'],pos,lookup)
   if not hit:
    unmatch.append((year,pos,x['player'],x['points'])); continue
   matched+=1; ymatch+=1
   got=round(hit['score'],2); exp=round(float(x['points']),2); d=round(got-exp,2)
   absdiff+=abs(d); yabs+=abs(d)
   if abs(d)<=.11: exact+=1; yexact+=1
   elif abs(d)<=.25: near+=1
   else: diffs.append((abs(d),year,pos,x['player'],hit['name'],exp,got,d,hit['record'].get('stats') or {})); yd.append(d)
  print(f'{pos}: matched {ymatch}/{len(rows)} | exact {yexact}/{ymatch or 1} | MAE {yabs/(ymatch or 1):.3f} | material {sum(abs(d)>.25 for d in yd)}')

print('\n=== OVERALL ===')
print(f'Rows in uploaded exports: {total}')
print(f'Name matched: {matched}/{total} ({matched/total:.2%})')
print(f'Exact within 0.11: {exact}/{matched} ({exact/(matched or 1):.2%})')
print(f'Additional within 0.25: {near}')
print(f'MAE across matched rows: {absdiff/(matched or 1):.4f}')
print(f'Material discrepancies >0.25: {len(diffs)}')
print(f'Unmatched names: {len(unmatch)}')

print('\nLargest discrepancies:')
for _,year,pos,csvname,sname,exp,got,d,s in sorted(diffs,reverse=True)[:80]:
 keys=('pass_yd','pass_td','pass_int','pass_2pt','rush_yd','rush_td','rush_2pt','rec','rec_yd','rec_td','rec_2pt','fum_lost','fum_rec_td','st_td','kick_ret_td','punt_ret_td')
 stats={k:s.get(k) for k in keys if num(s.get(k))}
 print(f'{year} {pos} {csvname} -> {sname}: export {exp:.2f}, raw {got:.2f}, diff {d:+.2f} | {stats}')

if unmatch:
 print('\nUnmatched:')
 for x in unmatch: print(*x)
