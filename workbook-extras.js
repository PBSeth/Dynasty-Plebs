(()=>{
  const DATA=window.DATA;
  if(!DATA)return;
  const current=new Set(DATA.currentManagers||[]);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const recWins=r=>r?Number(String(r).split('-')[0])||0:0;
  const recPct=r=>{if(!r)return null;const [w,l]=String(r).split('-').map(Number);return Number.isFinite(w)&&Number.isFinite(l)&&w+l?w/(w+l):null};

  const champs=document.getElementById('champions');
  if(champs){
    champs.innerHTML=DATA.champions.map(c=>`<div class="champ"><small>${c.year} Champion</small><strong>${esc(c.manager)}</strong></div>`).join('');
  }

  const historyMetrics={
    legacy:{label:'Legacy Score',get:m=>DATA.legacy[m]?.score??0,fmt:(m,v)=>Number(v).toLocaleString(),sort:(a,b)=>(DATA.legacy[b]?.score??0)-(DATA.legacy[a]?.score??0)},
    wins:{label:'Reg. Wins',get:m=>recWins(DATA.regular[m]?.total),fmt:(m,v)=>String(v),sort:(a,b)=>recWins(DATA.regular[b]?.total)-recWins(DATA.regular[a]?.total)},
    pct:{label:'Win %',get:m=>DATA.regular[m]?.winPct??0,fmt:(m,v)=>(v*100).toFixed(1)+'%',sort:(a,b)=>(DATA.regular[b]?.winPct??0)-(DATA.regular[a]?.winPct??0)},
    avg:{label:'Avg Finish',get:m=>Math.max(0,13-(DATA.legacy[m]?.avg??13)),fmt:m=>Number.isFinite(DATA.legacy[m]?.avg)?DATA.legacy[m].avg.toFixed(2):'—',sort:(a,b)=>(DATA.legacy[a]?.avg??99)-(DATA.legacy[b]?.avg??99)}
  };
  let historyMetric='legacy';
  const historyBtns=document.getElementById('historyMetricBtns');
  const historyChart=document.getElementById('historyChart');
  function renderHistory(){
    if(!historyBtns||!historyChart)return;
    historyBtns.innerHTML=Object.entries(historyMetrics).map(([k,m])=>`<button class="${k===historyMetric?'on':''}" data-metric="${k}">${m.label}</button>`).join('');
    historyBtns.querySelectorAll('button').forEach(b=>b.onclick=()=>{historyMetric=b.dataset.metric;renderHistory()});
    const metric=historyMetrics[historyMetric];
    const managers=Object.keys(DATA.regular).sort((a,b)=>(current.has(a)?0:1)-(current.has(b)?0:1)||metric.sort(a,b)||a.localeCompare(b));
    const max=historyMetric==='legacy'?2500:Math.max(1,...managers.map(metric.get));
    historyChart.innerHTML=managers.map((m,i)=>{
      const v=metric.get(m),width=Math.max(3,v/max*100);
      return `<div class="archive-bar"><strong>${i+1}. ${esc(m)}</strong><div class="archive-track"><div class="archive-fill" style="width:${width}%"></div></div><div class="archive-value">${esc(metric.fmt(m,v))}</div></div>`;
    }).join('');
    if(historyMetric==='legacy')historyChart.dataset.legacyScale='0-2500';
    else delete historyChart.dataset.legacyScale;
  }
  renderHistory();

  const timelineMetrics={
    wins:{label:'Season Wins',min:0,max:14,ticks:[0,3.5,7,10.5,14],get:(m,y)=>recWins(DATA.regular[m]?.yearly?.[y]),fmt:v=>String(Math.round(v)),axis:v=>String(Math.round(v))},
    pct:{label:'Win %',min:0,max:1,ticks:[0,.25,.5,.75,1],get:(m,y)=>recPct(DATA.regular[m]?.yearly?.[y]),fmt:v=>(v*100).toFixed(0)+'%',axis:v=>v.toFixed(2).replace(/^0/,'')},
    finish:{label:'Final Finish',min:1,max:12,ticks:[1,4,7,10,12],invert:true,get:(m,y)=>DATA.legacy[m]?.finish?.[y],fmt:v=>'#'+Math.round(v),axis:v=>'#'+Math.round(v)}
  };
  let timelineMetric='wins';
  const managerSelect=document.getElementById('managerSelect');
  const timelineBtns=document.getElementById('timelineMetricBtns');
  const timelineBox=document.getElementById('managerTimeline');
  function renderTimelineControls(){
    if(!timelineBtns)return;
    timelineBtns.innerHTML=Object.entries(timelineMetrics).map(([k,m])=>`<button class="${k===timelineMetric?'on':''}" data-timeline="${k}">${m.label}</button>`).join('');
    timelineBtns.querySelectorAll('button').forEach(b=>b.onclick=()=>{timelineMetric=b.dataset.timeline;renderTimelineControls();renderTimeline()});
  }
  function renderTimeline(){
    if(!timelineBox||!managerSelect)return;
    const manager=managerSelect.value;
    const metric=timelineMetrics[timelineMetric];
    const years=Object.keys(DATA.regular[manager]?.yearly||{}).filter(y=>DATA.regular[manager].yearly[y]&&Number.isFinite(metric.get(manager,y))).sort((a,b)=>a-b);
    if(!years.length){timelineBox.innerHTML='';return}
    const W=760,H=270,p={l:52,r:22,t:28,b:38},iw=W-p.l-p.r,ih=H-p.t-p.b;
    const x=i=>p.l+(years.length===1?iw/2:i*iw/(years.length-1));
    const y=v=>metric.invert?p.t+(v-metric.min)/(metric.max-metric.min)*ih:p.t+(metric.max-v)/(metric.max-metric.min)*ih;
    const grids=metric.ticks.map(t=>{const yy=y(t);return `<line class="timeline-grid" x1="${p.l}" x2="${W-p.r}" y1="${yy}" y2="${yy}"/><text class="timeline-axis" x="${p.l-8}" y="${yy+3}" text-anchor="end">${metric.axis(t)}</text>`}).join('');
    const pts=years.map((yr,i)=>({yr,v:metric.get(manager,yr),x:x(i)})).map(q=>({...q,y:y(q.v)}));
    const path=pts.map((q,i)=>`${i?'L':'M'} ${q.x.toFixed(1)} ${q.y.toFixed(1)}`).join(' ');
    const dots=pts.map(q=>`<circle class="timeline-dot" cx="${q.x}" cy="${q.y}" r="5"><title>${q.yr}: ${metric.fmt(q.v)}</title></circle>`).join('');
    const labels=pts.map(q=>`<text class="timeline-label" x="${q.x}" y="${Math.max(13,q.y-11)}">${metric.fmt(q.v)}</text>`).join('');
    const yearLabels=pts.map(q=>`<text class="timeline-axis" x="${q.x}" y="${H-12}" text-anchor="middle">${q.yr}</text>`).join('');
    timelineBox.innerHTML=`<div class="timeline-wrap"><svg class="timeline-svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="${metric.label} timeline for ${esc(manager)}">${grids}<path class="timeline-line" d="${path}"/>${dots}${labels}${yearLabels}</svg></div>`;
  }
  renderTimelineControls();
  renderTimeline();
  if(managerSelect)managerSelect.addEventListener('change',renderTimeline);
})();
