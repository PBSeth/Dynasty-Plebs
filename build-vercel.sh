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

# Queued visual fixes: snap PF/PA championship dots, use an absolute Avg Finish
# scale, mute former-manager history bars, and make former-manager markers black.
cat >> dist/regression-fix.js <<'EOF'

(()=>{
  const D=window.DATA;if(!D)return;
  const current=new Set(D.currentManagers||[]);
  const style=document.createElement('style');
  style.textContent=`
    #historyChart .archive-bar.dp-former-history .archive-fill{background:#9b968c!important;opacity:.78!important}
  `;
  document.head.appendChild(style);

  function snapChampToPf(){
    const svg=document.querySelector('#managerTimeline svg[data-pfpa-lines="1"]');
    if(!svg)return;
    const pf=[...svg.querySelectorAll('circle.dp-pf-point')];
    const champs=[...svg.querySelectorAll('circle.dp-dot.champ')];
    if(!pf.length||!champs.length)return;
    champs.forEach(ch=>{
      const cx=Number(ch.getAttribute('cx'));
      const target=pf.reduce((best,p)=>{
        const d=Math.abs(Number(p.getAttribute('cx'))-cx);
        return !best||d<best.d?{p,d}:best;
      },null)?.p;
      if(!target)return;
      ch.setAttribute('cx',target.getAttribute('cx'));
      ch.setAttribute('cy',target.getAttribute('cy'));
      ch.setAttribute('r','6');
      ch.dataset.snappedPf='1';
      svg.appendChild(ch);
    });
  }

  function fixHistory(){
    const chart=document.getElementById('historyChart');if(!chart)return;
    const avgOn=[...document.querySelectorAll('#historyMetricBtns button')].some(b=>b.classList.contains('on')&&b.textContent.trim()==='Avg Finish');
    chart.querySelectorAll('.archive-bar').forEach(row=>{
      const name=(row.querySelector('strong')?.textContent||'').replace(/^\d+\.\s*/, '').trim();
      row.classList.toggle('dp-former-history',!current.has(name));
      if(avgOn){
        const value=Number(row.querySelector('.archive-value')?.textContent);
        const fill=row.querySelector('.archive-fill');
        if(fill&&Number.isFinite(value))fill.style.width=`${Math.max(3,Math.min(100,(13-value)/12*100))}%`;
      }
    });
  }

  function fixFormerMarkers(){
    const manager=document.getElementById('managerSelect')?.value||'Seth Miller';
    if(current.has(manager))return;
    document.querySelectorAll('#managerPicks .pick').forEach(card=>card.style.setProperty('--pc','#111111'));
    document.querySelectorAll('#draftBoard .dp-compact-owner').forEach(node=>{
      if(node.textContent.trim()===manager)node.style.setProperty('--owner-color','#111111');
    });
  }

  const schedule=()=>setTimeout(()=>{snapChampToPf();fixHistory();fixFormerMarkers()},0);
  const observe=id=>{const node=document.getElementById(id);if(node)new MutationObserver(schedule).observe(node,{childList:true,subtree:true})};
  observe('managerTimeline');observe('historyChart');observe('managerPicks');observe('draftBoard');
  document.getElementById('managerSelect')?.addEventListener('change',schedule);
  document.getElementById('historyMetricBtns')?.addEventListener('click',schedule);
  document.getElementById('draftYear')?.addEventListener('change',schedule);
  schedule();
})();
EOF
