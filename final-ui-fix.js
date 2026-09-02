(()=>{
  const D=window.DATA;if(!D)return;
  const current=new Set(D.currentManagers||[]);
  const OUT=window.DRAFT_OUTCOMES||{};
  const PRIMARY='#b88b3e';
  const norm=s=>String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]/g,'');
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt=n=>Math.round(Number(n)||0).toLocaleString('en-US');

  const style=document.createElement('style');
  style.textContent=`
    #managerTimeline .dp-series{stroke:${PRIMARY}!important}
    #managerTimeline .dp-area{fill:${PRIMARY}!important}
    #managerTimeline .dp-dot:not(.champ){stroke:${PRIMARY}!important}
    #managerTimeline .dp-pf-line{stroke:${PRIMARY}!important}
    #managerTimeline .dp-pf-point{stroke:${PRIMARY}!important}
  `;
  document.head.appendChild(style);

  function fixDraftOwnerMarkers(){
    document.querySelectorAll('#draftBoard .dp-compact-owner').forEach(node=>{
      const owner=node.textContent.trim();
      if(owner&&!current.has(owner))node.style.setProperty('--owner-color','#111111');
    });
  }

  function statFor(year,player){
    const base=norm(player),keys=[base,base.replace(/lll$/,'iii'),base.replace(/ii$/,'iii')];
    for(const k of keys){
      const hit=OUT[`${year}|${k}`];
      if(hit)return hit;
    }
    return null;
  }

  function rookieClasses(){
    const classes=[];
    Object.keys(D.regular||{}).forEach(manager=>{
      Object.entries(D.drafts||{}).forEach(([year,board])=>{
        if(+year>2025)return;
        const picks=(board.rounds||[]).flat().filter(p=>p?.owner===manager&&p.player);
        const scored=picks.map(p=>statFor(+year,p.player)).filter(stat=>stat&&stat.excluded!=='veteran'&&Number.isFinite(stat.ppg));
        if(!scored.length)return;
        const points=scored.reduce((sum,stat)=>sum+(Number.isFinite(stat.points)?stat.points:0),0);
        classes.push({manager,year:+year,points});
      });
    });
    return classes;
  }

  function rookieClassRecords(){
    const classes=rookieClasses();
    if(!classes.length)return null;
    const top=Math.max(...classes.map(x=>x.points));
    const topClasses=classes.filter(x=>Math.abs(x.points-top)<1e-9);
    const byManager={};
    classes.forEach(x=>(byManager[x.manager]??=[]).push(x.points));
    const averages=Object.entries(byManager).map(([manager,vals])=>({manager,avg:vals.reduce((a,b)=>a+b,0)/vals.length,classes:vals.length}));
    const topAvg=Math.max(...averages.map(x=>x.avg));
    const topAverages=averages.filter(x=>Math.abs(x.avg-topAvg)<1e-9);
    return{top,topClasses,topAvg,topAverages};
  }

  function rookieManagerRows(){
    const classes=rookieClasses(),byManager={};
    classes.forEach(x=>(byManager[x.manager]??=[]).push(x));
    return Object.keys(D.regular||{}).map(manager=>{
      const rows=byManager[manager]||[];
      if(!rows.length)return{manager,best:null,bestYears:[],avg:null,classes:0};
      const best=Math.max(...rows.map(x=>x.points));
      const bestYears=rows.filter(x=>Math.abs(x.points-best)<1e-9).map(x=>x.year).sort((a,b)=>a-b);
      const avg=rows.reduce((sum,x)=>sum+x.points,0)/rows.length;
      return{manager,best,bestYears,avg,classes:rows.length};
    });
  }

  function addWallRecords(){
    const wall=document.getElementById('kpis');
    if(!wall||wall.dataset.rookieClassRecords==='1')return;
    const r=rookieClassRecords();
    if(!r)return;
    const highNames=r.topClasses.map(x=>x.manager).join(' & ');
    const highYears=[...new Set(r.topClasses.map(x=>x.year))].join(' / ');
    const avgNames=r.topAverages.map(x=>x.manager).join(' & ');
    const avgClasses=[...new Set(r.topAverages.map(x=>x.classes))];
    const avgSub=avgClasses.length===1?`${avgClasses[0]} class${avgClasses[0]===1?'':'es'}`:'Career';
    wall.insertAdjacentHTML('beforeend',
      `<div class="kpi"><small>Highest-Scoring Rookie Class</small><b>${fmt(r.top)}</b><span><strong>${esc(highNames)}</strong><em>${esc(highYears)}</em></span></div>`+
      `<div class="kpi"><small>Avg Rookie Points / Class</small><b>${r.topAvg.toFixed(1)}</b><span><strong>${esc(avgNames)}</strong><em>${esc(avgSub)}</em></span></div>`
    );
    wall.dataset.rookieClassRecords='1';
  }

  let rookieHistoryMode=null;
  function ensureHistoryButtons(){
    const controls=document.getElementById('historyMetricBtns');
    if(!controls)return;
    const defs=[['bestClass','Best Rookie Class'],['avgClass','Avg Rookie Pts/Class']];
    defs.forEach(([key,label])=>{
      if(controls.querySelector(`[data-rookie-history="${key}"]`))return;
      const b=document.createElement('button');
      b.type='button';
      b.dataset.rookieHistory=key;
      b.textContent=label;
      controls.appendChild(b);
    });
    if(rookieHistoryMode){
      controls.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.rookieHistory===rookieHistoryMode));
    }
  }

  function renderRookieHistory(mode){
    const controls=document.getElementById('historyMetricBtns'),chart=document.getElementById('historyChart');
    if(!controls||!chart)return;
    const rows=rookieManagerRows().filter(x=>mode==='bestClass'?Number.isFinite(x.best):Number.isFinite(x.avg));
    rows.sort((a,b)=>mode==='bestClass'?(b.best-a.best||a.manager.localeCompare(b.manager)):(b.avg-a.avg||a.manager.localeCompare(b.manager)));
    const max=Math.max(1,...rows.map(x=>mode==='bestClass'?x.best:x.avg));
    controls.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.rookieHistory===mode));
    chart.innerHTML=rows.map((x,i)=>{
      const value=mode==='bestClass'?x.best:x.avg;
      const detail=mode==='bestClass'?`${fmt(x.best)} · ${x.bestYears.join(' / ')}`:`${x.avg.toFixed(1)} · ${x.classes} class${x.classes===1?'':'es'}`;
      return `<div class="archive-bar"><strong>${i+1}. ${esc(x.manager)}</strong><div class="archive-track"><div class="archive-fill" style="width:${Math.max(3,value/max*100)}%"></div></div><div class="archive-value">${esc(detail)}</div></div>`;
    }).join('');
  }

  function bindHistoryMetrics(){
    const controls=document.getElementById('historyMetricBtns');
    if(!controls||controls.dataset.rookieMetricsBound==='1')return;
    controls.dataset.rookieMetricsBound='1';
    controls.addEventListener('click',e=>{
      const button=e.target.closest('button');
      if(!button)return;
      const mode=button.dataset.rookieHistory;
      if(!mode){rookieHistoryMode=null;return;}
      rookieHistoryMode=mode;
      setTimeout(()=>{ensureHistoryButtons();renderRookieHistory(mode)},1);
    });
    new MutationObserver(()=>setTimeout(()=>{
      ensureHistoryButtons();
      if(rookieHistoryMode)renderRookieHistory(rookieHistoryMode);
    },0)).observe(controls,{childList:true});
    ensureHistoryButtons();
  }

  let queued=false;
  function queue(){
    if(queued)return;
    queued=true;
    setTimeout(()=>{queued=false;fixDraftOwnerMarkers();addWallRecords();bindHistoryMetrics();ensureHistoryButtons()},0);
  }

  const draftBoard=document.getElementById('draftBoard');
  if(draftBoard)new MutationObserver(queue).observe(draftBoard,{childList:true,subtree:true});
  document.getElementById('draftYear')?.addEventListener('change',queue);
  document.querySelectorAll('.dp-round-tabs button').forEach(b=>b.addEventListener('click',queue));
  queue();
})();
