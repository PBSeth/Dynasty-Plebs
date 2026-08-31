from pathlib import Path
import json, re, urllib.request

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'index.html'
BASE = 'https://api.sleeper.app/v1'

CANON = {
    'mcnutted86': 'Jordan Martin',
    'peedawg': 'Payton Docheff',
    'justintreyreed': 'Bo Tiller',
    'sharkmoons': 'Bo Tiller',
    'mrplows': 'Clint Hudson',
    'pbseth': 'Seth Miller',
    'tomahawkchop6': 'Travis Page',
    'matthewmetz1985': 'Matt Metz',
    'abogueros': 'Alex Agueros',
    'imjustluke': 'Luke Miller',
    'shuturmuth': 'David Carnes',
    'rjlipkin': 'Ryan Lipkin',
    'clawdaddy69': 'Matt Clawson',
}


def get_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Dynasty-Plebs-Archive/1.0'})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)


def norm(s):
    return re.sub(r'[^a-z0-9]', '', str(s or '').lower())


def discover_champion(year):
    user = get_json(f'{BASE}/user/PBSeth')
    uid = user['user_id']
    leagues = get_json(f'{BASE}/user/{uid}/leagues/nfl/{year}')
    candidates = [l for l in leagues if 'pleb' in str(l.get('name', '')).lower()]
    if len(candidates) != 1:
        names = [l.get('name') for l in leagues]
        raise RuntimeError(f'{year}: expected one Plebs league, found {len(candidates)}; leagues={names}')
    league = candidates[0]
    lid = league['league_id']
    bracket = get_json(f'{BASE}/league/{lid}/winners_bracket')
    finals = [m for m in bracket if m.get('p') == 1 and m.get('w') is not None]
    if len(finals) != 1:
        raise RuntimeError(f'{year}: could not identify completed championship match: {bracket}')
    champ_roster = finals[0]['w']
    rosters = get_json(f'{BASE}/league/{lid}/rosters')
    users = get_json(f'{BASE}/league/{lid}/users')
    roster = next((r for r in rosters if r.get('roster_id') == champ_roster), None)
    if not roster:
        raise RuntimeError(f'{year}: championship roster {champ_roster} missing')
    owner = next((u for u in users if u.get('user_id') == roster.get('owner_id')), None)
    if not owner:
        raise RuntimeError(f'{year}: owner missing for championship roster {champ_roster}')
    username = str(owner.get('username') or owner.get('display_name') or '').lower()
    manager = CANON.get(username)
    if not manager:
        # Exact fallback against canonical manager names via display name.
        display = str(owner.get('display_name') or '')
        canon_names = set(CANON.values())
        manager = next((n for n in canon_names if norm(n) == norm(display)), display)
    print(f'{year} Sleeper champion: {manager} ({owner.get("username")}) league={league.get("name")} id={lid}')
    return manager


def parse_seasons(src):
    m = re.search(r'const seasons=(\[.*?\]);\nconst champions=', src, re.S)
    if not m:
        raise RuntimeError('Could not parse seasons data')
    return json.loads(m.group(1))


def team_for(seasons, year, manager):
    season = next(s for s in seasons if s['y'] == year)
    row = next((r for r in season['r'] if r[0] == manager), None)
    if not row:
        raise RuntimeError(f'{year}: champion {manager} not found in season standings')
    return row[1]


src = INDEX.read_text()
seasons = parse_seasons(src)

# Preserve verified archive champions and fetch the two missing Sleeper-era winners.
champions = [
    {'year': 2019, 'manager': 'David Carnes', 'team': 'Turn Down for WATT'},
    {'year': 2020, 'manager': 'Matthew Piontek', 'team': "Mott's Applesauce"},
    {'year': 2021, 'manager': 'Matthew Piontek', 'team': "Mott's Applesauce"},
    {'year': 2022, 'manager': 'Seth Miller', 'team': 'The Collector'},
    {'year': 2023, 'manager': 'Jordan Martin', 'team': 'Team Bad fingers'},
]
for year in (2024, 2025):
    manager = discover_champion(year)
    champions.append({'year': year, 'manager': manager, 'team': team_for(seasons, year, manager)})

champ_line = 'const champions=' + json.dumps(champions, separators=(',', ':')) + ';'
src, n = re.subn(r'const champions=\[.*?\];', champ_line, src, count=1, flags=re.S)
if n != 1:
    raise RuntimeError('Champions block replacement failed')

# All-Time: active managers first, sorted by the selected metric; former managers follow,
# also sorted by that metric. Show the complete archive rather than truncating to 12.
new_draw_chart = r'''function drawChart(){const m=metrics[metric],d=[...careers].sort((a,b)=>{const aa=currentManagers.has(a.m)?0:1,bb=currentManagers.has(b.m)?0:1;return aa-bb||m.get(b)-m.get(a)||b.s-a.s||b.pf-a.pf}),max=Math.max(...d.map(m.get));document.getElementById('chart').innerHTML=d.map((x,i)=>`<div class="bar"><div><strong>${i+1}. ${x.m}</strong><small>${m.sub(x)}${currentManagers.has(x.m)?'':' · Former'}</small></div><div class="track"><div class="fill" style="width:${Math.max(4,m.get(x)/max*100)}%"></div></div><div class="val">${m.fmt(m.get(x))}</div></div>`).join('')}'''
src, n = re.subn(r'function drawChart\(\)\{.*?\}\n(?=function showView)', new_draw_chart + '\n', src, count=1, flags=re.S)
if n != 1:
    raise RuntimeError('All-Time drawChart replacement failed')

# Manager timeline: PF and PA share one fixed-scale overlay. Keep labels compact for mobile.
new_timeline_metrics = r'''const timelineMetrics={wins:{label:'Season Wins',get:s=>s.w,fmt:v=>String(Math.round(v)),axis:v=>String(Math.round(v)),min:0,max:14,ticks:[0,3.5,7,10.5,14]},pct:{label:'Win %',get:s=>s.w/(s.w+s.l),fmt:v=>winDec(v),axis:v=>v.toFixed(2).replace(/^0/,''),min:0,max:1,ticks:[0,.25,.5,.75,1]},points:{label:'PF / PA',axis:v=>Math.round(v).toLocaleString(),min:900,max:2200,ticks:[900,1225,1550,1875,2200]}};'''
src, n = re.subn(r'const timelineMetrics=\{.*?\};\n(?=const tc=)', new_timeline_metrics + '\n', src, count=1, flags=re.S)
if n != 1:
    raise RuntimeError('timelineMetrics replacement failed')

new_draw_timeline = r'''function drawTimeline(){const h=[...(history.get(selectedManager)||[])].sort((a,b)=>a.year-b.year),m=timelineMetrics[timelineMetric];if(!h.length){document.getElementById('timelineBox').innerHTML='';return}const W=760,H=270,p={l:56,r:24,t:28,b:38},iw=W-p.l-p.r,ih=H-p.t-p.b,min=m.min,max=m.max,range=max-min,x=i=>p.l+(h.length===1?iw/2:i*iw/(h.length-1)),y=v=>p.t+(max-v)/range*ih;const grids=m.ticks.map(t=>{const yy=y(t);return `<line class="grid-line" x1="${p.l}" x2="${W-p.r}" y1="${yy}" y2="${yy}"/><text class="axis-label" x="${p.l-9}" y="${yy+3}" text-anchor="end">${m.axis(t)}</text>`}).join(''),years=h.map((s,i)=>`<text class="axis-label" x="${x(i)}" y="${H-12}" text-anchor="middle">${s.year}</text>`).join('');if(timelineMetric==='points'){const makePts=key=>h.map((s,i)=>({x:x(i),y:y(s[key]),v:s[key],s})),pf=makePts('pf'),pa=makePts('pa'),path=pts=>pts.map((q,i)=>`${i?'L':'M'} ${q.x.toFixed(1)} ${q.y.toFixed(1)}`).join(' '),dots=(pts,cls,key)=>pts.map(q=>`<circle class="series-dot ${cls}" cx="${q.x}" cy="${q.y}" r="5"><title>${q.s.year} ${key}: ${nf.format(q.v)}</title></circle>`).join(''),labels=(pts,cls,key,dy)=>pts.map(q=>`<text class="point-label ${cls}" x="${q.x}" y="${Math.max(12,Math.min(H-28,q.y+dy))}">${key} ${Math.round(q.v).toLocaleString()}</text>`).join('');document.getElementById('timelineBox').innerHTML=`<div class="timeline-legend"><span><i class="legend-pf"></i>PF</span><span><i class="legend-pa"></i>PA</span></div><svg class="timeline-svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="PF and PA timeline for ${selectedManager}">${grids}<path class="series-line" d="${path(pf)}"/><path class="series-line pa" d="${path(pa)}"/>${dots(pf,'','PF')}${dots(pa,'pa','PA')}${labels(pf,'','PF',-11)}${labels(pa,'pa','PA',14)}${years}</svg>`;return}const pts=h.map((s,i)=>({x:x(i),y:y(m.get(s)),v:m.get(s),s})),path=pts.map((q,i)=>`${i?'L':'M'} ${q.x.toFixed(1)} ${q.y.toFixed(1)}`).join(' '),area=`${path} L ${pts.at(-1).x.toFixed(1)} ${(p.t+ih).toFixed(1)} L ${pts[0].x.toFixed(1)} ${(p.t+ih).toFixed(1)} Z`,dots=pts.map(q=>`<circle class="series-dot" cx="${q.x}" cy="${q.y}" r="5"><title>${q.s.year}: ${m.fmt(q.v)}</title></circle>`).join(''),labels=pts.map(q=>`<text class="point-label" x="${q.x}" y="${Math.max(12,q.y-11)}">${m.fmt(q.v)}</text>`).join('');document.getElementById('timelineBox').innerHTML=`<svg class="timeline-svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="${m.label} timeline for ${selectedManager}">${grids}<path class="series-area" d="${area}"/><path class="series-line" d="${path}"/>${dots}${labels}${years}</svg>`}'''
src, n = re.subn(r'function drawTimeline\(\)\{.*?\}\n(?=function )', new_draw_timeline + '\n', src, count=1, flags=re.S)
if n != 1:
    raise RuntimeError('drawTimeline replacement failed')

# Add a visually distinct PA series and compact inline legend without changing the manager PF color.
css_anchor = '.point-label{font-size:8px;fill:#5d5244;font-weight:800;text-anchor:middle}.scale-note{padding:8px 12px 0;color:var(--muted);font-size:10px;text-align:right}'
css_new = '.point-label{font-size:8px;fill:#5d5244;font-weight:800;text-anchor:middle}.series-line.pa{stroke:#8a6b3b}.series-dot.pa{stroke:#8a6b3b}.point-label.pa{fill:#7b6648}.timeline-legend{display:flex;justify-content:flex-end;gap:12px;padding:7px 12px 0;color:var(--muted);font-size:9px;font-weight:900}.timeline-legend span{display:flex;align-items:center;gap:4px}.timeline-legend i{display:inline-block;width:15px;height:3px;border-radius:3px;background:var(--manager-color,#7a3023)}.timeline-legend i.legend-pa{background:#8a6b3b}.scale-note{padding:8px 12px 0;color:var(--muted);font-size:10px;text-align:right}'
if css_anchor in src:
    src = src.replace(css_anchor, css_new, 1)
elif '.series-line.pa{' not in src:
    raise RuntimeError('CSS timeline anchor missing')

INDEX.write_text(src)
print('Updated champions:', champions)
print('Applied active-first All-Time sorting and combined PF / PA manager timeline.')
