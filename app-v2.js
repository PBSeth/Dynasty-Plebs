const DATA=window.DATA;
const COLORS=window.COLORS;
const current=new Set(DATA.currentManagers);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=v=>Number.isFinite(v)?(v*100).toFixed(1)+'%':'—';
const color=n=>COLORS[n]||'#9b8257';
const recWins=r=>{if(!r)return 0;const [w]=r.split('-').map(Number);return w||0};
const allManagers=Object.keys(DATA.regular);

function showView(id){
  document.querySelectorAll('.view').forEach(x=>x.classList.toggle('on',x.id===id));
  document.querySelectorAll('.navtabs button').forEach(x=>x.classList.toggle('on',x.dataset.view===id));
  scrollTo({top:0,behavior:'smooth'});
}
document.querySelectorAll('.navtabs button').forEach(b=>b.onclick=()=>showView(b.dataset.view));

const legacySorted=Object.entries(DATA.legacy).sort((a,b)=>b[1].score-a[1].score);
const activeSorted=Object.entries(DATA.regular).filter(([m])=>current.has(m)).sort((a,b)=>b[1].winPct-a[1].winPct);
const maxWins=Math.max(...Object.values(DATA.regular).map(x=>recWins(x.total)));
const winLeaders=Object.entries(DATA.regular).filter(([m,x])=>recWins(x.total)===maxWins).map(([m])=>m);
const maxPlay=Math.max(...Object.values(DATA.formulaInputs).map(x=>x.playoffWins||0));

document.getElementById('kpis').innerHTML=[
  ['Legacy King',DATA.legacy[legacySorted[0][0]].score.toLocaleString(),legacySorted[0][0]],
  ['Regular-Season Wins',maxWins,winLeaders.join(' & ')],
  ['Active Win %',pct(activeSorted[0][1].winPct),activeSorted.filter(x=>x[1].winPct===activeSorted[0][1].winPct).map(x=>x[0]).join(' & ')],
  ['Playoff Wins',maxPlay,Object.entries(DATA.formulaInputs).filter(([m,x])=>x.playoffWins===maxPlay).map(([m])=>m).join(' & ')],
  ['Championships',Math.max(...Object.values(DATA.legacy).map(x=>x.titles)),Object.entries(DATA.legacy).filter(([m,x])=>x.titles===2).map(([m])=>m).join(' & ')]
].map(([l,v,n])=>`<div class="kpi"><small>${l}</small><b>${v}</b><span>${esc(n)}</span></div>`).join('');

document.getElementById('champions').innerHTML=DATA.champions.map(c=>`<div class="champ"><small>${c.year} Champion</small><strong>${esc(c.manager)}</strong></div>`).join('');

document.getElementById('legacyTable').innerHTML=`<tr><th>#</th><th>Manager</th><th>Score</th><th>Avg Finish</th><th>Last 3</th><th>Titles</th><th>Reg. Win %</th><th>Playoff Wins</th></tr>`+
  legacySorted.map(([m,x],i)=>`<tr class="${current.has(m)?'current':''}"><td>${i+1}</td><td><strong>${esc(m)}</strong></td><td class="num">${Number(x.score).toLocaleString()}</td><td class="num">${Number.isFinite(x.avg)?x.avg.toFixed(2):'—'}</td><td class="num">${Number.isFinite(x.last3)?x.last3.toFixed(2):'—'}</td><td class="num">${x.titles}</td><td class="num">${pct(DATA.regular[m]?.winPct)}</td><td class="num">${DATA.formulaInputs[m]?.playoffWins??'—'}</td></tr>`).join('');

const managerSelect=document.getElementById('managerSelect');
managerSelect.innerHTML=allManagers.sort((a,b)=>(current.has(a)?0:1)-(current.has(b)?0:1)||a.localeCompare(b)).map(m=>`<option>${esc(m)}</option>`).join('');

function managerDraftPicks(m){
  const out=[];
  Object.entries(DATA.drafts).forEach(([year,b])=>b.rounds.forEach((r,ri)=>r.forEach(p=>{
    if(p.owner===m)out.push({year:+year,round:ri+1,...p});
  })));
  return out.sort((a,b)=>b.year-a.year||a.round-b.round||a.slot-b.slot);
}

function renderManager(m){
  const r=DATA.regular[m],p=DATA.playoffs[m],l=DATA.legacy[m],f=DATA.formulaInputs[m],rank=1+legacySorted.findIndex(([n])=>n===m);
  document.documentElement.style.setProperty('--mc',color(m));
  document.getElementById('managerProfile').innerHTML=`
    <div class="manager-head"><h2>${esc(m)}</h2><span class="badge ${current.has(m)?'':'former'}">${current.has(m)?'Active':'Former'}</span></div>
    <div class="legacy-hero"><small>Legacy Score</small><b>${Number(l.score).toLocaleString()}</b><span>#${rank} all-time</span></div>
    <div class="stat-grid">
      <div class="stat"><small>Regular Season</small><b>${r.total||'—'}</b></div>
      <div class="stat"><small>Win %</small><b>${pct(r.winPct)}</b></div>
      <div class="stat"><small>Playoffs</small><b>${p.total||'—'}</b></div>
      <div class="stat"><small>Titles</small><b>${l.titles}</b></div>
      <div class="stat"><small>Avg Finish</small><b>${Number.isFinite(l.avg)?l.avg.toFixed(2):'—'}</b></div>
      <div class="stat"><small>Last 3 Avg</small><b>${Number.isFinite(l.last3)?l.last3.toFixed(2):'—'}</b></div>
      <div class="stat"><small>Playoff Wins</small><b>${f?.playoffWins??'—'}</b></div>
      <div class="stat"><small>Draft Picks</small><b>${managerDraftPicks(m).length}</b></div>
    </div>`;

  const years=Object.keys(r.yearly).sort((a,b)=>b-a);
  document.getElementById('seasonHistory').innerHTML=years.map(y=>{
    const rr=r.yearly[y],pr=p.yearly[y],fin=l.finish[y];
    if(!rr&&!pr&&!fin)return'';
    return `<div class="season-row"><strong>${y}</strong><span>${pr||'—'}</span><div class="rec">${rr||'—'}</div><div class="finish">${fin?('#'+fin):'—'}</div></div>`;
  }).join('');

  const picks=managerDraftPicks(m);
  const grouped=Object.groupBy?Object.groupBy(picks,x=>x.year):picks.reduce((a,x)=>((a[x.year]??=[]).push(x),a),{});
  document.getElementById('managerPicks').innerHTML=picks.length?Object.entries(grouped).sort((a,b)=>b[0]-a[0]).map(([y,ps])=>`<div class="round"><h3>${y}</h3><div class="pick-grid">${ps.map(x=>`<div class="pick" style="--pc:${color(m)}"><small><span>${x.round}.${String(x.slot).padStart(2,'0')}</span><span>${esc(m)}</span></small><b>${esc(x.player||'—')}</b></div>`).join('')}</div></div>`).join(''):'<div class="empty">No recorded rookie picks.</div>';
}

managerSelect.onchange=()=>renderManager(managerSelect.value);
managerSelect.value='Seth Miller';
renderManager('Seth Miller');

const draftYear=document.getElementById('draftYear');
const draftYears=Object.keys(DATA.drafts).sort((a,b)=>b-a);
draftYear.innerHTML=draftYears.map(y=>`<option>${y}</option>`).join('');
function renderDraft(y){
  const b=DATA.drafts[y];
  document.getElementById('draftBoard').innerHTML=b.rounds.map((r,ri)=>`<div class="round"><h3>Round ${ri+1}</h3><div class="pick-grid">${r.map(p=>`<div class="pick" style="--pc:${color(p.owner)}"><small><span>${ri+1}.${String(p.slot).padStart(2,'0')}</span><span>${esc(p.owner||'Unknown')}</span></small><b>${esc(p.player||'—')}</b></div>`).join('')}</div></div>`).join('');
}
draftYear.onchange=()=>renderDraft(draftYear.value);
draftYear.value=draftYears.includes('2026')?'2026':draftYears[0];
renderDraft(draftYear.value);
