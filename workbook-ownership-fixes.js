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

  // PF/PA is a uniform-color chart. Keep the PF legend swatch on the same gold
  // used by the PF line instead of inheriting the selected manager's old color.
  const pfLegendStyle=document.createElement('style');
  pfLegendStyle.textContent='#managerTimeline .dp-pfpa-legend i.pf{background:#b88b3e!important}';
  document.head.appendChild(pfLegendStyle);
})();
