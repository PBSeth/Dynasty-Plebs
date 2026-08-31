import re
from pathlib import Path

INDEX = Path('index.html')
src = INDEX.read_text(encoding='utf-8')

# Final recovered user instructions, applied after all earlier data/graph patches.
STYLE = r'''/* USER_NOTES_20260831 */
/* Champions: bespoke gold crown ABOVE all words; remove old watermark crown. */
.champion-card{padding:50px 12px 17px!important;min-height:142px!important;overflow:visible!important}
.champion-card:after{content:none!important;display:none!important}
.champion-card:before{content:"";position:absolute;z-index:2;top:13px;left:50%;transform:translateX(-50%);width:52px;height:27px;background:linear-gradient(180deg,#f6da78 0%,#d3a43f 58%,#9a691e 100%);clip-path:polygon(0 78%,8% 18%,29% 57%,50% 0,71% 57%,92% 18%,100% 78%,94% 100%,6% 100%);filter:drop-shadow(0 2px 1px rgba(52,34,10,.35)) drop-shadow(0 0 5px rgba(183,138,61,.22));border-radius:2px}
.champion-card .yr{font-size:11px!important}.champion-card h3{font-size:20px!important;margin-top:8px!important}.champion-card p{font-size:12px!important;margin-top:5px!important}
/* Readability: labels/tables were too small. */
.wall-card small{font-size:11px!important}.wall-card strong{font-size:15px!important}.wall-card span{font-size:12px!important}
.controls button,.timeline-controls button{font-size:13px!important;padding:9px 12px!important}
.bar strong{font-size:15px!important}.bar small{font-size:12px!important}.val{font-size:16px!important}
.subhead h3{font-size:25px!important}.subhead p{font-size:13px!important}
.axis-label{font-size:12px!important}.point-label{font-size:11px!important}.timeline-legend{font-size:12px!important}
.draft-intel{grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:10px!important;padding:14px!important}
.intel-card{min-height:112px!important;padding:14px 12px!important}.intel-card small{font-size:11px!important;line-height:1.2!important}.intel-card b{font-size:30px!important;margin-top:8px!important}.intel-card strong{font-size:13px!important;line-height:1.3!important}.intel-card span{font-size:11px!important;line-height:1.35!important;margin-top:5px!important}.intel-note{font-size:11px!important;line-height:1.45!important}
.rookie-year-tabs button{font-size:13px!important;padding:9px 12px!important}.pick{padding:14px!important}.pick .meta{font-size:12px!important}.pick b{font-size:17px!important;margin-top:7px!important}.ppg-value{font:800 20px/1 Georgia,"Times New Roman",serif;color:var(--ink);white-space:nowrap}.ppg-badge{display:none!important}
.history-year{font-size:18px!important}.history-team strong{font-size:15px!important}.history-team small{font-size:12px!important}.history-record{font-size:16px!important}.history-record small{font-size:11px!important}
.profile-stats{grid-template-columns:repeat(4,1fr)!important}.profile-stat small{font-size:10px!important}.profile-stat b{font-size:23px!important}.legacy-stat{background:linear-gradient(180deg,#f5e5b9,#ead29a)!important;border-color:#c59a45!important}
@media(max-width:920px){.draft-intel{grid-template-columns:repeat(2,minmax(0,1fr))!important}.profile-stats{grid-template-columns:repeat(2,1fr)!important}}
@media(max-width:620px){.champion-card{padding-top:48px!important}.champion-card:before{top:12px!important;width:48px!important;height:25px!important}.draft-intel{grid-template-columns:repeat(2,minmax(0,1fr))!important}.intel-card{min-height:0!important}.intel-card b{font-size:29px!important}.pick .meta{align-items:flex-end!important}.ppg-value{font-size:19px!important}.bar strong{font-size:14px!important}.bar small{display:block!important;font-size:10px!important}.axis-label{font-size:10px!important}.point-label{font-size:9px!important}}
/* END_USER_NOTES_20260831 */'''

src = re.sub(r'/\* USER_NOTES_20260831 \*/.*?/\* END_USER_NOTES_20260831 \*/', '', src, flags=re.S)
if '</style>' not in src:
    raise RuntimeError('style close tag missing')
src = src.replace('</style>', STYLE + '\n</style>', 1)

# Rookie section language: true rookies only, no veteran rows in the displayed archive.
src = re.sub(
    r'Complete recovered rookie-draft history with career-to-date Dynasty Plebs scoring\.(?: Veteran selections stay in the archive but are excluded from rookie-draft grading\.)?',
    'Complete recovered rookie-draft history with Dynasty Plebs scoring. True rookie selections only; veteran selections are removed from this view and all rookie-draft grading.',
    src,
    count=1,
)

# All-Time rookie-pick totals. 2026 has not played yet, so the completed-outcome
# denominator stops at the 2025 season. A true rookie who had an opportunity but
# never scored still counts as a pick; veterans never count.
new_metrics = r'''const completedRookiePicks=m=>(rookiePicks[m]||[]).filter(p=>p.excluded!=='veteran'&&p.year<=2025),rookiePointTotal=m=>completedRookiePicks(m).reduce((a,p)=>a+(Number.isFinite(p.points)?p.points:0),0),rookiePickCount=m=>completedRookiePicks(m).length,rookieAvgPoints=m=>rookiePickCount(m)?rookiePointTotal(m)/rookiePickCount(m):0;
const metrics={wins:{label:'Wins',get:x=>x.w,fmt:v=>nf.format(v),sub:x=>`${x.w}-${x.l}`},pct:{label:'Win %',get:x=>x.p,fmt:v=>winDec(v),sub:x=>`${x.w}-${x.l}`},pf:{label:'Points For',get:x=>x.pf,fmt:v=>nf.format(v),sub:x=>`${x.s} seasons`},pa:{label:'Points Against',get:x=>x.pa,fmt:v=>nf.format(v),sub:x=>`${x.s} seasons`},rookiePts:{label:'Rookie Pick Points',get:x=>rookiePointTotal(x.m),fmt:v=>nf.format(v),sub:x=>`${rookiePickCount(x.m)} true rookie picks`},rookieAvg:{label:'Avg Points / Rookie Pick',get:x=>rookieAvgPoints(x.m),fmt:v=>nf.format(v),sub:x=>`${rookiePickCount(x.m)} true rookie picks`}};let metric='wins';'''
src, n = re.subn(r'const metrics=\{.*?\};let metric=\'wins\';', new_metrics, src, count=1, flags=re.S)
if n != 1:
    raise RuntimeError(f'All-Time metrics replacement count={n}')

# Active-manager-only rookie grading. Former managers remain visible/selectable and
# retain raw historical outcomes, but they are explicitly not included in rankings.
new_intel = r'''function renderDraftIntel(){
 const box=document.getElementById('draftIntel'),activeManagers=[...currentManagers].filter(m=>rookiePicks[m]),getScored=m=>(rookiePicks[m]||[]).filter(p=>Number.isFinite(p.ppg)&&p.pos&&p.excluded!=='veteran'),scored=getScored(selectedManager),isActive=currentManagers.has(selectedManager);
 if(!scored.length){box.innerHTML=`<div class="intel-note">Draft intel appears after an eligible rookie pick records an NFL regular-season game. PPG uses games actually played only; zero-game seasons never enter the PPG denominator. Veteran selections are removed.</div>`;return}
 const bucket=p=>Math.min(4,Number(p.pick.split('.')[0])),mean=vals=>vals.length?vals.reduce((a,v)=>a+v,0)/vals.length:null;
 const tagged=activeManagers.flatMap(m=>getScored(m).map(p=>({...p,manager:m})));
 const expected=(p,manager)=>{const r=bucket(p),pos=p.pos;let peers=tagged.filter(x=>x.manager!==manager&&x.pos===pos&&bucket(x)===r);if(peers.length<2)peers=tagged.filter(x=>x.manager!==manager&&x.pos===pos);if(peers.length<2)peers=tagged.filter(x=>x.manager!==manager&&bucket(x)===r);if(!peers.length)peers=tagged.filter(x=>x.manager!==manager);return mean(peers.map(x=>x.ppg))};
 const delta=(p,m)=>{const e=expected(p,m);return Number.isFinite(e)?p.ppg-e:null},rawAvg=d=>mean(d.map(p=>p.ppg)),adjAvg=(d,m)=>mean(d.map(p=>delta(p,m)).filter(Number.isFinite));
 const managerMetrics=activeManagers.map(m=>{const d=getScored(m);if(!d.length)return null;const rounds={};[1,2,3,4].forEach(r=>rounds[r]=adjAvg(d.filter(p=>bucket(p)===r),m));return{m,avg:rawAvg(d),adj:adjAvg(d,m),rounds,n:d.length}}).filter(Boolean),me=isActive?managerMetrics.find(x=>x.m===selectedManager):{m:selectedManager,avg:rawAvg(scored),adj:adjAvg(scored,selectedManager),rounds:{},n:scored.length};
 [1,2,3,4].forEach(r=>{if(!isActive)me.rounds[r]=adjAvg(scored.filter(p=>bucket(p)===r),selectedManager)});
 const rank=(value,values)=>{const valid=values.filter(Number.isFinite).sort((a,b)=>b-a);if(!Number.isFinite(value)||!valid.length)return'';return`Rank ${1+valid.filter(v=>v>value+1e-9).length} of ${valid.length} active`},rankLine=(value,values)=>isActive?(rank(value,values)||'No active-manager rank'):'Former manager · not ranked';
 const scoredWithDelta=scored.map(p=>({...p,adj:delta(p,selectedManager)})).filter(p=>Number.isFinite(p.adj)),best=[...scoredWithDelta].sort((a,b)=>b.adj-a.adj)[0],worst=[...scoredWithDelta].sort((a,b)=>a.adj-b.adj)[0];
 const roundCards=[1,2,3,4].map(r=>{const d=scored.filter(p=>bucket(p)===r),raw=rawAvg(d),adj=adjAvg(d,selectedManager),label=r===4?'Round 4+':`Round ${r}`;return`<div class="intel-card"><small>${label} Avg PPG</small><b>${raw==null?'—':raw.toFixed(1)}</b><strong>${rankLine(adj,managerMetrics.map(x=>x.rounds[r]))}${Number.isFinite(adj)?` · ${adj>=0?'+':''}${adj.toFixed(1)} adj`:''}</strong><span>${d.length} eligible scored pick${d.length===1?'':'s'}</span></div>`}).join('');
 box.innerHTML=`<div class="intel-card"><small>Avg PPG / Pick</small><b>${me.avg.toFixed(1)}</b><strong>${isActive?'Raw scoring':'Former manager · not ranked'}</strong><span>${me.n} eligible scored picks</span></div><div class="intel-card"><small>Pos + Round Draft Value</small><b>${me.adj==null?'—':(me.adj>=0?'+':'')+me.adj.toFixed(1)}</b><strong>${rankLine(me.adj,managerMetrics.map(x=>x.adj))}</strong><span>vs active-manager peers at the same position + round</span></div><div class="intel-card"><small>Best Adjusted Pick</small><strong>${best?best.player:'—'}</strong><span>${best?`${best.year} · ${best.pick} · ${best.ppg.toFixed(1)} PPG · ${best.adj>=0?'+':''}${best.adj.toFixed(1)} adj`:'No eligible scored picks'}</span></div><div class="intel-card"><small>Worst Adjusted Pick</small><strong>${worst?worst.player:'—'}</strong><span>${worst?`${worst.year} · ${worst.pick} · ${worst.ppg.toFixed(1)} PPG · ${worst.adj>=0?'+':''}${worst.adj.toFixed(1)} adj`:'No eligible scored picks'}</span></div>${roundCards}<div class="intel-note">Rookie-performance ranks compare current managers only. Former managers remain in the historical manager archive but are not included in the active ranking pool. PPG is total Plebs fantasy points divided only by NFL regular-season games actually played; seasons with 0 games do not dilute it. Veteran selections are removed from rookie-pick history and every rookie metric.</div>`;
}'''
src, n = re.subn(r'function renderDraftIntel\(\)\{.*?\n\}\nfunction renderRookies', new_intel + '\nfunction renderRookies', src, count=1, flags=re.S)
if n != 1:
    raise RuntimeError(f'renderDraftIntel replacement count={n}')

# Remove veterans from rookie history entirely and make the bare PPG value a large,
# normal visual element instead of a tiny "Career PPG" badge.
new_rookies = r'''function renderRookies(){const picks=(rookiePicks[selectedManager]||[]).filter(p=>p.excluded!=='veteran'),tabs=document.getElementById('rookieYearTabs');renderDraftIntel();const years=[...new Set(picks.map(p=>p.year))].sort((a,b)=>b-a);if(!years.length){tabs.innerHTML='';document.getElementById('rookiePicks').innerHTML='<div class="empty">No recovered true-rookie draft entries for this manager.</div>';return}if(!rookieYear||!years.includes(rookieYear))rookieYear=years[0];tabs.innerHTML=years.map(y=>`<button class="${y===rookieYear?'on':''}" data-y="${y}">${y}</button>`).join('');tabs.querySelectorAll('button').forEach(b=>b.onclick=()=>{rookieYear=Number(b.dataset.y);renderRookies()});const d=picks.filter(p=>p.year===rookieYear).sort((a,b)=>Number(a.pick.split('.')[0])-Number(b.pick.split('.')[0])||Number(a.pick.split('.')[1])-Number(b.pick.split('.')[1]));document.getElementById('rookiePicks').innerHTML=d.length?`<div class="pick-grid">${d.map(p=>`<div class="pick" style="--pick-color:${managerColors[selectedManager]||'#b78a3d'}"><div class="meta"><span>${p.pick}</span>${Number.isFinite(p.ppg)?`<span class="ppg-value">${p.ppg.toFixed(1)} PPG</span>`:''}</div><b>${p.player}</b></div>`).join('')}</div>`:'<div class="empty">No true-rookie picks recovered for this year.</div>'}'''
src, n = re.subn(r'function renderRookies\(\)\{.*?\}\n(?=function renderManager)', new_rookies + '\n', src, count=1, flags=re.S)
if n != 1:
    raise RuntimeError(f'renderRookies replacement count={n}')

# Manager page: surface the exact Plebs legacy score and its rank. legacyScores and
# legacyInputs are injected by legacy_score_patch.py immediately before this script.
new_manager = r'''function renderManager(name){selectedManager=name;rookieYear=null;const c=careers.find(x=>x.m===name),h=[...(history.get(name)||[])].sort((a,b)=>a.year-b.year),latest=h.at(-1),active=currentManagers.has(name),legacy=(typeof legacyScores!=='undefined'?legacyScores[name]:null),legacyVals=typeof legacyScores!=='undefined'?Object.values(legacyScores).filter(Number.isFinite).sort((a,b)=>b-a):[],legacyRank=Number.isFinite(legacy)?1+legacyVals.filter(v=>v>legacy+1e-9).length:null;document.documentElement.style.setProperty('--manager-color',managerColors[name]||'#7a3023');document.getElementById('profile').innerHTML=`<div class="profile-top"><div class="profile-title"><h2>${name}</h2><p>${c.s} seasons · ${h[0].year}–${latest.year}</p></div><span class="status ${active?'':'former'}">${active?'Active':'Former'}</span></div><div class="team-pill">${latest.team}</div><div class="record-hero"><small>Career Regular-Season Record</small><b>${c.w}-${c.l}</b></div><div class="profile-stats"><div class="profile-stat"><small>Win %</small><b>${winDec(c.p)}</b></div><div class="profile-stat"><small>Points For</small><b>${nf.format(c.pf)}</b></div><div class="profile-stat"><small>Points Against</small><b>${nf.format(c.pa)}</b></div><div class="profile-stat legacy-stat"><small>Legacy Score</small><b>${Number.isFinite(legacy)?legacy.toFixed(3):'—'}</b>${legacyRank?`<span style="display:block;margin-top:4px;color:var(--muted);font-size:10px;font-weight:800">#${legacyRank} all-time</span>`:''}</div></div>`;document.getElementById('history').innerHTML=[...h].sort((a,b)=>b.year-a.year).map(s=>`<div class="history-row"><div class="history-year">${s.year}</div><div class="history-team"><strong>${s.team}</strong><small>PF ${nf.format(s.pf)} · PA ${nf.format(s.pa)}</small></div><div class="history-record">${s.w}-${s.l}<small>${winDec(s.w/(s.w+s.l))}</small></div></div>`).join('');drawTimeline();renderRookies()}'''
src, n = re.subn(r'function renderManager\(name\)\{.*?\}\n(?=drawChart\(\);)', new_manager + '\n', src, count=1, flags=re.S)
if n != 1:
    raise RuntimeError(f'renderManager replacement count={n}')

INDEX.write_text(src, encoding='utf-8')
print('Applied recovered user instructions: active-only rookie grading, no veteran rows, larger PPG/readability, gold champion crowns, rookie All-Time points, and manager Legacy Score.')
