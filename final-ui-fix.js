(()=>{
  const D=window.DATA;if(!D)return;
  const current=new Set(D.currentManagers||[]);
  const PRIMARY='#b88b3e';

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

  let queued=false;
  function queue(){
    if(queued)return;
    queued=true;
    setTimeout(()=>{queued=false;fixDraftOwnerMarkers()},0);
  }

  const draftBoard=document.getElementById('draftBoard');
  if(draftBoard)new MutationObserver(queue).observe(draftBoard,{childList:true,subtree:true});
  document.getElementById('draftYear')?.addEventListener('change',queue);
  document.querySelectorAll('.dp-round-tabs button').forEach(b=>b.addEventListener('click',queue));
  queue();
})();
