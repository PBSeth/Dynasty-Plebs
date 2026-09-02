#!/bin/sh
set -eu
node verify-workbook-data.js
mkdir -p dist
node extract-draft-outcomes.js
cp site-v2.css workbook-extras.css production-upgrade.css regression-fix.css app-v2.js workbook-extras.js production-upgrade.js regression-fix.js data-v3-*.js dist/
cp index-workbook.html dist/index.html

# Final mobile chart/layout correction. Appended at build time so it runs after the
# existing manager fixes without disturbing the workbook-backed source files.
cat >> dist/regression-fix.js <<'EOF'

(()=>{
  const style=document.createElement('style');
  style.textContent=`
    .career-overview-panel .dp-chart-wrap{padding:4px 5px 6px!important}
    .career-overview-panel .dp-chart-svg[viewBox="0 0 760 390"]{height:auto!important;aspect-ratio:760/390!important}
    .rookie-picks-head{display:flex!important;justify-content:center!important;text-align:center!important}
    .rookie-picks-head h3{width:100%!important;margin-left:auto!important;margin-right:auto!important;text-align:center!important}
    .dp-rookie-bar{transform:scaleY(.82)!important;transform-origin:bottom center!important}
    .dp-rookie-value{top:1px!important;z-index:3!important}
    .dp-pf-line,.dp-pa-line{fill:none;stroke-width:4;stroke-linecap:round;stroke-linejoin:round}
    .dp-pf-line{stroke:var(--mc,#7e3125)}
    .dp-pa-line{stroke:#9a7b49}
    .dp-pf-point,.dp-pa-point{fill:#fffaf0;stroke-width:3}
    .dp-pf-point{stroke:var(--mc,#7e3125)}
    .dp-pa-point{stroke:#9a7b49}
    @media(max-width:680px){
      .career-overview-panel .dp-chart-wrap{padding:2px 4px 4px!important}
      .rookie-picks-head h3{font-size:34px!important}
      .dp-rookie-bar{transform:scaleY(.80)!important}
    }
  `;
  document.head.appendChild(style);

  const NS='http://www.w3.org/2000/svg';
  function convertPfPaBars(){
    const svg=document.querySelector('#managerTimeline svg');
    if(!svg||svg.dataset.pfpaLines==='1')return;
    const pf=[...svg.querySelectorAll('rect.dp-pf-bar')];
    const pa=[...svg.querySelectorAll('rect.dp-pa-bar')];
    if(!pf.length||pf.length!==pa.length)return;
    svg.dataset.pfpaLines='1';
    const pts=rects=>rects.map(r=>({
      x:Number(r.getAttribute('x'))+Number(r.getAttribute('width'))/2,
      y:Number(r.getAttribute('y'))
    }));
    const addSeries=(points,pathClass,pointClass)=>{
      const path=document.createElementNS(NS,'path');
      path.setAttribute('class',pathClass);
      path.setAttribute('d',points.map((p,i)=>`${i?'L':'M'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' '));
      svg.appendChild(path);
      points.forEach(p=>{
        const c=document.createElementNS(NS,'circle');
        c.setAttribute('class',pointClass);
        c.setAttribute('cx',p.x.toFixed(1));
        c.setAttribute('cy',p.y.toFixed(1));
        c.setAttribute('r','5');
        svg.appendChild(c);
      });
    };
    addSeries(pts(pf),'dp-pf-line','dp-pf-point');
    addSeries(pts(pa),'dp-pa-line','dp-pa-point');
    [...pf,...pa].forEach(r=>r.remove());
  }

  const timeline=document.getElementById('managerTimeline');
  if(timeline){
    new MutationObserver(()=>convertPfPaBars()).observe(timeline,{childList:true,subtree:true});
    setTimeout(convertPfPaBars,0);
  }
})();
EOF

# Rookie-count semantics + card hierarchy. The analytics sample can be smaller than
# the manager's actual rookie-pick total, so keep those two counts distinct.
cat >> dist/regression-fix.js <<'EOF'

(()=>{
  const D=window.DATA, OUT=window.DRAFT_OUTCOMES||{};
  if(!D)return;
  const norm=s=>String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]/g,'');

  const style=document.createElement('style');
  style.textContent=`
    .dp-manager-picks .pick .dp-pick-meta{justify-content:flex-start!important}
    .dp-manager-picks .pick .ppg-value{display:block!important;margin:5px 0 0!important;color:#3e563b!important;font:900 12px/1.1 Arial,sans-serif!important;white-space:nowrap!important}
    .dp-manager-picks .pick .ppg-value.muted{color:var(--muted)!important}
    .dp-manager-picks .pick b{margin-top:7px!important}
    .dp-manager-picks .dp-pick-pos{margin-top:4px!important}
    @media(max-width:680px){.dp-manager-picks .pick .ppg-value{font-size:11px!important}}
  `;
  document.head.appendChild(style);

  function pickCounts(manager){
    let rookie=0,scored=0;
    Object.entries(D.drafts||{}).forEach(([year,b])=>{
      if(+year>2025)return;
      (b.rounds||[]).flat().forEach(p=>{
        if(!p||p.owner!==manager||!p.player)return;
        const stat=OUT[`${year}|${norm(p.player)}`];
        if(stat?.excluded==='veteran')return;
        rookie++;
        if(stat&&Number.isFinite(stat.ppg)&&stat.pos)scored++;
      });
    });
    return{rookie,scored};
  }

  function fixRookieDisplay(){
    const manager=document.getElementById('managerSelect')?.value||'Seth Miller';
    const picks=document.getElementById('managerPicks');
    if(picks){
      picks.querySelectorAll('.pick').forEach(card=>{
        const name=card.querySelector('b'),ppg=card.querySelector('.ppg-value');
        if(name&&ppg&&ppg.previousElementSibling!==name)name.insertAdjacentElement('afterend',ppg);
      });
    }
    const first=document.querySelector('#rookieAnalytics .dp-draft-intel .dp-intel-card');
    if(first){
      const counts=pickCounts(manager),label=first.querySelector('small'),span=first.querySelector('span');
      if(label&&label.textContent!=='Avg PPG / Scored Pick')label.textContent='Avg PPG / Scored Pick';
      const text=`${counts.rookie} rookie picks · ${counts.scored} scored`;
      if(span&&span.textContent!==text)span.textContent=text;
    }
  }

  const watch=node=>node&&new MutationObserver(()=>setTimeout(fixRookieDisplay,0)).observe(node,{childList:true,subtree:true});
  watch(document.getElementById('managerPicks'));
  watch(document.getElementById('rookieAnalytics'));
  document.getElementById('managerSelect')?.addEventListener('change',()=>setTimeout(fixRookieDisplay,0));
  setTimeout(fixRookieDisplay,0);
})();
EOF
