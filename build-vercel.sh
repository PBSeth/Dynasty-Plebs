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
