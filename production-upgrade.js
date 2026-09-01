(()=>{
  const D=window.DATA,OUT=window.DRAFT_OUTCOMES||{},C=window.COLORS||{};
  if(!D)return;
  const current=new Set(D.currentManagers||[]);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const norm=s=>String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]/g,'');
  const record=r=>{if(!r||!String(r).includes('-'))return{w:0,l:0};const [w,l]=String(r).split('-').map(Number);return{w:w||0,l:l||0}};
  const fmt=n=>Math.round(Number(n)||0).toLocaleString('en-US');
  const color=m=>C[m]||'#9b8257';
  const legacyOrder=Object.entries(D.legacy).sort((a,b)=>b[1].score-a[1].score);
  const active=[...current];

  function activeYears(m){return Object.entries(D.regular[m]?.yearly||{}).filter(([,r])=>r).map(([y])=>+y).sort((a,b)=>a-b)}
  function cumulative(m,year){let w=0,l=0;Object.entries(D.regular[m]?.yearly||{}).forEach(([y,r])=>{if(+y<=year&&r){const x=record(r);w+=x.w;l+=x.l}});return{w,l}}
  function legacyAt(m,year){
    const years=activeYears(m);if(!years.length||year<years[0])return null;
    if(year>=years.at(-1)&&Number.isFinite(D.legacy[m]?.score))return D.legacy[m].score;
    const reg=cumulative(m,year),service=years.filter(y=>y<=year).length;
    let pw=0;Object.entries(D.playoffs[m]?.yearly||{}).forEach(([y,r])=>{if(+y<=year&&r)pw+=record(r).w});
    const titles=(D.champions||[]).filter(c=>c.manager===m&&+c.year<=year).length;
    const pct=(reg.w+reg.l)?reg.w/(reg.w+reg.l):0;
    return pct*(1+.05*service+.05*pw+.50*titles)*1000;
  }
  function rankAt(m,year){const v=legacyAt(m,year);if(!Number.isFinite(v))return null;const vals=Object.keys(D.regular).map(n=>legacyAt(n,year)).filter(Number.isFinite).sort((a,b)=>b-a);return 1+vals.filter(x=>x>v+1e-9).length}
  function currentRank(m){const i=legacyOrder.findIndex(([n])=>n===m);return i<0?null:i+1}

  function renderProfile(m){
    const box=document.getElementById('managerProfile'),r=D.regular[m],l=D.legacy[m];if(!box||!r||!l)return;
    document.documentElement.style.setProperty('--mc',color(m));
    const rank=currentRank(m);
    box.innerHTML=`<div class="manager-head"><h2>${esc(m)}</h2><span class="badge ${current.has(m)?'':'former'}">${current.has(m)?'Active':'Former'}</span></div><div class="dp-legacy-hero"><div class="dp-legacy-label">Legacy Score</div><b class="dp-legacy-score">${fmt(l.score)}</b></div><div class="stat-grid dp-profile-stats"><div class="stat"><small>Legacy Rank</small><b>${rank?`#${rank}`:'—'}</b></div><div class="stat"><small>Reg. Record</small><b>${esc(r.total||'—')}</b></div><div class="stat"><small>Championships</small><b>${l.titles??0}</b></div></div>`;
  }

  let timelineMode='legacy';
  function drawTimeline(m){
    const controls=document.getElementById('timelineMetricBtns'),box=document.getElementById('managerTimeline');if(!controls||!box)return;
    const modes=[['legacy','Legacy'],['rank','Rank'],['record','Reg. Record']];
    controls.className='dp-timeline-controls';
    controls.innerHTML=modes.map(([k,l])=>`<button data-dp="${k}" class="${timelineMode===k?'on':''}">${l}</button>`).join('');
    controls.querySelectorAll('button').forEach(b=>b.onclick=()=>{timelineMode=b.dataset.dp;drawTimeline(m)});
    const years=activeYears(m);if(!years.length){box.innerHTML='';return}
    const data=years.map(y=>{
      if(timelineMode==='legacy'){const v=legacyAt(m,y);return{year:y,v,label:fmt(v)}}
      if(timelineMode==='rank'){const v=rankAt(m,y);return{year:y,v,label:`#${v}`}}
      const x=cumulative(m,y);return{year:y,v:x.w,label:`${x.w}-${x.l}`};
    }).filter(x=>Number.isFinite(x.v));
    const W=760,H=260,p={l:52,r:22,t:27,b:38},iw=W-p.l-p.r,ih=H-p.t-p.b;
    let min=0,max=Math.max(...data.map(x=>x.v)),ticks=[];
    if(timelineMode==='rank'){min=1;max=Math.max(2,max);ticks=[...new Set([1,Math.max(1,Math.ceil((1+max)/2)),max])]}else{const base=timelineMode==='legacy'?250:5;const step=Math.max(base,Math.ceil((max/4)/base)*base);max=Math.max(step,Math.ceil(max/step)*step);ticks=[0,step,step*2,step*3,step*4].filter(v=>v<=max);if(!ticks.includes(max))ticks.push(max)}
    const x=i=>p.l+(data.length===1?iw/2:i*iw/(data.length-1));
    const y=v=>timelineMode==='rank'?p.t+(v-min)/Math.max(1,max-min)*ih:p.t+(max-v)/Math.max(1,max-min)*ih;
    const grid=ticks.map(t=>`<line class="dp-grid" x1="${p.l}" x2="${W-p.r}" y1="${y(t)}" y2="${y(t)}"/><text class="dp-axis" x="${p.l-8}" y="${y(t)+3}" text-anchor="end">${timelineMode==='legacy'?fmt(t):timelineMode==='rank'?`#${t}`:t}</text>`).join('');
    const pts=data.map((d,i)=>({...d,x:x(i),y:y(d.v)})),path=pts.map((q,i)=>`${i?'L':'M'} ${q.x.toFixed(1)} ${q.y.toFixed(1)}`).join(' '),area=timelineMode==='rank'?'':`${path} L ${pts.at(-1).x.toFixed(1)} ${(p.t+ih).toFixed(1)} L ${pts[0].x.toFixed(1)} ${(p.t+ih).toFixed(1)} Z`;
    box.innerHTML=`<div class="dp-chart-wrap"><svg class="dp-chart-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Career timeline for ${esc(m)}">${grid}${area?`<path class="dp-area" d="${area}"/>`:''}<path class="dp-series" d="${path}"/>${pts.map(q=>`<circle class="dp-dot" cx="${q.x}" cy="${q.y}" r="4.5"/><text class="dp-point-label" x="${q.x}" y="${Math.max(12,q.y-10)}">${q.label}</text><text class="dp-axis" x="${q.x}" y="${H-12}" text-anchor="middle">${q.year}</text>`).join('')}</svg></div>`;
  }

  function statFor(year,player){const base=norm(player),keys=[base,base.replace(/lll$/,'iii'),base.replace(/ii$/,'iii')];for(const k of keys){const hit=OUT[`${year}|${k}`];if(hit)return hit}return null}
  function picksFor(m){const out=[];Object.entries(D.drafts||{}).forEach(([ys,b])=>(b.rounds||[]).forEach((r,ri)=>(r||[]).forEach(p=>{if(p.owner===m&&p.player)out.push({year:+ys,round:ri+1,slot:p.slot,player:p.player,stat:statFor(+ys,p.player)})})));return out}
  function eligible(m){return picksFor(m).filter(p=>p.year<=2025&&p.stat&&p.stat.excluded!=='veteran'&&Number.isFinite(p.stat.ppg)&&p.stat.pos)}
  const mean=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:null;
  function draftValue(m,tagged){const mine=eligible(m);if(!mine.length)return null;const bucket=p=>Math.min(4,p.round),d=mine.map(p=>{let peers=tagged.filter(x=>x.manager!==m&&x.stat.pos===p.stat.pos&&bucket(x)===bucket(p));if(peers.length<2)peers=tagged.filter(x=>x.manager!==m&&x.stat.pos===p.stat.pos);if(peers.length<2)peers=tagged.filter(x=>x.manager!==m&&bucket(x)===bucket(p));if(!peers.length)peers=tagged.filter(x=>x.manager!==m);const exp=mean(peers.map(x=>x.stat.ppg));return Number.isFinite(exp)?p.stat.ppg-exp:null}).filter(Number.isFinite);return mean(d)}

  function renderRookieAnalytics(m){
    const picksBox=document.getElementById('managerPicks');if(!picksBox)return;
    let box=document.getElementById('rookieAnalytics');if(!box){box=document.createElement('div');box.id='rookieAnalytics';box.className='dp-rookie-analytics';picksBox.before(box)}
    const picks=picksFor(m).filter(p=>p.year<=2025&&p.stat&&p.stat.excluded!=='veteran');
    const yearly=[...new Set(picks.map(p=>p.year))].sort((a,b)=>a-b).map(year=>({year,points:picks.filter(p=>p.year===year).reduce((s,p)=>s+(Number.isFinite(p.stat?.points)?p.stat.points:0),0)}));
    const max=Math.max(1,...yearly.map(x=>x.points));
    const bars=yearly.length?yearly.map(x=>`<div class="dp-rookie-col"><div class="dp-rookie-value">${fmt(x.points)}</div><div class="dp-rookie-bar" style="height:${Math.max(3,x.points/max*100)}%"></div><div class="dp-rookie-year">${x.year}</div></div>`).join(''):'<div class="empty">No scored rookie classes yet.</div>';
    const tagged=active.flatMap(n=>eligible(n).map(p=>({...p,manager:n}))),metrics=active.map(n=>({m:n,v:draftValue(n,tagged)})).filter(x=>Number.isFinite(x.v)),mine=metrics.find(x=>x.m===m),sorted=metrics.map(x=>x.v).sort((a,b)=>b-a),rank=mine?1+sorted.filter(v=>v>mine.v+1e-9).length:null,pctRank=rank&&sorted.length>1?Math.max(5,(sorted.length-rank)/(sorted.length-1)*100):0;
    box.innerHTML=`<div class="dp-rookie-inner"><div class="dp-analytics-title">Rookie Points</div><div class="dp-rookie-chart">${bars}</div><p class="dp-rookie-note">Career fantasy points generated by each drafted rookie class through 2025.</p><div class="dp-draft-value"><h4>Pos + Round Draft Value</h4><p>Compares each rookie pick to league averages at the same position and round. Higher is better.</p><div class="dp-draft-rank"><span>Rank</span><strong>${current.has(m)&&rank?rank:'—'}</strong><span>${current.has(m)?`of ${metrics.length} active`:'Former manager · not ranked'}</span>${mine?`<span class="dp-draft-score">${mine.v>=0?'+':''}${mine.v.toFixed(2)} adj PPG/pick</span>`:''}</div><div class="dp-rankbar"><span style="width:${current.has(m)?pctRank:0}%"></span></div></div></div>`;
  }

  let roundFilter='all';
  function renderDenseDraft(){
    const sel=document.getElementById('draftYear'),box=document.getElementById('draftBoard');if(!sel||!box)return;const b=D.drafts?.[String(sel.value)];if(!b)return;
    const rounds=b.rounds||[],total=rounds.reduce((s,r)=>s+(r?.length||0),0),teams=new Set(rounds.flat().map(p=>p?.owner).filter(Boolean)).size,filters=['all',...rounds.map((_,i)=>String(i+1))];
    box.className='draft-rounds';
    const visible=rounds.map((r,i)=>({r,i})).filter(x=>roundFilter==='all'||String(x.i+1)===roundFilter);
    box.innerHTML=`<div class="dp-draft-summary"><span>${total} picks</span><span>${rounds.length} rounds</span><span>${teams} teams</span></div><div class="dp-round-tabs">${filters.map(f=>`<button data-round="${f}" class="${roundFilter===f?'on':''}">${f==='all'?'All Rounds':`R${f}`}</button>`).join('')}</div>${visible.map(({r,i})=>`<section class="dp-compact-round"><h3>Round ${i+1}<span>${r.length} picks</span></h3>${r.map(p=>`<div class="dp-compact-row"><div class="dp-compact-pick">${i+1}.${String(p.slot).padStart(2,'0')}</div><div class="dp-compact-player">${esc(p.player||'—')}</div><div class="dp-compact-owner" style="--owner-color:${color(p.owner)}">${esc(p.owner||'Unknown')}</div></div>`).join('')}</section>`).join('')}`;
    box.querySelectorAll('.dp-round-tabs button').forEach(btn=>btn.onclick=()=>{roundFilter=btn.dataset.round;renderDenseDraft()});
  }

  const managerSelect=document.getElementById('managerSelect');
  function refreshManager(){const m=managerSelect?.value||'Seth Miller';renderProfile(m);drawTimeline(m);renderRookieAnalytics(m)}
  if(managerSelect)managerSelect.addEventListener('change',()=>setTimeout(refreshManager,0));
  const draftYear=document.getElementById('draftYear');if(draftYear)draftYear.addEventListener('change',()=>{roundFilter='all';setTimeout(renderDenseDraft,0)});
  refreshManager();renderDenseDraft();
})();
