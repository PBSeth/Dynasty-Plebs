(()=>{
  const D=window.DATA, OUT=window.DRAFT_OUTCOMES||{}, C=window.COLORS||{};
  if(!D)return;
  const current=new Set(D.currentManagers||[]);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const norm=s=>String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]/g,'');
  const record=r=>{if(!r||!String(r).includes('-'))return{w:0,l:0};const [w,l]=String(r).split('-').map(Number);return{w:w||0,l:l||0}};
  const winDec=v=>Number.isFinite(Number(v))?Number(v).toFixed(3).replace(/^0/,''):'—';
  const fmt=n=>Math.round(Number(n)||0).toLocaleString('en-US');
  const mean=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:null;
  const color=m=>C[m]||'#9b8257';

  function renderWall(){
    const box=document.getElementById('kpis'); if(!box)return;
    box.classList.add('dp-wall-grid');
    const regs=Object.entries(D.regular||{});
    const maxWins=Math.max(...regs.map(([,r])=>record(r.total).w));
    const winLeaders=regs.filter(([,r])=>record(r.total).w===maxWins).map(([m])=>m);
    const eligible=regs.filter(([,r])=>Object.values(r.yearly||{}).filter(Boolean).length>=3&&Number.isFinite(r.winPct));
    const bestPct=Math.max(...eligible.map(([,r])=>r.winPct));
    const pctLeaders=eligible.filter(([,r])=>Math.abs(r.winPct-bestPct)<1e-9).map(([m])=>m);
    const maxPlay=Math.max(...Object.values(D.formulaInputs||{}).map(x=>x.playoffWins||0));
    const playLeaders=Object.entries(D.formulaInputs||{}).filter(([,x])=>(x.playoffWins||0)===maxPlay).map(([m])=>m);
    const maxTitles=Math.max(...Object.values(D.legacy||{}).map(x=>x.titles||0));
    const titleLeaders=Object.entries(D.legacy||{}).filter(([,x])=>(x.titles||0)===maxTitles).map(([m])=>m);
    const wall=[
      ['Highest Team PPG','150.9','Travis Page','2025'],
      ['Lowest Team PPG','75.2','Ryan Lipkin','2024'],
      ['Best Margin / Game','+33.9','Matthew Piontek','2021'],
      ['Worst Margin / Game','-45.8','Travis Page','2021'],
      ['Career Reg. Wins',maxWins,winLeaders.join(' & '),'All-Time'],
      ['Career Win %',winDec(bestPct),pctLeaders.join(' & '),'3+ seasons'],
      ['Playoff Wins',maxPlay,playLeaders.join(' & '),'All-Time'],
      ['Championships',maxTitles,titleLeaders.join(' & '),'All-Time']
    ];
    box.innerHTML=wall.map(([l,v,n,s])=>`<div class="kpi"><small>${esc(l)}</small><b>${esc(v)}</b><span><strong>${esc(n)}</strong>${s?`<em>${esc(s)}</em>`:''}</span></div>`).join('');
  }

  let historyMetric='record';
  const historyMetrics={
    record:{label:'Wins · Win %',get:m=>record(D.regular[m]?.total).w,sort:(a,b)=>record(D.regular[b]?.total).w-record(D.regular[a]?.total).w,fmt:m=>`${record(D.regular[m]?.total).w} W · ${winDec(D.regular[m]?.winPct)}`},
    legacy:{label:'Legacy Score',get:m=>D.legacy[m]?.score??0,sort:(a,b)=>(D.legacy[b]?.score??0)-(D.legacy[a]?.score??0),fmt:m=>fmt(D.legacy[m]?.score)},
    avg:{label:'Avg Finish',get:m=>Math.max(0,13-(D.legacy[m]?.avg??13)),sort:(a,b)=>(D.legacy[a]?.avg??99)-(D.legacy[b]?.avg??99),fmt:m=>Number.isFinite(D.legacy[m]?.avg)?D.legacy[m].avg.toFixed(2):'—'}
  };
  function renderHistory(){
    const btns=document.getElementById('historyMetricBtns'),chart=document.getElementById('historyChart'); if(!btns||!chart)return;
    btns.innerHTML=Object.entries(historyMetrics).map(([k,x])=>`<button class="${historyMetric===k?'on':''}" data-fix-history="${k}">${x.label}</button>`).join('');
    btns.querySelectorAll('button').forEach(b=>b.onclick=()=>{historyMetric=b.dataset.fixHistory;renderHistory()});
    const x=historyMetrics[historyMetric], managers=Object.keys(D.regular||{}).sort(x.sort), max=Math.max(1,...Object.keys(D.regular||{}).map(x.get));
    chart.innerHTML=managers.map((m,i)=>`<div class="archive-bar"><strong>${i+1}. ${esc(m)}</strong><div class="archive-track"><div class="archive-fill" style="width:${Math.max(3,x.get(m)/max*100)}%"></div></div><div class="archive-value">${esc(x.fmt(m))}</div></div>`).join('');
  }

  function activeYears(m){return Object.entries(D.regular[m]?.yearly||{}).filter(([,r])=>r).map(([y])=>+y).sort((a,b)=>a-b)}
  function cumulative(m,year){let w=0,l=0;Object.entries(D.regular[m]?.yearly||{}).forEach(([y,r])=>{if(+y<=year&&r){const x=record(r);w+=x.w;l+=x.l}});return{w,l}}
  function legacyAt(m,year){
    const years=activeYears(m); if(!years.length||year<years[0])return null;
    if(year>=years.at(-1)&&Number.isFinite(D.legacy[m]?.score))return D.legacy[m].score;
    const reg=cumulative(m,year), service=years.filter(y=>y<=year).length;
    let pw=0;Object.entries(D.playoffs[m]?.yearly||{}).forEach(([y,r])=>{if(+y<=year&&r)pw+=record(r).w});
    const titles=(D.champions||[]).filter(c=>c.manager===m&&+c.year<=year).length;
    const pct=(reg.w+reg.l)?reg.w/(reg.w+reg.l):0;
    return pct*(1+.05*service+.05*pw+.50*titles)*1000;
  }
  function rankAt(m,year){const v=legacyAt(m,year);if(!Number.isFinite(v))return null;const vals=Object.keys(D.regular||{}).map(n=>legacyAt(n,year)).filter(Number.isFinite).sort((a,b)=>b-a);return 1+vals.filter(x=>x>v+1e-9).length}

  let timelineMode='legacy';
  function renderTimeline(m){
    const controls=document.getElementById('timelineMetricBtns'),box=document.getElementById('managerTimeline'); if(!controls||!box)return;
    const modes=[['legacy','Legacy'],['rank','Rank'],['record','Reg. Record']];
    controls.className='dp-timeline-controls';
    controls.innerHTML=modes.map(([k,l])=>`<button data-fix-timeline="${k}" class="${timelineMode===k?'on':''}">${l}</button>`).join('');
    controls.querySelectorAll('button').forEach(b=>b.onclick=()=>{timelineMode=b.dataset.fixTimeline;renderTimeline(m)});
    const years=activeYears(m); if(!years.length){box.innerHTML='';return}
    const data=years.map(y=>{
      if(timelineMode==='legacy'){const v=legacyAt(m,y);return{year:y,v,label:fmt(v)}}
      if(timelineMode==='rank'){const v=rankAt(m,y);return{year:y,v,label:`#${v}`}}
      const r=cumulative(m,y);return{year:y,v:r.w,label:`${r.w}-${r.l}`};
    }).filter(x=>Number.isFinite(x.v));
    if(!data.length){box.innerHTML='';return}
    const W=760,H=240,p={l:60,r:18,t:19,b:34},iw=W-p.l-p.r,ih=H-p.t-p.b;
    const vals=data.map(x=>x.v), rawMin=Math.min(...vals), rawMax=Math.max(...vals), range=Math.max(1,rawMax-rawMin), pad=Math.max(1,range*.10);
    let min,max,invert=false;
    if(timelineMode==='rank'){min=Math.max(1,rawMin-.4);max=rawMax+.6;invert=true}else{min=Math.max(0,rawMin-pad);max=rawMax+pad}
    if(max<=min)max=min+1;
    const x=i=>p.l+(data.length===1?iw/2:i*iw/(data.length-1));
    const y=v=>invert?p.t+(v-min)/(max-min)*ih:p.t+(max-v)/(max-min)*ih;
    const tickVals=[0,.25,.5,.75,1].map(t=>min+(max-min)*t);
    const axisFmt=v=>timelineMode==='rank'?`#${Math.max(1,Math.round(v))}`:fmt(v);
    const grid=tickVals.map(t=>`<line class="dp-grid" x1="${p.l}" x2="${W-p.r}" y1="${y(t)}" y2="${y(t)}"/><text class="dp-axis" x="${p.l-9}" y="${y(t)+4}" text-anchor="end">${axisFmt(t)}</text>`).join('');
    const pts=data.map((d,i)=>({...d,x:x(i),y:y(d.v)})), path=pts.map((q,i)=>`${i?'L':'M'} ${q.x.toFixed(1)} ${q.y.toFixed(1)}`).join(' ');
    const area=timelineMode==='rank'?'':`${path} L ${pts.at(-1).x.toFixed(1)} ${(p.t+ih).toFixed(1)} L ${pts[0].x.toFixed(1)} ${(p.t+ih).toFixed(1)} Z`;
    box.innerHTML=`<div class="dp-chart-wrap"><svg class="dp-chart-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Career timeline for ${esc(m)}">${grid}${area?`<path class="dp-area" d="${area}"/>`:''}<path class="dp-series" d="${path}"/>${pts.map(q=>`<circle class="dp-dot" cx="${q.x}" cy="${q.y}" r="5.5"/><text class="dp-point-label" x="${q.x}" y="${Math.max(14,q.y-11)}">${q.label}</text><text class="dp-axis dp-year-axis" x="${q.x}" y="${H-10}" text-anchor="middle">${q.year}</text>`).join('')}</svg></div>`;
  }

  function statFor(year,player){const base=norm(player),keys=[base,base.replace(/lll$/,'iii'),base.replace(/ii$/,'iii')];for(const k of keys){const hit=OUT[`${year}|${k}`];if(hit)return hit}return null}
  function picksFor(m){const out=[];Object.entries(D.drafts||{}).forEach(([ys,b])=>(b.rounds||[]).forEach((r,ri)=>(r||[]).forEach(p=>{if(p.owner===m&&p.player)out.push({year:+ys,round:ri+1,slot:p.slot,player:p.player,stat:statFor(+ys,p.player)})})));return out}
  const eligible=m=>picksFor(m).filter(p=>p.year<=2025&&p.stat&&p.stat.excluded!=='veteran'&&Number.isFinite(p.stat.ppg)&&p.stat.pos);
  const bucket=p=>Math.min(4,Number(p.round)||4);
  function expected(p,manager,tagged){
    let peers=tagged.filter(x=>x.manager!==manager&&x.stat.pos===p.stat.pos&&bucket(x)===bucket(p));
    if(peers.length<2)peers=tagged.filter(x=>x.manager!==manager&&x.stat.pos===p.stat.pos);
    if(peers.length<2)peers=tagged.filter(x=>x.manager!==manager&&bucket(x)===bucket(p));
    if(!peers.length)peers=tagged.filter(x=>x.manager!==manager);
    return mean(peers.map(x=>x.stat.ppg));
  }
  function delta(p,m,tagged){const e=expected(p,m,tagged);return Number.isFinite(e)?p.stat.ppg-e:null}
  function avgDelta(d,m,tagged){return mean(d.map(p=>delta(p,m,tagged)).filter(Number.isFinite))}

  function renderPicks(m){
    const box=document.getElementById('managerPicks'); if(!box)return;
    const picks=picksFor(m).filter(p=>p.stat?.excluded!=='veteran').sort((a,b)=>b.year-a.year||a.round-b.round||a.slot-b.slot);
    const grouped=picks.reduce((a,p)=>((a[p.year]??=[]).push(p),a),{});
    box.className='draft-rounds dp-manager-picks';
    box.innerHTML=picks.length?Object.entries(grouped).sort((a,b)=>b[0]-a[0]).map(([year,ps])=>`<div class="round"><h3>${year}</h3><div class="pick-grid">${ps.map(p=>`<div class="pick" style="--pc:${color(m)}"><small class="dp-pick-meta"><span>${p.round}.${String(p.slot).padStart(2,'0')}</span>${Number.isFinite(p.stat?.ppg)?`<span class="ppg-value">${p.stat.ppg.toFixed(1)} PPG</span>`:'<span class="ppg-value muted">—</span>'}</small><b>${esc(p.player)}</b>${p.stat?.pos?`<span class="dp-pick-pos">${esc(p.stat.pos)}</span>`:''}</div>`).join('')}</div></div>`).join(''):'<div class="empty">No recorded rookie picks.</div>';
  }

  function renderRookieAnalytics(m){
    const picksBox=document.getElementById('managerPicks'); if(!picksBox)return;
    let box=document.getElementById('rookieAnalytics'); if(!box){box=document.createElement('div');box.id='rookieAnalytics';box.className='dp-rookie-analytics';picksBox.before(box)}
    const scored=picksFor(m).filter(p=>p.year<=2025&&p.stat&&p.stat.excluded!=='veteran'&&Number.isFinite(p.stat.ppg));
    const yearly=[...new Set(scored.map(p=>p.year))].sort((a,b)=>a-b).map(year=>({year,points:scored.filter(p=>p.year===year).reduce((s,p)=>s+(Number.isFinite(p.stat?.points)?p.stat.points:0),0)}));
    const maxPoints=Math.max(1,...yearly.map(x=>x.points));
    const bars=yearly.length?yearly.map(x=>`<div class="dp-rookie-col"><div class="dp-rookie-value">${fmt(x.points)}</div><div class="dp-rookie-bar" style="height:${Math.max(3,x.points/maxPoints*100)}%"></div><div class="dp-rookie-year">${x.year}</div></div>`).join(''):'<div class="empty">No scored rookie classes yet.</div>';

    const active=[...current], tagged=active.flatMap(n=>eligible(n).map(p=>({...p,manager:n})));
    const managerMetrics=active.map(n=>{const d=eligible(n);if(!d.length)return null;const rounds={};[1,2,3,4].forEach(r=>rounds[r]=avgDelta(d.filter(p=>bucket(p)===r),n,tagged));return{m:n,avg:mean(d.map(p=>p.stat.ppg)),adj:avgDelta(d,n,tagged),rounds,n:d.length}}).filter(Boolean);
    const mineD=eligible(m), isActive=current.has(m), me=isActive?managerMetrics.find(x=>x.m===m):{m,avg:mean(mineD.map(p=>p.stat.ppg)),adj:avgDelta(mineD,m,tagged),rounds:{},n:mineD.length};
    if(me&&!isActive)[1,2,3,4].forEach(r=>me.rounds[r]=avgDelta(mineD.filter(p=>bucket(p)===r),m,tagged));
    const rank=(value,values)=>{const valid=values.filter(Number.isFinite).sort((a,b)=>b-a);if(!Number.isFinite(value)||!valid.length)return null;return{r:1+valid.filter(v=>v>value+1e-9).length,n:valid.length}};
    const rankLine=(value,values)=>{if(!isActive)return'Former manager · not ranked';const x=rank(value,values);return x?`Rank ${x.r} of ${x.n} active`:'No active-manager rank'};
    const withDelta=mineD.map(p=>({...p,adj:delta(p,m,tagged)})).filter(p=>Number.isFinite(p.adj)),best=[...withDelta].sort((a,b)=>b.adj-a.adj)[0],worst=[...withDelta].sort((a,b)=>a.adj-b.adj)[0];
    const overallAvg=me?.avg, overallAdj=me?.adj;
    const roundCards=[1,2,3,4].map(r=>{const d=mineD.filter(p=>bucket(p)===r),raw=mean(d.map(p=>p.stat.ppg)),adj=avgDelta(d,m,tagged),label=r===4?'Round 4+':`Round ${r}`;return`<div class="dp-intel-card"><small>${label} Avg PPG</small><b>${Number.isFinite(raw)?raw.toFixed(1):'—'}</b><strong>${rankLine(adj,managerMetrics.map(x=>x.rounds[r]))}</strong><span>${Number.isFinite(adj)?`${adj>=0?'+':''}${adj.toFixed(1)} adjusted PPG`:''}${Number.isFinite(adj)&&d.length?' · ':''}${d.length} scored pick${d.length===1?'':'s'}</span></div>`}).join('');
    const intel=`<div class="dp-draft-intel"><div class="dp-intel-card"><small>Avg PPG / Pick</small><b>${Number.isFinite(overallAvg)?overallAvg.toFixed(1):'—'}</b><strong>${isActive?'Raw scoring average':'Former manager · not ranked'}</strong><span>${me?.n||0} eligible scored picks</span></div><div class="dp-intel-card"><small>Pos + Round Draft Value</small><b>${Number.isFinite(overallAdj)?`${overallAdj>=0?'+':''}${overallAdj.toFixed(1)}`:'—'}</b><strong>${rankLine(overallAdj,managerMetrics.map(x=>x.adj))}</strong><span>Adjusted PPG per pick vs position + round peers</span></div><div class="dp-intel-card"><small>Best Adjusted Pick</small><b class="dp-name-value">${best?esc(best.player):'—'}</b><strong>${best?`${best.stat.ppg.toFixed(1)} PPG`:'No eligible pick'}</strong><span>${best?`${best.year} · ${best.round}.${String(best.slot).padStart(2,'0')} · ${best.adj>=0?'+':''}${best.adj.toFixed(1)} adj`:''}</span></div><div class="dp-intel-card"><small>Worst Adjusted Pick</small><b class="dp-name-value">${worst?esc(worst.player):'—'}</b><strong>${worst?`${worst.stat.ppg.toFixed(1)} PPG`:'No eligible pick'}</strong><span>${worst?`${worst.year} · ${worst.round}.${String(worst.slot).padStart(2,'0')} · ${worst.adj>=0?'+':''}${worst.adj.toFixed(1)} adj`:''}</span></div>${roundCards}</div>`;
    box.innerHTML=`<div class="dp-rookie-inner"><div class="dp-analytics-title">Rookie Points</div><div class="dp-rookie-chart">${bars}</div><p class="dp-rookie-note">Career fantasy points generated by each drafted rookie class through 2025.</p><div class="dp-efficiency-title">Draft Efficiency</div>${intel}</div>`;
  }

  function renderManagerFix(){const m=document.getElementById('managerSelect')?.value||'Seth Miller';renderTimeline(m);renderRookieAnalytics(m);renderPicks(m)}
  renderWall();renderHistory();renderManagerFix();
  const managerSelect=document.getElementById('managerSelect');
  if(managerSelect)managerSelect.addEventListener('change',()=>setTimeout(renderManagerFix,0));
})();
