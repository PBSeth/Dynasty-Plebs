from pathlib import Path
import re

p = Path("index.html")
s = p.read_text()

old_metrics = "const timelineMetrics={wins:{label:'Season Wins',get:s=>s.w,fmt:v=>String(Math.round(v)),axis:v=>String(Math.round(v)),min:0,max:14,ticks:[0,3.5,7,10.5,14]},pct:{label:'Win %',get:s=>s.w/(s.w+s.l),fmt:v=>winDec(v),axis:v=>v.toFixed(2).replace(/^0/,''),min:0,max:1,ticks:[0,.25,.5,.75,1]},pf:{label:'PF',get:s=>s.pf,fmt:v=>nf.format(v),axis:v=>Math.round(v).toLocaleString(),min:900,max:2200,ticks:[900,1225,1550,1875,2200]},pa:{label:'PA',get:s=>s.pa,fmt:v=>nf.format(v),axis:v=>Math.round(v).toLocaleString(),min:1100,max:1700,ticks:[1100,1250,1400,1550,1700]}};"
new_metrics = "const timelineMetrics={wins:{label:'Season Wins',get:s=>s.w,fmt:v=>String(Math.round(v)),axis:v=>String(Math.round(v)),min:0,max:14,ticks:[0,3.5,7,10.5,14]},pct:{label:'Win %',get:s=>s.w/(s.w+s.l),fmt:v=>winDec(v),axis:v=>v.toFixed(2).replace(/^0/,''),min:0,max:1,ticks:[0,.25,.5,.75,1]},pfpa:{label:'PF / PA',fmt:v=>nf.format(v),axis:v=>Math.round(v).toLocaleString(),min:900,max:2200,ticks:[900,1225,1550,1875,2200]}};"
if old_metrics not in s:
    raise SystemExit("timeline metrics target not found")
s = s.replace(old_metrics, new_metrics)

new_draw = r'''function drawTimeline(){
 const h=[...(history.get(selectedManager)||[])].sort((a,b)=>a.year-b.year),m=timelineMetrics[timelineMetric];
 if(!h.length){document.getElementById('timelineBox').innerHTML='';return}
 const W=760,H=270,p={l:56,r:24,t:28,b:38},iw=W-p.l-p.r,ih=H-p.t-p.b,min=m.min,max=m.max,range=max-min;
 const x=i=>p.l+(h.length===1?iw/2:i*iw/(h.length-1)),y=v=>p.t+(max-v)/range*ih;
 const grids=m.ticks.map(t=>{const yy=y(t);return `<line class="grid-line" x1="${p.l}" x2="${W-p.r}" y1="${yy}" y2="${yy}"/><text class="axis-label" x="${p.l-9}" y="${yy+3}" text-anchor="end">${m.axis(t)}</text>`}).join('');
 if(timelineMetric==='pfpa'){
   const PF_COLOR='#8b3428',PA_COLOR='#3d6d88';
   const pf=h.map((s,i)=>({x:x(i),y:y(s.pf),v:s.pf,s})),pa=h.map((s,i)=>({x:x(i),y:y(s.pa),v:s.pa,s}));
   const mkPath=pts=>pts.map((q,i)=>`${i?'L':'M'} ${q.x.toFixed(1)} ${q.y.toFixed(1)}`).join(' ');
   const years=pf.map(q=>`<text class="axis-label" x="${q.x}" y="${H-12}" text-anchor="middle">${q.s.year}</text>`).join('');
   const dots=(pts,color,key)=>pts.map(q=>`<circle class="series-dot" style="stroke:${color}" cx="${q.x}" cy="${q.y}" r="5"><title>${q.s.year} ${key}: ${m.fmt(q.v)}</title></circle>`).join('');
   const labels=(pts,color,below=false)=>pts.map(q=>`<text class="point-label" style="fill:${color}" x="${q.x}" y="${below?Math.min(H-43,q.y+20):Math.max(13,q.y-12)}">${m.fmt(q.v)}</text>`).join('');
   document.getElementById('timelineBox').innerHTML=`<div style="display:flex;justify-content:flex-end;gap:14px;padding:5px 8px 0;font-size:11px;font-weight:900;color:#625746"><span style="display:inline-flex;align-items:center;gap:5px"><i style="width:18px;height:3px;border-radius:99px;background:${PF_COLOR}"></i>PF</span><span style="display:inline-flex;align-items:center;gap:5px"><i style="width:18px;height:3px;border-radius:99px;background:${PA_COLOR}"></i>PA</span></div><svg class="timeline-svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Points for and points against timeline for ${selectedManager}">${grids}<path class="series-line" style="stroke:${PF_COLOR}" d="${mkPath(pf)}"/><path class="series-line" style="stroke:${PA_COLOR}" d="${mkPath(pa)}"/>${dots(pf,PF_COLOR,'PF')}${dots(pa,PA_COLOR,'PA')}${labels(pf,PF_COLOR)}${labels(pa,PA_COLOR,true)}${years}</svg>`;
   return;
 }
 const pts=h.map((s,i)=>({x:x(i),y:y(m.get(s)),v:m.get(s),s}));
 const path=pts.map((q,i)=>`${i?'L':'M'} ${q.x.toFixed(1)} ${q.y.toFixed(1)}`).join(' '),area=`${path} L ${pts.at(-1).x.toFixed(1)} ${(p.t+ih).toFixed(1)} L ${pts[0].x.toFixed(1)} ${(p.t+ih).toFixed(1)} Z`;
 const years=pts.map(q=>`<text class="axis-label" x="${q.x}" y="${H-12}" text-anchor="middle">${q.s.year}</text>`).join(''),dots=pts.map(q=>`<circle class="series-dot" cx="${q.x}" cy="${q.y}" r="5"><title>${q.s.year}: ${m.fmt(q.v)}</title></circle>`).join(''),labels=pts.map(q=>`<text class="point-label" x="${q.x}" y="${Math.max(12,q.y-11)}">${m.fmt(q.v)}</text>`).join('');
 document.getElementById('timelineBox').innerHTML=`<svg class="timeline-svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="${m.label} timeline for ${selectedManager}">${grids}<path class="series-area" d="${area}"/><path class="series-line" d="${path}"/>${dots}${labels}${years}</svg>`;
}
'''
s2 = re.sub(r'function drawTimeline\(\)\{.*?(?=function renderDraftIntel\(\)\{)', new_draw, s, count=1, flags=re.S)
if s2 == s:
    raise SystemExit("drawTimeline target not found")
s = s2

new_intel = r'''function renderDraftIntel(){
 const picks=rookiePicks[selectedManager]||[],scored=picks.filter(p=>p.year<=2023&&Number.isFinite(p.ppg)),box=document.getElementById('draftIntel');
 if(!scored.length){box.innerHTML=`<div class="intel-note">First-three-year draft intel appears when this manager has mature WR/RB picks with verified Half-PPR outcomes.</div>`;return}
 const bucket=p=>Math.min(4,Number(p.pick.split('.')[0]));
 const managerNames=careers.map(c=>c.m);
 const scoredFor=name=>(rookiePicks[name]||[]).filter(p=>p.year<=2023&&Number.isFinite(p.ppg));
 const avgOf=d=>d.length?d.reduce((a,p)=>a+p.ppg,0)/d.length:null;
 const rankValue=(value,values)=>{const valid=values.filter(Number.isFinite).sort((a,b)=>b-a);return{rank:1+valid.filter(v=>v>value+1e-9).length,total:valid.length}};
 const avg=avgOf(scored),best=[...scored].sort((a,b)=>b.ppg-a.ppg)[0],worst=[...scored].sort((a,b)=>a.ppg-b.ppg)[0];
 const overallRanks=rankValue(avg,managerNames.map(n=>avgOf(scoredFor(n))));
 const allScored=managerNames.flatMap(scoredFor),base={};
 [1,2,3,4].forEach(r=>{const d=allScored.filter(p=>bucket(p)===r);base[r]=avgOf(d)});
 const managerAdjusted=name=>{const d=scoredFor(name).map(p=>p.ppg-base[bucket(p)]).filter(Number.isFinite);return d.length?d.reduce((a,v)=>a+v,0)/d.length:null};
 const adj=managerAdjusted(selectedManager),adjRanks=Number.isFinite(adj)?rankValue(adj,managerNames.map(managerAdjusted)):null;
 const roundStats=[1,2,3,4].map(r=>{
   const d=scored.filter(p=>bucket(p)===r),a=avgOf(d),delta=a==null||base[r]==null?null:a-base[r];
   const ranks=a==null?null:rankValue(a,managerNames.map(n=>avgOf(scoredFor(n).filter(p=>bucket(p)===r))));
   return{r,label:r===4?'Round 4+':`Round ${r}`,n:d.length,avg:a,delta,ranks};
 });
 const rankText=r=>r?`Rank ${r.rank} of ${r.total}`:'No rank';
 box.innerHTML=`<div class="intel-card"><small>Avg 3Y PPG / Pick</small><b>${avg.toFixed(1)}</b><span>${rankText(overallRanks)} · all mature WR/RB picks</span></div><div class="intel-card"><small>Round-Adjusted PPG</small><b>${adj==null?'—':(adj>=0?'+':'')+adj.toFixed(1)}</b><span>${adjRanks?rankText(adjRanks):'No rank'} · vs same-round league avg</span></div><div class="intel-card"><small>Best Pick</small><strong>${best.player}</strong><span>${best.year} · ${best.pick} · ${best.ppg.toFixed(1)} PPG</span></div><div class="intel-card"><small>Worst Pick</small><strong>${worst.player}</strong><span>${worst.year} · ${worst.pick} · ${worst.ppg.toFixed(1)} PPG</span></div>${roundStats.map(x=>`<div class="intel-card"><small>${x.label} Avg 3Y PPG</small><b>${x.avg==null?'—':x.avg.toFixed(1)}</b><span>${x.ranks?rankText(x.ranks)+' · ':''}${x.n} scored${x.delta==null?'':' · '+(x.delta>=0?'+':'')+x.delta.toFixed(1)+' vs league'}</span></div>`).join('')}<div class="intel-note">Ranks compare each manager with every other manager who has at least one mature scored WR/RB pick in that category. Round-adjusted PPG compares each pick with the league average from the same rookie-draft round. QB/TE picks and 2024–2026 classes remain in the history but are excluded from completed first-three-year Half-PPR outcome averages.</div>`;
}
'''
s2 = re.sub(r'function renderDraftIntel\(\)\{.*?(?=function renderRookies\(\)\{)', new_intel, s, count=1, flags=re.S)
if s2 == s:
    raise SystemExit("renderDraftIntel target not found")
s = s2

p.write_text(s)
