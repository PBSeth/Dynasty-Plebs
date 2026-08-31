import re
from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

css=r'''/* LEGACY_HERO_20260831 */
.record-hero small{font-size:11px!important}.record-hero b{font-size:clamp(48px,9vw,72px)!important}.legacy-rank{display:block;margin-top:7px;color:var(--muted);font-size:11px;font-weight:900;letter-spacing:.06em;text-transform:uppercase}.profile-stats{grid-template-columns:repeat(4,1fr)!important}
@media(max-width:700px){.profile-stats{grid-template-columns:repeat(2,1fr)!important}}
/* END_LEGACY_HERO_20260831 */'''
s=re.sub(r'/\* LEGACY_HERO_20260831 \*/.*?/\* END_LEGACY_HERO_20260831 \*/','',s,flags=re.S)
s=s.replace('</style>',css+'\n</style>',1)

new=r'''function renderManager(name){selectedManager=name;rookieYear=null;const c=careers.find(x=>x.m===name),h=[...(history.get(name)||[])].sort((a,b)=>a.year-b.year),latest=h.at(-1),active=currentManagers.has(name),legacy=(typeof legacyScores!=='undefined'?legacyScores[name]:null),legacyVals=typeof legacyScores!=='undefined'?Object.values(legacyScores).filter(Number.isFinite).sort((a,b)=>b-a):[],legacyRank=Number.isFinite(legacy)?1+legacyVals.filter(v=>v>legacy+1e-9).length:null;document.documentElement.style.setProperty('--manager-color',managerColors[name]||'#7a3023');document.getElementById('profile').innerHTML=`<div class="profile-top"><div class="profile-title"><h2>${name}</h2><p>${c.s} seasons · ${h[0].year}–${latest.year}</p></div><span class="status ${active?'':'former'}">${active?'Active':'Former'}</span></div><div class="team-pill">${latest.team}</div><div class="record-hero"><small>Legacy Score</small><b>${Number.isFinite(legacy)?Math.round(legacy).toLocaleString():'—'}</b>${legacyRank?`<span class="legacy-rank">#${legacyRank} all-time</span>`:''}</div><div class="profile-stats"><div class="profile-stat"><small>Career Record</small><b>${c.w}-${c.l}</b></div><div class="profile-stat"><small>Win %</small><b>${winDec(c.p)}</b></div><div class="profile-stat"><small>Points For</small><b>${nf.format(c.pf)}</b></div><div class="profile-stat"><small>Points Against</small><b>${nf.format(c.pa)}</b></div></div>`;document.getElementById('history').innerHTML=[...h].sort((a,b)=>b.year-a.year).map(s=>`<div class="history-row"><div class="history-year">${s.year}</div><div class="history-team"><strong>${s.team}</strong><small>PF ${nf.format(s.pf)} · PA ${nf.format(s.pa)}</small></div><div class="history-record">${s.w}-${s.l}<small>${winDec(s.w/(s.w+s.l))}</small></div></div>`).join('');drawTimeline();renderRookies()}'''
s,n=re.subn(r'function renderManager\(name\)\{.*?\}\n(?=drawChart\(\);)',new+'\n',s,count=1,flags=re.S)
if n!=1: raise SystemExit(f'renderManager replacement count={n}')
p.write_text(s,encoding='utf-8')
print('Moved Legacy Score into the manager hero and moved career W-L into the stat row.')
