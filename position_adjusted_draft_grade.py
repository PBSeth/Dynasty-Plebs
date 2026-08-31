import re
from pathlib import Path

p=Path('index.html')
s=p.read_text()
new=r'''function renderDraftIntel(){
 const box=document.getElementById('draftIntel'),allManagers=Object.keys(rookiePicks),getScored=m=>(rookiePicks[m]||[]).filter(p=>Number.isFinite(p.ppg)&&p.pos&&p.excluded!=='veteran'),scored=getScored(selectedManager);
 if(!scored.length){box.innerHTML=`<div class="intel-note">Career draft intel appears after an eligible rookie pick records an NFL regular-season game. Veteran selections are excluded.</div>`;return}
 const bucket=p=>Math.min(4,Number(p.pick.split('.')[0])),mean=vals=>vals.length?vals.reduce((a,v)=>a+v,0)/vals.length:null;
 const tagged=allManagers.flatMap(m=>getScored(m).map(p=>({...p,manager:m})));
 const expected=(p,manager)=>{
   const r=bucket(p),pos=p.pos;
   let peers=tagged.filter(x=>x.manager!==manager&&x.pos===pos&&bucket(x)===r);
   if(peers.length<2)peers=tagged.filter(x=>x.manager!==manager&&x.pos===pos);
   if(peers.length<2)peers=tagged.filter(x=>x.manager!==manager&&bucket(x)===r);
   if(!peers.length)peers=tagged.filter(x=>x.manager!==manager);
   return mean(peers.map(x=>x.ppg));
 };
 const delta=(p,m)=>{const e=expected(p,m);return Number.isFinite(e)?p.ppg-e:null};
 const rawAvg=d=>mean(d.map(p=>p.ppg));
 const adjAvg=(d,m)=>mean(d.map(p=>delta(p,m)).filter(Number.isFinite));
 const managerMetrics=allManagers.map(m=>{const d=getScored(m);if(!d.length)return null;const rounds={},rawRounds={};[1,2,3,4].forEach(r=>{const rd=d.filter(p=>bucket(p)===r);rounds[r]=adjAvg(rd,m);rawRounds[r]=rawAvg(rd)});return{m,avg:rawAvg(d),adj:adjAvg(d,m),rounds,rawRounds,n:d.length}}).filter(Boolean);
 const me=managerMetrics.find(x=>x.m===selectedManager),rank=(value,values)=>{const valid=values.filter(Number.isFinite).sort((a,b)=>b-a);if(!Number.isFinite(value)||!valid.length)return'';return`Rank ${1+valid.filter(v=>v>value+1e-9).length} of ${valid.length}`};
 const scoredWithDelta=scored.map(p=>({...p,adj:delta(p,selectedManager)})).filter(p=>Number.isFinite(p.adj));
 const best=[...scoredWithDelta].sort((a,b)=>b.adj-a.adj)[0],worst=[...scoredWithDelta].sort((a,b)=>a.adj-b.adj)[0];
 const roundCards=[1,2,3,4].map(r=>{const d=scored.filter(p=>bucket(p)===r),raw=rawAvg(d),adj=adjAvg(d,selectedManager),label=r===4?'Round 4+':`Round ${r}`,ranking=rank(adj,managerMetrics.map(x=>x.rounds[r]));return`<div class="intel-card"><small>${label} Avg Career PPG</small><b>${raw==null?'—':raw.toFixed(1)}</b><strong>${ranking||'No eligible scored picks'}${Number.isFinite(adj)?` · ${adj>=0?'+':''}${adj.toFixed(1)} adj`:''}</strong><span>${d.length} eligible scored pick${d.length===1?'':'s'}</span></div>`}).join('');
 box.innerHTML=`<div class="intel-card"><small>Avg Career PPG / Pick</small><b>${me.avg.toFixed(1)}</b><strong>Raw scoring only</strong><span>${me.n} eligible scored picks</span></div><div class="intel-card"><small>Pos + Round Draft Value</small><b>${me.adj==null?'—':(me.adj>=0?'+':'')+me.adj.toFixed(1)}</b><strong>${rank(me.adj,managerMetrics.map(x=>x.adj))}</strong><span>vs other managers at same position + round</span></div><div class="intel-card"><small>Best Adjusted Pick</small><strong>${best?best.player:'—'}</strong><span>${best?`${best.year} · ${best.pick} · ${best.ppg.toFixed(1)} PPG · ${best.adj>=0?'+':''}${best.adj.toFixed(1)} adj`:'No eligible scored picks'}</span></div><div class="intel-card"><small>Worst Adjusted Pick</small><strong>${worst?worst.player:'—'}</strong><span>${worst?`${worst.year} · ${worst.pick} · ${worst.ppg.toFixed(1)} PPG · ${worst.adj>=0?'+':''}${worst.adj.toFixed(1)} adj`:'No eligible scored picks'}</span></div>${roundCards}<div class="intel-note">Career PPG remains the raw descriptive stat for eligible rookie selections. Manager draft grading is position- and round-adjusted: each eligible pick is compared with other managers' picks at the same position and rookie-draft round. Veteran selections remain in the historical draft board but are excluded from all rookie PPG averages, rankings, best/worst picks, and adjusted grades.</div>`;
}'''
s2,n=re.subn(r'function renderDraftIntel\(\)\{.*?\n\}\nfunction renderRookies',new+'\nfunction renderRookies',s,count=1,flags=re.S)
if n!=1: raise SystemExit(f'renderDraftIntel replacements: {n}')
p.write_text(s2)
print('Applied position + round adjusted draft grading with veteran exclusions')
