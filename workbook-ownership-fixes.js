(()=>{
  const D=window.DATA;
  if(!D)throw new Error('Dynasty Plebs data must load before workbook ownership fixes.');

  // Audited Plebs application ledger / workbook correction:
  // 2020 1.06 Justin Jefferson belongs to Seth Miller.
  const jefferson=D.drafts?.['2020']?.rounds?.[0]?.[5];
  if(!jefferson||jefferson.slot!==6||jefferson.player!=='Justin Jefferson'){
    throw new Error('Expected Justin Jefferson at 2020 rookie pick 1.06 before applying ownership correction.');
  }
  jefferson.owner='Seth Miller';

  // PF/PA uses fixed series colors for every manager: Plebs gold for PF and a
  // cooler silver/steel for PA so the two lines remain clearly distinct.
  const pfPaStyle=document.createElement('style');
  pfPaStyle.textContent=`
    #managerTimeline .dp-pfpa-legend i.pf{background:#b88b3e!important}
    #managerTimeline .dp-pfpa-legend i.pa{background:#8f98a3!important}
    #managerTimeline .dp-pa-line{stroke:#8f98a3!important}
    #managerTimeline .dp-pa-point{stroke:#8f98a3!important}
  `;
  document.head.appendChild(pfPaStyle);

  // Keep PF and PA on one shared x-coordinate per season. The original PF/PA
  // bars were side-by-side, so converting their bar centers directly to line
  // points left the two series horizontally offset. Anchor both series to the
  // year-label positions (or the pair midpoint as a fallback), then rebuild the
  // paths from the aligned points.
  function alignPfPaByYear(){
    const svg=document.querySelector('#managerTimeline svg[data-pfpa-lines="1"],#managerTimeline svg');
    if(!svg)return;
    const pf=[...svg.querySelectorAll('circle.dp-pf-point')];
    const pa=[...svg.querySelectorAll('circle.dp-pa-point')];
    if(!pf.length||pf.length!==pa.length)return;

    const yearLabels=[...svg.querySelectorAll('text.dp-year-axis')];
    const xs=pf.map((point,i)=>{
      const yearX=yearLabels.length===pf.length?Number(yearLabels[i].getAttribute('x')):NaN;
      if(Number.isFinite(yearX))return yearX;
      const pfX=Number(point.getAttribute('cx')),paX=Number(pa[i].getAttribute('cx'));
      return Number.isFinite(pfX)&&Number.isFinite(paX)?(pfX+paX)/2:pfX;
    });

    pf.forEach((point,i)=>point.setAttribute('cx',xs[i].toFixed(1)));
    pa.forEach((point,i)=>point.setAttribute('cx',xs[i].toFixed(1)));

    const pathFor=points=>points.map((point,i)=>{
      const x=Number(point.getAttribute('cx')),y=Number(point.getAttribute('cy'));
      return `${i?'L':'M'} ${x.toFixed(1)} ${y.toFixed(1)}`;
    }).join(' ');
    svg.querySelector('path.dp-pf-line')?.setAttribute('d',pathFor(pf));
    svg.querySelector('path.dp-pa-line')?.setAttribute('d',pathFor(pa));

    svg.querySelectorAll('circle.dp-dot.champ').forEach(champ=>{
      const cx=Number(champ.getAttribute('cx'));
      const nearest=pf.reduce((best,point)=>{
        const d=Math.abs(Number(point.getAttribute('cx'))-cx);
        return !best||d<best.d?{point,d}:best;
      },null)?.point;
      if(nearest){
        champ.setAttribute('cx',nearest.getAttribute('cx'));
        champ.setAttribute('cy',nearest.getAttribute('cy'));
      }
    });
  }

  let alignQueued=false;
  const queueAlign=()=>{
    if(alignQueued)return;
    alignQueued=true;
    setTimeout(()=>{alignQueued=false;alignPfPaByYear()},0);
  };
  const timeline=document.getElementById('managerTimeline');
  if(timeline)new MutationObserver(queueAlign).observe(timeline,{childList:true,subtree:true});
  document.getElementById('timelineMetricBtns')?.addEventListener('click',queueAlign);
  document.getElementById('managerSelect')?.addEventListener('change',queueAlign);
  queueAlign();
})();
