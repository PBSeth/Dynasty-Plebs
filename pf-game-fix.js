(()=>{
  const D=window.DATA;if(!D)return;
  const AVG_PF_GAME={
    'Matthew Piontek':128.70526315789473,'Seth Miller':124.93869565217392,'Travis Page':123.35847826086956,
    'Jordan Martin':123.2982608695652,'Matt Metz':121.21826086956521,'Tim Bell':119.69,
    'Bo Tiller':116.77195652173911,'Mason Good':109.79684210526315,'Kevin Long':109.52,
    'Payton Docheff':109.40108695652174,'Clint Hudson':109.18047619047618,'Dave Carnes':104.35478260869567,
    'Alex Agueros':104.2591304347826,'Luke Miller':98.26354430379746,'Matt Clawson':97.68586956521737,
    'Ryan Lipkin':80.83857142857143
  };
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const controls=document.getElementById('historyMetricBtns');
  const chart=document.getElementById('historyChart');
  if(!controls||!chart)return;

  function label(){
    const b=controls.querySelector('[data-rookie-history="avgPf"]');
    if(b)b.textContent='Avg PF/Game';
  }

  function render(){
    const rows=Object.keys(D.regular||{}).map(manager=>({manager,value:AVG_PF_GAME[manager]})).filter(x=>Number.isFinite(x.value));
    rows.sort((a,b)=>b.value-a.value||a.manager.localeCompare(b.manager));
    const max=Math.max(1,...rows.map(x=>x.value));
    controls.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.rookieHistory==='avgPf'));
    chart.innerHTML=rows.map((x,i)=>`<div class="archive-bar"><strong>${i+1}. ${esc(x.manager)}</strong><div class="archive-track"><div class="archive-fill" style="width:${Math.max(3,x.value/max*100)}%"></div></div><div class="archive-value">${x.value.toFixed(1)}</div></div>`).join('');
  }

  controls.addEventListener('click',e=>{
    const b=e.target.closest('button');
    if(b?.dataset.rookieHistory==='avgPf')setTimeout(render,5);
  });
  new MutationObserver(label).observe(controls,{childList:true,subtree:true});
  label();
})();
