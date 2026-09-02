(()=>{
  const D=window.DATA;if(!D)return;
  const current=new Set(D.currentManagers||[]);
  const OUT=window.DRAFT_OUTCOMES||{};
  const PRIMARY='#b88b3e';
  const AVG_PF_GAME={
    'Matthew Piontek':128.70526315789473,'Seth Miller':124.93869565217392,'Travis Page':123.35847826086956,
    'Jordan Martin':123.2982608695652,'Matt Metz':121.21826086956521,'Tim Bell':119.69,
    'Bo Tiller':116.77195652173911,'Mason Good':109.79684210526315,'Kevin Long':109.52,
    'Payton Docheff':109.40108695652174,'Clint Hudson':109.18047619047618,'Dave Carnes':104.35478260869567,
    'Alex Agueros':104.2591304347826,'Luke Miller':98.26354430379746,'Matt Clawson':97.68586956521737,
    'Ryan Lipkin':80.83857142857143
  };
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
    #historyChart .dp-history-qualifier{padding:14px 16px 15px;border-top:1px solid #dfd0b6;color:#8a775b;font-size:10px;font-weight:900;letter-spacing:.06em;text-transform:uppercase;text-align:center}
    #history .dp-centered-history-head{justify-content:center!important;text-align:center!important;align-items:center!important}
    #history .dp-centered-history-head h2{width:100%;text-align:center!important}
    #managers>.section-head,#drafts>.section-head{justify-content:center!important;text-align:center!important;align-items:center!important}
    #managers>.section-head h2,#drafts>.section-head h2{width:100%;text-align:center!important}
    #managerPicks .round>h3,#managerPicks .round h3{width:100%;text-align:center!important}
    .dp-draft-intel .dp-intel-card>b,.dp-draft-intel .dp-intel-card>strong{text-align:center!important}
  `;
  document.head.appendChild(style);

  function centerHistoryHeads(){
    [document.getElementById('champions'),document.getElementById('historyChart')].forEach(node=>{
      const head=node?.closest('.section')?.querySelector('.section-head');
      if(head)head.classList.add('dp-centered-history-head');
    });
  }

  function fixDraftOwnerMarkers(){
    document.querySelectorAll('#draftBoard .dp-compact-owner').forEach(node=>{
      const owner=node.textContent.trim();
      if(owner&&!current.has(owner))node.style.setProperty('--owner-color','#111111');
    });
  }

  function statFor(year,player){
    const base=norm(player),keys=[base,base.replace(/lll$/,'iii'),base.replace(/ii$/,'iii')];
    for(const k of keys){const hit=OUT[`${year}|${k}`];if(hit)return hit}
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
    const classes=rookieClasses();if(!classes.length)return null;
    const top=Math.max(...classes.map(x=>x.points));
    const topClasses=classes.filter(x=>Math.abs(x.points-top)<1e-9);
    const byManager={};classes.forEach(x=>(byManager[x.manager]??=[]).push(x.points));
    const averages=Object.entries(byManager).map(([manager,vals])=>({manager,avg:vals.reduce((a,b)=>a+b,0)/vals.length,classes:vals.length}));
    const topAvg=Math.max(...averages.map(x=>x.avg));
    const topAverages=averages.filter(x=>Math.abs(x.avg-topAvg)<1e-9);
    return{top,topClasses,topAvg,topAverages};
  }

  function rookieManagerRows(){
    const classes=rookieClasses(),byManager={};classes.forEach(x=>(byManager[x.manager]??=[]).push(x));
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
    const wall=document.getElementById('kpis');if(!wall||wall.dataset.rookieClassRecords==='1')return;
    const r=rookieClassRecords();if(!r)return;
    const highNames=r.topClasses.map(x=>x.manager).join(' & ');
    const highYears=[...new Set(r.topClasses.map(x=>x.year))].join(' / ');
    const avgNames=r.topAverages.map(x=>x.manager).join(' & ');
    const avgClasses=[...new Set(r.topAverages.map(x=>x.classes))];
    const avgSub=avgClasses.length===1?`${avgClasses[0]} class${avgClasses[0]===1?'':'es'}`:'Career';
    wall.insertAdjacentHTML('beforeend',
      `<div class="kpi"><small>Best Rookie Class</small><b>${fmt(r.top)}</b><span><strong>${esc(highNames)}</strong><em>${esc(highYears)}</em></span></div>`+
      `<div class="kpi"><small>Draft Class Average</small><b>${r.topAvg.toFixed(1)}</b><span><strong>${esc(avgNames)}</strong><em>${esc(avgSub)}</em></span></div>`
    );
    wall.dataset.rookieClassRecords='1';
  }

  let historyAddonMode=null;
  function ensureHistoryButtons(){
    const controls=document.getElementById('historyMetricBtns');if(!controls)return;
    const defs=[['avgPf','Avg PF/Game'],['bestClass','Best Rookie Class'],['avgClass','Draft Class Average']];
    defs.forEach(([key,label])=>{
      const existing=controls.querySelector(`[data-rookie-history="${key}"]`);
      if(existing){if(existing.textContent!==label)existing.textContent=label;return}
      const b=document.createElement('button');b.type='button';b.dataset.rookieHistory=key;b.textContent=label;controls.appendChild(b);
    });
    if(historyAddonMode)controls.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.rookieHistory===historyAddonMode));
  }

  function activeFirstSort(a,b){
    const activeDelta=(current.has(a.manager)?0:1)-(current.has(b.manager)?0:1);
    return activeDelta||b.value-a.value||a.manager.localeCompare(b.manager);
  }

  function renderAddonHistory(mode){
    const controls=document.getElementById('historyMetricBtns'),chart=document.getElementById('historyChart');if(!controls||!chart)return;
    let rows=[],qualifier='';
    if(mode==='avgPf'){
      rows=Object.keys(D.regular||{}).map(manager=>({manager,value:AVG_PF_GAME[manager]})).filter(x=>Number.isFinite(x.value));
      rows.sort(activeFirstSort);
    }else{
      rows=rookieManagerRows().filter(x=>mode==='bestClass'?Number.isFinite(x.best):Number.isFinite(x.avg)).map(x=>({...x,value:mode==='bestClass'?x.best:x.avg}));
      rows.sort(activeFirstSort);
      qualifier=mode==='bestClass'?'Career points to date':'Career points per class';
    }
    const max=Math.max(1,...rows.map(x=>x.value));
    controls.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.rookieHistory===mode));
    const bars=rows.map((x,i)=>{
      let detail;
      if(mode==='avgPf')detail=x.value.toFixed(1);
      else if(mode==='bestClass')detail=`${fmt(x.best)} · ${x.bestYears.join(' / ')}`;
      else detail=`${x.avg.toFixed(1)} · ${x.classes} class${x.classes===1?'':'es'}`;
      return `<div class="archive-bar"><strong>${i+1}. ${esc(x.manager)}</strong><div class="archive-track"><div class="archive-fill" style="width:${Math.max(3,x.value/max*100)}%"></div></div><div class="archive-value">${esc(detail)}</div></div>`;
    }).join('');
    chart.innerHTML=bars+(qualifier?`<div class="dp-history-qualifier">${qualifier}</div>`:'');
  }

  function bindHistoryMetrics(){
    const controls=document.getElementById('historyMetricBtns');if(!controls||controls.dataset.stableMetricsBound==='1')return;
    controls.dataset.stableMetricsBound='1';
    controls.addEventListener('click',e=>{
      const button=e.target.closest('button');if(!button)return;
      const mode=button.dataset.rookieHistory;
      if(!mode){historyAddonMode=null;setTimeout(ensureHistoryButtons,0);return}
      historyAddonMode=mode;
      setTimeout(()=>{ensureHistoryButtons();renderAddonHistory(mode)},0);
    });
    ensureHistoryButtons();
  }

  let queued=false;
  function queue(){
    if(queued)return;queued=true;
    setTimeout(()=>{queued=false;centerHistoryHeads();fixDraftOwnerMarkers();addWallRecords();bindHistoryMetrics();ensureHistoryButtons()},0);
  }
  const draftBoard=document.getElementById('draftBoard');
  if(draftBoard)new MutationObserver(queue).observe(draftBoard,{childList:true,subtree:true});
  document.getElementById('draftYear')?.addEventListener('change',queue);
  queue();
})();