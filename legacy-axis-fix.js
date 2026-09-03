(()=>{
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
    const STEP=500,top=52,bottom=40,H=390,inner=H-top-bottom;
    const lo=Math.min(...rows.map(x=>x.value)),hi=Math.max(...rows.map(x=>x.value));
    let min=Math.max(0,Math.floor(lo/STEP)*STEP),max=Math.ceil(hi/STEP)*STEP;
    if(max<=min)max=min+STEP;
    const y=v=>top+(max-v)/(max-min)*inner;
    rows.forEach(r=>{
      const yy=y(r.value);
      r.dot.setAttribute('cy',yy.toFixed(1));
      r.label.setAttribute('y',String(Math.max(22,yy-14)));
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
  }
  document.getElementById('timelineMetricBtns')?.addEventListener('click',()=>setTimeout(applyLegacyAxis,0));
  document.getElementById('managerSelect')?.addEventListener('change',()=>setTimeout(applyLegacyAxis,0));
  setTimeout(applyLegacyAxis,0);
})();

(()=>{
  const D=window.DATA;if(!D)return;
  const current=new Set(D.currentManagers||[]);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  function pickTotals(){
    const totals={};
    Object.entries(D.drafts||{}).forEach(([year,board])=>{
      if(+year>2026)return;
      (board.rounds||[]).flat().forEach(p=>{
        if(!p?.owner||!p.player)return;
        totals[p.owner]=(totals[p.owner]||0)+1;
      });
    });
    return totals;
  }

  function rows(){
    const totals=pickTotals();
    const managers=new Set([...Object.keys(D.regular||{}),...Object.keys(totals)]);
    return [...managers].map(manager=>({manager,value:totals[manager]||0}))
      .filter(x=>x.value>0)
      .sort((a,b)=>((current.has(a.manager)?0:1)-(current.has(b.manager)?0:1))||b.value-a.value||a.manager.localeCompare(b.manager));
  }

  function syncWallCard(){
    const wall=document.getElementById('kpis');if(!wall)return;
    const card=[...wall.querySelectorAll('.kpi')].find(x=>x.querySelector('small')?.textContent.trim()==='Draft Class Average'||x.querySelector('small')?.textContent.trim()==='Rookie Picks');
    if(!card)return;
    const data=rows();if(!data.length)return;
    const top=data[0].value,names=data.filter(x=>x.value===top).map(x=>x.manager).join(' & ');
    const small=card.querySelector('small'),big=card.querySelector('b'),span=card.querySelector('span');
    if(small)small.textContent='Rookie Picks';
    if(big)big.textContent=String(top);
    if(span)span.innerHTML=`<strong>${esc(names)}</strong><em>Through 2026</em>`;
  }

  function syncButton(){
    const controls=document.getElementById('historyMetricBtns');if(!controls)return;
    const existing=controls.querySelector('button[data-rookie-history="rookiePicks"]');
    controls.querySelectorAll('button[data-rookie-history="avgClass"]').forEach((b,i)=>{
      if(existing||i>0)b.remove();
      else{b.dataset.rookieHistory='rookiePicks';b.textContent='Rookie Picks'}
    });
    const button=controls.querySelector('button[data-rookie-history="rookiePicks"]');
    if(button)button.textContent='Rookie Picks';
  }

  function render(){
    const controls=document.getElementById('historyMetricBtns'),chart=document.getElementById('historyChart');if(!controls||!chart)return;
    const data=rows(),max=Math.max(1,...data.map(x=>x.value));
    controls.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.rookieHistory==='rookiePicks'));
    chart.innerHTML=data.map((x,i)=>`<div class="archive-bar${current.has(x.manager)?'':' dp-former-history'}"><strong>${i+1}. ${esc(x.manager)}</strong><div class="archive-track"><div class="archive-fill" style="width:${Math.max(3,x.value/max*100)}%"></div></div><div class="archive-value">${x.value} pick${x.value===1?'':'s'}</div></div>`).join('')+'<div class="dp-history-qualifier">All selections through 2026</div>';
  }

  function sync(){syncButton();syncWallCard()}
  const controls=document.getElementById('historyMetricBtns');
  controls?.addEventListener('click',e=>{
    const button=e.target.closest('button[data-rookie-history="rookiePicks"]');if(!button)return;
    e.preventDefault();e.stopImmediatePropagation();render();
  },true);
  if(controls)new MutationObserver(()=>setTimeout(sync,0)).observe(controls,{childList:true,subtree:true});
  const wall=document.getElementById('kpis');
  if(wall)new MutationObserver(()=>setTimeout(syncWallCard,0)).observe(wall,{childList:true,subtree:true});
  setTimeout(sync,0);
})();