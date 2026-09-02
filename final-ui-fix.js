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

  function rookieClassRecords(){
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

  let queued=false;
  function queue(){
    if(queued)return;
    queued=true;
    setTimeout(()=>{queued=false;fixDraftOwnerMarkers();addWallRecords()},0);
  }

  const draftBoard=document.getElementById('draftBoard');
  if(draftBoard)new MutationObserver(queue).observe(draftBoard,{childList:true,subtree:true});
  document.getElementById('draftYear')?.addEventListener('change',queue);
  document.querySelectorAll('.dp-round-tabs button').forEach(b=>b.addEventListener('click',queue));
  queue();
})();
