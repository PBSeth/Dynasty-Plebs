(()=>{
  const D=window.DATA, A=window.DRAFT_ADJUSTED_PPG;
  if(!D||!A?.picks)return;

  const current=new Set(D.currentManagers||[]);
  const definition='Career PPG minus the expected Career PPG for a rookie at the same position and draft slot.';
  const norm=s=>String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]/g,'');
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot',"'":'&#39;'}[c]));
  const mean=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:null;
  const signed=v=>Number.isFinite(v)?`${v>=0?'+':''}${v.toFixed(1)}`:'—';
  const one=v=>Number.isFinite(v)?v.toFixed(1):'—';
  const bucket=p=>Math.min(4,Number(String(p.pick||'4.01').split('.')[0])||4);
  const careerFor=rec=>Number.isFinite(rec?.careerPpg)?rec.careerPpg:(Number.isFinite(rec?.expectedPpg)&&Number.isFinite(rec?.draftAdjPpg)?rec.expectedPpg+rec.draftAdjPpg:null);

  const style=document.createElement('style');
  style.textContent=`
    .dp-draft-adj-definition{grid-column:1/-1;margin:1px 2px 0;padding:10px 12px;border-top:1px solid #d7c7aa;color:var(--muted);font-size:11px;line-height:1.4;text-align:center}
    .dp-draft-intel .dp-intel-card[data-draft-adj-main="1"] b{font-variant-numeric:tabular-nums}
    .dp-draft-intel .dp-intel-card .dp-adj-detail{line-height:1.3}
    .dp-draft-intel .dp-intel-card[data-round-card="1"]{text-align:center!important}
    .dp-draft-intel .dp-intel-card[data-round-card="1"] small,
    .dp-draft-intel .dp-intel-card[data-round-card="1"] b,
    .dp-draft-intel .dp-intel-card[data-round-card="1"] strong,
    .dp-draft-intel .dp-intel-card[data-round-card="1"] span{display:block;text-align:center!important}
    @media(max-width:680px){.dp-draft-adj-definition{font-size:10px;padding:9px 8px}}
  `;
  document.head.appendChild(style);

  function recFor(year,player){return A.picks[`${year}|${norm(player)}`]||null}
  function managerPicks(manager){
    const out=[];
    Object.entries(D.drafts||{}).forEach(([year,board])=>{
      if(+year>A.throughSeason)return;
      (board.rounds||[]).forEach((round,ri)=>(round||[]).forEach(p=>{
        if(!p?.player||p.owner!==manager)return;
        const rec=recFor(year,p.player);
        if(!rec||rec.status==='veteran_excluded')return;
        out.push({year:+year,player:p.player,pick:rec.pick||`${ri+1}.${String(p.slot||1).padStart(2,'0')}`,rec});
      }));
    });
    return out;
  }
  function gradedFor(manager){
    return managerPicks(manager)
      .filter(p=>p.rec.status==='scored'&&Number.isFinite(p.rec.draftAdjPpg)&&Number.isFinite(p.rec.expectedPpg)&&Number.isFinite(careerFor(p.rec)))
      .map(p=>({...p,careerPpg:careerFor(p.rec),adj:p.rec.draftAdjPpg}));
  }
  function metrics(manager){
    const all=managerPicks(manager), graded=gradedFor(manager);
    const rounds={};
    [1,2,3,4].forEach(r=>{
      const d=graded.filter(p=>bucket(p)===r);
      rounds[r]={adj:mean(d.map(p=>p.adj)),raw:mean(d.map(p=>p.careerPpg)),n:d.length};
    });
    const worstEligible=graded.filter(p=>!(p.rec.pos==='QB'&&bucket(p)===4));
    return{
      manager,
      rookieCount:all.length,
      gradedCount:graded.length,
      raw:mean(graded.map(p=>p.careerPpg)),
      adj:mean(graded.map(p=>p.adj)),
      rounds,
      best:graded.length?[...graded].sort((a,b)=>b.adj-a.adj)[0]:null,
      worst:worstEligible.length?[...worstEligible].sort((a,b)=>a.adj-b.adj)[0]:null
    };
  }
  function rank(value,values,total=values.length){
    const valid=values.filter(Number.isFinite).sort((a,b)=>b-a);
    if(!Number.isFinite(value)||!valid.length)return null;
    return{r:1+valid.filter(v=>v>value+1e-9).length,n:total};
  }
  function rankLine(manager,value,values){
    if(!current.has(manager))return'Poxed · not ranked';
    const x=rank(value,values,current.size);
    return x?`Rank ${x.r} of ${x.n} active`:'No active-manager rank';
  }
  function bestWorstCard(label,p){
    if(!p)return`<div class="dp-intel-card"><small>${label}</small><b class="dp-name-value">—</b><strong>No graded pick</strong><span></span></div>`;
    return`<div class="dp-intel-card"><small>${label}</small><b class="dp-name-value">${esc(p.player)}</b><strong>${signed(p.adj)} Draft-Adjusted</strong><span class="dp-adj-detail">${one(p.careerPpg)} career PPG · ${one(p.rec.expectedPpg)} expected · ${p.year} ${esc(p.pick)}</span></div>`;
  }

  function applyAnalytics(){
    const grid=document.querySelector('#rookieAnalytics .dp-draft-intel');
    if(!grid||grid.dataset.draftAdjApplied===A.version)return;
    const manager=document.getElementById('managerSelect')?.value||'Seth Miller';
    const me=metrics(manager);
    const activeMetrics=[...current].map(metrics).filter(x=>x.gradedCount);
    const roundCards=[1,2,3,4].map(r=>{
      const x=me.rounds[r], label=r===4?'Round 4+':`Round ${r}`;
      return`<div class="dp-intel-card" data-round-card="1"><small>${label} Draft-Adjusted</small><b>${signed(x.adj)}</b><strong>${rankLine(manager,x.adj,activeMetrics.map(m=>m.rounds[r].adj))}</strong><span>${one(x.raw)} career PPG · ${x.n} rookie pick${x.n===1?'':'s'}</span></div>`;
    }).join('');
    grid.dataset.draftAdjApplied=A.version;
    grid.innerHTML=`
      <div class="dp-intel-card"><small>Avg PPG / Rookie Pick</small><b>${one(me.raw)}</b><strong>Raw career scoring average</strong><span>${me.rookieCount} rookie picks</span></div>
      <div class="dp-intel-card" data-draft-adj-main="1" title="${esc(definition)}"><small>Draft-Adjusted PPG</small><b>${signed(me.adj)}</b><strong>${rankLine(manager,me.adj,activeMetrics.map(m=>m.adj))}</strong><span>Average value above/below historical expectation</span></div>
      ${bestWorstCard('Best Draft-Adjusted Pick',me.best)}
      ${bestWorstCard('Worst Draft-Adjusted Pick',me.worst)}
      ${roundCards}
      <div class="dp-draft-adj-definition">${esc(definition)}</div>`;
  }

  function applyRookieCards(){
    document.querySelectorAll('#managerPicks .round').forEach(group=>{
      const year=Number(group.querySelector('h3')?.textContent);
      if(!year)return;
      group.querySelectorAll('.pick').forEach(card=>{
        const name=card.querySelector('b')?.textContent?.trim();
        if(!name)return;
        const rec=recFor(year,name), pos=rec?.pos, career=careerFor(rec);
        const posEl=card.querySelector('.dp-pick-pos');
        if(posEl&&pos&&posEl.textContent!==pos)posEl.textContent=pos;
        const ppgEl=card.querySelector('.ppg-value');
        if(ppgEl&&rec?.status==='scored'&&Number.isFinite(career)){
          ppgEl.textContent=`${career.toFixed(1)} PPG`;
          ppgEl.classList.remove('muted');
        }
      });
    });
  }

  function applyPoxedStatus(){
    const manager=document.getElementById('managerSelect')?.value||'Seth Miller';
    if(current.has(manager))return;
    const badge=document.querySelector('#managerProfile .badge');
    if(badge)badge.textContent='Poxed';
  }

  let queued=false;
  function queue(){
    if(queued)return; queued=true;
    setTimeout(()=>{queued=false;applyAnalytics();applyRookieCards();applyPoxedStatus()},0);
  }
  const analytics=document.getElementById('rookieAnalytics');
  const picks=document.getElementById('managerPicks');
  if(analytics)new MutationObserver(queue).observe(analytics,{childList:true,subtree:true});
  if(picks)new MutationObserver(queue).observe(picks,{childList:true,subtree:true});
  document.getElementById('managerSelect')?.addEventListener('change',queue);
  queue();
})();
