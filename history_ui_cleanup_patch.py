import json
import re
from pathlib import Path

INDEX = Path('index.html')
src = INDEX.read_text(encoding='utf-8')

# ---- Completed rookie outcome guard -------------------------------------------------
# Frank Gore Jr. was a true 2024 rookie selection and has zero NFL regular-season
# appearances through the completed 2025 season. A zero-game rookie draft pick must
# still count as a 0.0 draft outcome in manager Avg PPG / Pick and round totals; it
# simply contributes no games to any individual career-game denominator.
stats_m = re.search(r'const careerDraftStats=(\{.*?\});\nconst rookieBoards=', src, re.S)
if not stats_m:
    raise RuntimeError('careerDraftStats block not found')
stats = json.loads(stats_m.group(1))
stats['2024|frankgorejr'] = {
    'ppg': 0.0,
    'points': 0.0,
    'games': 0,
    'seasons': 0,
    'through': 2025,
    'pos': 'RB',
    'zeroGameOutcome': True,
}
stats_json = json.dumps(stats, separators=(',', ':'), ensure_ascii=False)
src = src[:stats_m.start(1)] + stats_json + src[stats_m.end(1):]

# ---- History / main-page naming ------------------------------------------------------
src = src.replace(
    '<button class="on" data-view="alltime">All-Time</button>',
    '<button class="on" data-view="alltime">History</button>',
)
src = src.replace(
    '<div class="section-head"><h2>Wall of Fame</h2><p>League records from the 2019–2025 regular-season archive.</p></div>',
    '<div class="section-head"><h2>Wall of Fame</h2></div>',
)
src = src.replace(
    '<div class="section-head"><h2>Champions</h2><p>Verified champions currently in the league archive.</p></div>',
    '<div class="section-head"><h2>Champions</h2></div>',
)
src = src.replace(
    '<div class="section-head left"><h2>All-Time</h2><p>Career regular-season totals.</p></div>',
    '<div class="section-head"><h2>History</h2></div>',
)

# ---- Manager-page subtitle cleanup ---------------------------------------------------
src = src.replace(
    '<div class="subhead"><h3>Career Timeline</h3><p>Year-by-year regular-season performance. Every manager uses the same scale for each metric.</p></div>',
    '<div class="subhead"><h3>Career Timeline</h3></div>',
)
src = src.replace(
    '<div class="subhead"><h3>Rookie Picks</h3><p>Complete recovered rookie-draft history with Dynasty Plebs scoring. True rookie selections only; veteran selections are removed from this view and all rookie-draft grading.</p></div>',
    '<div class="subhead"><h3>Rookie Picks</h3></div>',
)
# Tolerate an earlier wording if a source patch is rerun from an older base.
src = src.replace(
    '<div class="subhead"><h3>Rookie Picks</h3><p>Complete recovered rookie-draft history with career-to-date Dynasty Plebs scoring.</p></div>',
    '<div class="subhead"><h3>Rookie Picks</h3></div>',
)

# Remove only the requested explanatory subtext from the Pos + Round card.
src = src.replace(
    "<span>vs active-manager peers at the same position + round</span></div>",
    "</div>",
)

# Remove the long explanatory note beneath the rookie-intel cards. Keep card-specific
# counts/details because they are data, not section-header explanatory copy.
src = re.sub(
    r'<div class=\\"intel-note\\">Rookie-performance ranks compare current managers only\..*?Veteran selections are removed from rookie-pick history and every rookie metric\.</div>',
    '',
    src,
    count=1,
    flags=re.S,
)
# The HTML lives inside a JS template literal and can also appear without escaped quotes.
src = re.sub(
    r'<div class="intel-note">Rookie-performance ranks compare current managers only\..*?Veteran selections are removed from rookie-pick history and every rookie metric\.</div>',
    '',
    src,
    count=1,
    flags=re.S,
)

# ---- Hard regression audit for Seth's completed rookie sample ------------------------
boards_m = re.search(r'const rookieBoards=(\{.*?\});\nconst nf=', src, re.S)
if not boards_m:
    raise RuntimeError('rookieBoards block not found')
boards = json.loads(boards_m.group(1))

def norm_name(value):
    import unicodedata
    s = unicodedata.normalize('NFD', str(value or '').lower())
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', s)

seth_all = []
seth_true = []
seth_scored = []
for year_text, board in boards.items():
    year = int(year_text)
    if year > 2025:
        continue
    rounds = board.get('rounds', [])
    owners = board.get('ownersByRound', [])
    for ri, players in enumerate(rounds):
        owner_row = owners[ri] if ri < len(owners) else []
        for si, player in enumerate(players):
            if not player or si >= len(owner_row) or owner_row[si] != 'Seth Miller':
                continue
            key = f'{year}|{norm_name(player)}'
            stat = stats.get(key)
            seth_all.append((year, ri + 1, si + 1, player, key))
            if not stat or stat.get('excluded') != 'veteran':
                seth_true.append((year, ri + 1, si + 1, player, key))
                if stat and isinstance(stat.get('ppg'), (int, float)) and stat.get('pos'):
                    seth_scored.append((year, ri + 1, si + 1, player, key))

if len(seth_all) != 50:
    raise RuntimeError(f'Seth completed draft-pick count drifted: {len(seth_all)} != 50')
if len(seth_true) != 48:
    raise RuntimeError(f'Seth true-rookie count drifted: {len(seth_true)} != 48')
if len(seth_scored) != 48:
    missing = [row for row in seth_true if row not in seth_scored]
    raise RuntimeError(f'Seth scored rookie sample should be 48; found {len(seth_scored)}. Missing={missing}')

# Requested UI strings must be gone/present exactly as intended.
required = [
    '<button class="on" data-view="alltime">History</button>',
    '<div class="section-head"><h2>History</h2></div>',
]
for needle in required:
    if needle not in src:
        raise RuntimeError(f'Missing requested History UI marker: {needle}')
for stale in [
    '<button class="on" data-view="alltime">All-Time</button>',
    '<div class="section-head left"><h2>All-Time</h2>',
    'League records from the 2019–2025 regular-season archive.',
    'Verified champions currently in the league archive.',
    'Career regular-season totals.',
    'Year-by-year regular-season performance. Every manager uses the same scale for each metric.',
    'vs active-manager peers at the same position + round',
    'Rookie-performance ranks compare current managers only.',
]:
    if stale in src:
        raise RuntimeError(f'Requested subtitle/UI cleanup did not remove: {stale}')

INDEX.write_text(src, encoding='utf-8')
print('History UI cleanup applied: centered History, main subtitles removed, manager rookie/career subtitles removed.')
print('Seth completed rookie audit: 50 draft picks, 48 true rookies, 48 scored outcomes (Frank Gore Jr. = verified 0.0 zero-game outcome).')
