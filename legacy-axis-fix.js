(()=>{
  const graphLabelStyle=document.createElement('style');
  graphLabelStyle.textContent='#managerTimeline .dp-point-label,#managerTimeline .timeline-label,#managerTimeline .point-label{display:none!important}';
  document.head.appendChild(graphLabelStyle);

  const NS='http://www.w3.org/2000/svg';
  function applyLegacyAxis(){
    const controls=document.getElementById('timelineMetricBtns');
    if(!controls?.querySelector('button.on[data-mode="legacy"]'))return;
    const svg=document.querySelector('#managerTimeline svg.dp-chart-svg');
    if(!svg)return;
    const dots=[...svg.querySelectorAll('circle.dp-dot')];
    const labels=[...svg.querySelectorAll('text.dp-point-label')];
    if(!dots.length||dots.length!==labels.length)return;
    const rows=dots.map((dot,i)=>({
      dot,
      label:labels[i],
      x:Number(dot.getAttribute('cx')),
      value:Number(String(labels[i].textContent||'').replace(/,/g,''))
    })).filter(x=>Number.isFinite(x.x)&&Number.isFinite(x.value));
    if(rows.length!==dots.length)return;
    const STEP=500,MIN=0,MAX=2500,top=52,bottom=40,H=390,inner=H-top-bottom;
    const min=MIN,max=MAX;
    const y=v=>top+(max-v)/(max-min)*inner;
    rows.forEach(r=>{
      const yy=y(r.value);
      r.dot.setAttribute('cy',yy.toFixed(1));
      r.label.style.display='none';
    });
    svg.querySelectorAll('circle.dp-champ-halo').forEach(h=>{
      const x=Number(h.getAttribute('cx'));
      const target=rows.reduce((best,r)=>!best||Math.abs(r.x-x)<best.d?{r,d:Math.abs(r.x-x)}:best,null)?.r;
      if(target)h.setAttribute('cy',target.dot.getAttribute('cy'));
    });
    const path=rows.map((r,i)=>`${i?'L':'M'} ${r.x.toFixed(1)} ${Number(r.dot.getAttribute('cy')).toFixed(1)}`).join(' ');
    svg.querySelector('path.dp-series')?.setAttribute('d',path);
    const area=svg.querySelector('path.dp-area');
    if(area)area.setAttribute('d',`${path} L ${rows.at(-1).x.toFixed(1)} ${(top+inner).toFixed(1)} L ${rows[0].x.toFixed(1)} ${(top+inner).toFixed(1)} Z`);
    svg.querySelectorAll('line.dp-grid,text.dp-axis[text-anchor="end"]').forEach(n=>n.remove());
    const anchor=svg.querySelector('path.dp-area,path.dp-series');
    for(let tick=min;tick<=max;tick+=STEP){
      const yy=y(tick);
      const line=document.createElementNS(NS,'line');
      line.setAttribute('class','dp-grid');line.setAttribute('x1','54');line.setAttribute('x2','742');line.setAttribute('y1',yy);line.setAttribute('y2',yy);
      const text=document.createElementNS(NS,'text');
      text.setAttribute('class','dp-axis');text.setAttribute('x','45');text.setAttribute('y',yy+4);text.setAttribute('text-anchor','end');text.textContent=tick.toLocaleString('en-US');
      svg.insertBefore(line,anchor);svg.insertBefore(text,anchor);
    }
    svg.dataset.legacyAxisStep='500';
    svg.dataset.legacyAxisMin='0';
    svg.dataset.legacyAxisMax='2500';
  }
  document.getElementById('timelineMetricBtns')?.addEventListener('click',()=>setTimeout(applyLegacyAxis,0));
  document.getElementById('managerSelect')?.addEventListener('change',()=>setTimeout(applyLegacyAxis,0));
  setTimeout(applyLegacyAxis,0);
})();

(()=>{
  const D=window.DATA;if(!D)return;
  const current=new Set(D.currentManagers||[]);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  function pickStats(){
    const totals={},classes={};
    Object.entries(D.drafts||{}).forEach(([year,board])=>{
      if(+year>2026)return;
      (board.rounds||[]).flat().forEach(p=>{
        if(!p?.owner||!p.player)return;
        totals[p.owner]=(totals[p.owner]||0)+1;
        (classes[p.owner]??=new Set()).add(+year);
      });
    });
    return{totals,classes};
  }

  function rows(){
    const {totals,classes}=pickStats();
    const managers=new Set([...Object.keys(D.regular||{}),...Object.keys(totals)]);
    return [...managers].map(manager=>{
      const total=totals[manager]||0,count=classes[manager]?.size||0;
      return{manager,total,classes:count,value:count?total/count:0};
    }).filter(x=>x.classes>0)
      .sort((a,b)=>((current.has(a.manager)?0:1)-(current.has(b.manager)?0:1))||b.value-a.value||b.total-a.total||a.manager.localeCompare(b.manager));
  }

  function syncWallCard(){
    const wall=document.getElementById('kpis');if(!wall)return;
    const card=[...wall.querySelectorAll('.kpi')].find(x=>['Draft Class Average','Rookie Picks','Picks per Class'].includes(x.querySelector('small')?.textContent.trim()));
    if(!card)return;
    const data=rows();if(!data.length)return;
    const top=Math.max(...data.map(x=>x.value));
    const leaders=data.filter(x=>Math.abs(x.value-top)<1e-9);
    const names=leaders.map(x=>x.manager).join(' & ');
    const small=card.querySelector('small'),big=card.querySelector('b'),span=card.querySelector('span');
    if(small)small.textContent='Picks per Class';
    if(big)big.textContent=top.toFixed(1);
    if(span)span.innerHTML=`<strong>${esc(names)}</strong><em>Through 2026</em>`;
  }

  function syncButton(){
    const controls=document.getElementById('historyMetricBtns');if(!controls)return;
    const existing=controls.querySelector('button[data-rookie-history="picksPerClass"]');
    controls.querySelectorAll('button[data-rookie-history="avgClass"],button[data-rookie-history="rookiePicks"]').forEach((b,i)=>{
      if(existing||i>0)b.remove();
      else{b.dataset.rookieHistory='picksPerClass';b.textContent='Picks per Class'}
    });
    const button=controls.querySelector('button[data-rookie-history="picksPerClass"]');
    if(button)button.textContent='Picks per Class';
  }

  function render(){
    const controls=document.getElementById('historyMetricBtns'),chart=document.getElementById('historyChart');if(!controls||!chart)return;
    const data=rows(),max=Math.max(1,...data.map(x=>x.value));
    controls.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.rookieHistory==='picksPerClass'));
    chart.innerHTML=data.map((x,i)=>`<div class="archive-bar${current.has(x.manager)?'':' dp-former-history'}"><strong>${i+1}. ${esc(x.manager)}</strong><div class="archive-track"><div class="archive-fill" style="width:${Math.max(3,x.value/max*100)}%"></div></div><div class="archive-value">${x.value.toFixed(1)} · ${x.total} picks / ${x.classes} class${x.classes===1?'':'es'}</div></div>`).join('')+'<div class="dp-history-qualifier">All selections through 2026 · classes with at least one pick</div>';
  }

  function sync(){syncButton();syncWallCard()}
  const controls=document.getElementById('historyMetricBtns');
  controls?.addEventListener('click',e=>{
    const button=e.target.closest('button[data-rookie-history="picksPerClass"]');if(!button)return;
    e.preventDefault();e.stopImmediatePropagation();render();
  },true);
  if(controls)new MutationObserver(()=>setTimeout(sync,0)).observe(controls,{childList:true,subtree:true});
  const wall=document.getElementById('kpis');
  if(wall)new MutationObserver(()=>setTimeout(syncWallCard,0)).observe(wall,{childList:true,subtree:true});
  setTimeout(sync,0);
})();