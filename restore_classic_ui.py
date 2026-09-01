import re
import subprocess
from pathlib import Path

BASE_COMMIT = '5c1e6357634c63086827252be45572fd6d19aa4f'
INDEX = Path('index.html')

src = subprocess.check_output(
    ['git', 'show', f'{BASE_COMMIT}:index.html'],
    text=True,
)

# -----------------------------------------------------------------------------
# Restore the compact pre-workbook-rebuild shell. The workbook assets remain in
# the repo as our data north star; this puts the established Plebs UX back on top.
# -----------------------------------------------------------------------------

# Keep only the useful top-level sections. Drafts stays; 2027 Picks + Trades do not.
old_nav = '<div class="navtabs"><button class="on" data-view="alltime">History</button><button data-view="managers">Managers</button></div>'
new_nav = '<div class="navtabs"><button class="on" data-view="alltime">History</button><button data-view="managers">Managers</button><button data-view="drafts">Drafts</button></div>'
if old_nav not in src:
    raise RuntimeError('Classic nav marker not found')
src = src.replace(old_nav, new_nav, 1)

# Delete lingering explanatory header copy. Data labels/counts remain.
src = src.replace(
    '<div class="subhead"><h3>Season History</h3><p>Team name, record, points for and points against.</p></div>',
    '<div class="subhead"><h3>Season History</h3></div>',
)

# Standalone draft archive using the already-audited rookieBoards data.
drafts_section = '''
<section class="view" id="drafts">
  <div class="section"><div class="section-head"><h2>Rookie Drafts</h2></div>
    <div class="panel">
      <div class="manager-toolbar draft-toolbar"><label for="leagueDraftYear">Year</label><select id="leagueDraftYear"></select></div>
      <div class="league-draft-board" id="leagueDraftBoard"></div>
    </div>
  </div>
</section>
'''
if '</main>' not in src:
    raise RuntimeError('main closing tag not found')
src = src.replace('</main>', drafts_section + '</main>', 1)

# Styling for the retained Drafts tab, built from the classic pick-card language.
extra_css = '''
/* CLASSIC_DRAFT_ARCHIVE_20260901 */
.draft-toolbar{padding:12px 14px;margin:0;border-bottom:1px solid #ded2ba}.league-draft-board{padding:0}.league-draft-round{padding:14px;border-top:1px solid #ded2ba}.league-draft-round:first-child{border-top:0}.league-draft-round h3{margin:0 0 10px;font:800 21px/1 Georgia,serif}.league-draft-round .pick small{display:flex;justify-content:space-between;gap:8px}.league-draft-round .pick small span:last-child{text-align:right}.league-draft-round .pick b{font-size:15px}
@media(max-width:620px){.league-draft-round{padding:10px}.league-draft-round h3{font-size:19px}.league-draft-round .pick-grid{grid-template-columns:1fr}}
/* END_CLASSIC_DRAFT_ARCHIVE_20260901 */
'''
src = src.replace('</style>', extra_css + '</style>', 1)

# -----------------------------------------------------------------------------
# Workbook corrections that the classic shell was missing.
# -----------------------------------------------------------------------------

# 2019's 9-4 franchise belongs to Josh Ponath, not Bo. This is what made Josh
# disappear from League/manager history while his draft picks still existed.
old_josh_row = '["Bo Tiller","Warren Mooners",9,4,1549.84,1408.26]'
new_josh_row = '["Josh Ponath","Warren Mooners",9,4,1549.84,1408.26]'
if old_josh_row not in src:
    raise RuntimeError('2019 Josh/Bo correction marker not found')
src = src.replace(old_josh_row, new_josh_row, 1)

# Use the canonical workbook Legacy standings. Keep the classic display identity
# "David Carnes" so it remains joined to the existing historical/draft data.
canonical_legacy = (
    'const legacyScores={"David Carnes":914,"Bo Tiller":656,"Matt Metz":887,'
    '"Travis Page":1402,"Matthew Piontek":1676,"Jordan Martin":1370,'
    '"Alex Agueros":670,"Matt Clawson":499,"Mason Good":528,"Seth Miller":1796,'
    '"Payton Docheff":657,"Kevin Long":508,"Luke Miller":488,"Tim Bell":575,'
    '"Clint Hudson":589,"Ryan Lipkin":157,"Josh Ponath":796};'
)
src, n = re.subn(r'const legacyScores=\{.*?\};', canonical_legacy, src, count=1, flags=re.S)
if n != 1:
    raise RuntimeError('legacyScores block not replaced')

# Legacy Score returns to being ONE ranking tab alongside the established league
# totals instead of a giant standalone front-page table.
metrics = '''const metrics={wins:{label:'Wins',get:x=>x.w,fmt:v=>nf.format(v),sub:x=>`${x.w}-${x.l}`},pct:{label:'Win %',get:x=>x.p,fmt:v=>winDec(v),sub:x=>`${x.w}-${x.l}`},pf:{label:'Points For',get:x=>x.pf,fmt:v=>nf.format(v),sub:x=>seasonLabel(x.s)},pa:{label:'Points Against',get:x=>x.pa,fmt:v=>nf.format(v),sub:x=>seasonLabel(x.s)},legacy:{label:'Legacy Score',get:x=>legacyScores[x.m]??0,fmt:v=>nf.format(Math.round(v)),sub:x=>''},rookiePts:{label:'Drafted Points',get:x=>draftedPointTotal(x.m),fmt:v=>nf.format(v),sub:x=>`${draftPickCount(x.m)} draft picks`},rookieAvg:{label:'Avg Pts / Draft Pick',get:x=>draftedAvgPoints(x.m),fmt:v=>nf.format(v),sub:x=>`${draftPickCount(x.m)} draft picks`}};let metric='wins';'''
src, n = re.subn(r"const metrics=\{.*?\};let metric='wins';", metrics, src, count=1, flags=re.S)
if n != 1:
    raise RuntimeError('front-page metrics block not replaced')

# Retain the mature manager page: career timeline + per-round rookie PPG/value +
# year-by-year pick cards. Add a standalone draft-board renderer without touching
# those manager analytics.
draft_js = r'''
const leagueDraftYear=document.getElementById('leagueDraftYear');
function renderLeagueDraft(){
  const y=String(leagueDraftYear.value),b=rookieBoards[y],box=document.getElementById('leagueDraftBoard');
  if(!b){box.innerHTML='';return}
  box.innerHTML=b.rounds.map((players,ri)=>`<div class="league-draft-round"><h3>Round ${ri+1}</h3><div class="pick-grid">${players.map((player,si)=>{const owner=b.ownersByRound?b.ownersByRound[ri]?.[si]:b.owners?.[si];return `<div class="pick" style="--pick-color:${managerColors[owner]||'#b78a3d'}"><div class="meta"><span>${ri+1}.${String(si+1).padStart(2,'0')}</span><span>${owner||'—'}</span></div><b>${player||'—'}</b></div>`}).join('')}</div></div>`).join('');
}
if(leagueDraftYear){
  leagueDraftYear.innerHTML=Object.keys(rookieBoards).sort((a,b)=>Number(b)-Number(a)).map(y=>`<option value="${y}">${y}</option>`).join('');
  leagueDraftYear.value=Object.prototype.hasOwnProperty.call(rookieBoards,'2026')?'2026':Object.keys(rookieBoards).sort((a,b)=>Number(b)-Number(a))[0];
  leagueDraftYear.onchange=renderLeagueDraft;
  renderLeagueDraft();
}
'''
marker = "drawChart();select.value='Seth Miller';renderManager('Seth Miller');"
if marker not in src:
    raise RuntimeError('classic init marker not found')
src = src.replace(marker, draft_js + '\n' + marker, 1)

# -----------------------------------------------------------------------------
# Regression guards. Fail rather than silently ship another stripped redesign.
# -----------------------------------------------------------------------------
required = [
    '<h2>Wall of Fame</h2>',
    '<h2>Champions</h2>',
    '<h2>History</h2>',
    'data-view="managers">Managers</button>',
    'data-view="drafts">Drafts</button>',
    '<h3>Career Timeline</h3>',
    '<h3>Rookie Picks</h3>',
    "label=r===4?'Round 4+'",
    "label:'Legacy Score'",
    'Josh Ponath',
    '2024|frankgorejr',
]
for needle in required:
    if needle not in src:
        raise RuntimeError(f'Missing restored Plebs feature: {needle}')

for stale in [
    '2027 Picks',
    'Trade Scroll',
    'data-view="future"',
    'data-view="trades"',
    'Official workbook standings, not reconstructed estimates.',
    'The league ledger, rebuilt from the canonical workbook',
    'Pick ownership is read from the workbook',
    'Legacy components:',
]:
    if stale in src:
        raise RuntimeError(f'Stale rebuild UI survived: {stale}')

# Josh must now be a real league-history manager, not merely a draft-cell owner.
if new_josh_row not in src:
    raise RuntimeError('Josh Ponath 2019 league row missing')

# Seth's corrected rookie sample from the pre-rebuild build must survive.
if '2024|frankgorejr":{"ppg":0.0,"points":0.0,"games":0' not in src:
    raise RuntimeError('Frank Gore Jr. zero-game rookie outcome lost')

INDEX.write_text(src, encoding='utf-8')
print('Restored classic Dynasty Plebs UI.')
print('Front page: proper Wall of Fame + Champions + ranking tabs including Legacy Score.')
print('Top nav: History / Managers / Drafts only; 2027 Picks and Trades removed.')
print('Manager page: classic timeline, per-round rookie PPG/value, yearly rookie cards restored.')
print('Josh Ponath restored to 2019 League history and canonical Legacy Score 796.')
