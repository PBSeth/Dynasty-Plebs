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
})();
