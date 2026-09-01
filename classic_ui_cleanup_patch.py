from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

# Legacy Score belongs in the History ranking controls, not as the manager-page hero.
s = s.replace(
    '/* LEGACY_HERO_20260831 */\n.record-hero small{font-size:11px!important}.record-hero b{font-size:clamp(48px,9vw,72px)!important}.legacy-rank{display:block;margin-top:7px;color:var(--muted);font-size:11px;font-weight:900;letter-spacing:.06em;text-transform:uppercase}.profile-stats{grid-template-columns:repeat(4,1fr)!important}\n@media(max-width:700px){.profile-stats{grid-template-columns:repeat(2,1fr)!important}}\n/* END_LEGACY_HERO_20260831 */\n',
    ''
)

old_profile = '''<div class="record-hero"><small>Legacy Score</small><b>${Number.isFinite(legacy)?Math.round(legacy).toLocaleString():'—'}</b>${legacyRank?`<span class="legacy-rank">#${legacyRank} all-time</span>`:''}</div><div class="profile-stats"><div class="profile-stat"><small>Career Record</small><b>${c.w}-${c.l}</b></div><div class="profile-stat"><small>Win %</small><b>${winDec(c.p)}</b></div><div class="profile-stat"><small>Points For</small><b>${nf.format(c.pf)}</b></div><div class="profile-stat"><small>Points Against</small><b>${nf.format(c.pa)}</b></div></div>'''
new_profile = '''<div class="record-hero"><small>Career Regular-Season Record</small><b>${c.w}-${c.l}</b></div><div class="profile-stats"><div class="profile-stat"><small>Win %</small><b>${winDec(c.p)}</b></div><div class="profile-stat"><small>Points For</small><b>${nf.format(c.pf)}</b></div><div class="profile-stat"><small>Points Against</small><b>${nf.format(c.pa)}</b></div></div>'''
if old_profile not in s:
    raise RuntimeError('Manager Legacy hero marker not found')
s = s.replace(old_profile, new_profile, 1)

# User explicitly asked for no explanatory/ranking subtext beneath Pos + Round Draft Value.
old_posround = '''<div class="intel-card"><small>Pos + Round Draft Value</small><b>${me.adj==null?'—':(me.adj>=0?'+':'')+me.adj.toFixed(1)}</b><strong>${rankLine(me.adj,managerMetrics.map(x=>x.adj))}</strong></div>'''
new_posround = '''<div class="intel-card"><small>Pos + Round Draft Value</small><b>${me.adj==null?'—':(me.adj>=0?'+':'')+me.adj.toFixed(1)}</b></div>'''
if old_posround not in s:
    raise RuntimeError('Pos + Round Draft Value subtext marker not found')
s = s.replace(old_posround, new_posround, 1)

# If a manager has no scored rookie outcomes, keep the state compact rather than another explainer paragraph.
s = s.replace(
    '''if(!scored.length){box.innerHTML=`<div class="intel-note">Draft intel appears after an eligible rookie pick records an NFL regular-season game. PPG uses games actually played only; zero-game seasons never enter the PPG denominator. Veteran selections are removed.</div>`;return}''',
    '''if(!scored.length){box.innerHTML=`<div class="intel-note">No eligible scored rookie picks.</div>`;return}'''
)

# Regression guards: requested structure and copy.
required = [
    "legacy:{label:'Legacy Score'",
    '<small>Career Regular-Season Record</small>',
    '<small>Pos + Round Draft Value</small>',
    '<h3>Career Timeline</h3>',
    '<h3>Rookie Picks</h3>',
]
for needle in required:
    if needle not in s:
        raise RuntimeError(f'Missing required restored UI marker: {needle}')

for stale in [
    '<small>Legacy Score</small><b>${Number.isFinite(legacy)',
    'legacy-rank',
    '<small>Pos + Round Draft Value</small><b>${me.adj==null?\'—\':(me.adj>=0?\'+\':\'\')+me.adj.toFixed(1)}</b><strong>',
]:
    if stale in s:
        raise RuntimeError(f'Stale manager-page subtext/Legacy UI remains: {stale}')

p.write_text(s, encoding='utf-8')
print('Manager page trimmed: Career Record hero restored, Legacy kept only as History metric, Pos + Round subtext removed.')
