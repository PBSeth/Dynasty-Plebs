import csv
import io
import json
import re
import unicodedata
import urllib.request
from pathlib import Path

INDEX = Path('index.html')
LAST_COMPLETE_SEASON = 2025
SEASONS = range(2019, LAST_COMPLETE_SEASON + 1)
OFFENSIVE_POSITIONS = {'QB','RB','WR','TE'}

# Only identity aliases needed to reach a stable nflverse/PFR player record.
ALIASES = {
    'kenwalkeriii':'kennethwalkeriii',
    'nathanieldell':'tankdell',
    'deriusdavis':'dariusdavis',
    'jaelondarden':'jaleondarden',
    'terracemarshall':'terracemarshalljr',
    'brianrobinson':'brianrobinsonjr',
    'zachmoss':'zackmoss',
    'gabrieldavis':'gabedavis',
    'kennethgainwell':'kennygainwell',
    'dwayneeskridge':'deeeskridge',
    'joshpalmer':'joshuapalmer',
    'travisetienne':'travisetiennejr',
    'marvinmimsjr':'marvinmims',
    'michaelwilson':'michaelwilsonjr',
    'chrisrodriguezjr':'chrisrodriguez',
    'joshdowns':'joshuadowns',
}


def norm_name(value):
    s = unicodedata.normalize('NFD', str(value or '').lower())
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', s)


def without_suffix(value):
    for suffix in ('junior','senior','jr','sr','iii','ii','iv','v'):
        if value.endswith(suffix) and len(value) > len(suffix) + 3:
            return value[:-len(suffix)]
    return value


def as_num(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def fetch_bytes(url):
    req = urllib.request.Request(url, headers={
        'User-Agent':'Mozilla/5.0 (Dynasty-Plebs games-played correction)',
        'Accept':'*/*',
    })
    with urllib.request.urlopen(req, timeout=180) as response:
        return response.read()


def csv_rows(url):
    text = fetch_bytes(url).decode('utf-8-sig', errors='replace')
    return list(csv.DictReader(io.StringIO(text)))


def fetch_json(url):
    return json.loads(fetch_bytes(url).decode('utf-8'))


def sleeper_name(record):
    p = record.get('player') or {}
    return (p.get('full_name') or ' '.join(x for x in (p.get('first_name'),p.get('last_name')) if x) or record.get('player_name') or '').strip()


def sleeper_position(record):
    p = record.get('player') or {}
    return p.get('position') or record.get('position') or ''


def resolve_key(target, lookup):
    n = norm_name(target)
    candidates = [n, ALIASES.get(n), without_suffix(n)]
    if ALIASES.get(n):
        candidates.append(without_suffix(ALIASES[n]))
    for candidate in candidates:
        if candidate and candidate in lookup:
            return candidate
    base = without_suffix(n)
    matches = [k for k in lookup if without_suffix(k) == base]
    return matches[0] if len(matches) == 1 else None


html = INDEX.read_text(encoding='utf-8')
boards_match = re.search(r'const rookieBoards=(\{.*?\});\nconst nf=', html, re.S)
stats_match = re.search(r'const careerDraftStats=(\{.*?\});\nconst rookieBoards=', html, re.S)
if not boards_match or not stats_match:
    raise RuntimeError('rookieBoards/careerDraftStats not found in index.html')
boards = json.loads(boards_match.group(1))
old_stats = json.loads(stats_match.group(1))

# Only completed NFL draft classes can have a career outcome today.
draft_entries = []
for year_text, board in boards.items():
    draft_year = int(year_text)
    if draft_year > LAST_COMPLETE_SEASON:
        continue
    for round_players in board.get('rounds', []):
        for player in round_players:
            if player:
                draft_entries.append((draft_year, player))
draft_entries.append((2025, "Don'te Thornton"))

# nflverse player identity table gives us stable PFR ids for the game-level snap data.
player_rows = csv_rows('https://github.com/nflverse/nflverse-data/releases/download/players/players.csv')
name_rows = {}
for row in player_rows:
    position = (row.get('position') or '').strip()
    if position and position not in OFFENSIVE_POSITIONS:
        continue
    labels = [row.get(k) for k in ('display_name','football_name','short_name') if row.get(k)]
    first = (row.get('common_first_name') or row.get('first_name') or '').strip()
    last = (row.get('last_name') or '').strip()
    if first and last:
        labels.append(first + ' ' + last)
    for label in labels:
        name_rows.setdefault(norm_name(label), []).append(row)


def player_row(name):
    n = norm_name(name)
    candidates = [n, ALIASES.get(n), without_suffix(n)]
    if ALIASES.get(n):
        candidates.append(without_suffix(ALIASES[n]))
    rows = []
    for candidate in candidates:
        if candidate:
            rows.extend(name_rows.get(candidate, []))
    unique = {((r.get('gsis_id') or ''),(r.get('pfr_id') or ''),(r.get('display_name') or '')):r for r in rows}
    return next(iter(unique.values())) if len(unique) == 1 else None


identities = {name: player_row(name) for _, name in draft_entries}

# PFR snap-count rows are game-level and include game_type. A REG row is a real appearance.
pfr_games = {}
for season in SEASONS:
    by_player = {}
    rows = csv_rows(f'https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_{season}.csv')
    for row in rows:
        if (row.get('game_type') or '').upper() != 'REG':
            continue
        pfr_id = (row.get('pfr_player_id') or '').strip()
        if not pfr_id:
            continue
        game_id = (row.get('game_id') or row.get('pfr_game_id') or f"{season}|{row.get('week')}|{row.get('team')}").strip()
        by_player.setdefault(pfr_id, set()).add(game_id)
    pfr_games[season] = {pfr_id: len(games) for pfr_id, games in by_player.items()}

# Sleeper raw gp is a safe fallback when a stable PFR identity is unavailable.
# Critically, gms_active is NEVER used as games played: it created the IR/inactive phantom seasons.
sleeper = {}
for season in SEASONS:
    lookup = {}
    for record in fetch_json(f'https://api.sleeper.com/stats/nfl/{season}?season_type=regular'):
        name = sleeper_name(record)
        position = sleeper_position(record)
        if not name or position not in OFFENSIVE_POSITIONS:
            continue
        stats = record.get('stats') or {}
        raw_gp = stats.get('gp')
        row = {
            'raw_gp': None if raw_gp is None else int(as_num(raw_gp)),
            'position': position,
        }
        key = norm_name(name)
        old = lookup.get(key)
        rank = row['raw_gp'] if row['raw_gp'] is not None else -1
        old_rank = old['raw_gp'] if old and old['raw_gp'] is not None else -2
        if old is None or rank > old_rank:
            lookup[key] = row
    sleeper[season] = lookup


def games_played(drafted_name, season):
    identity = identities.get(drafted_name)
    pfr_id = (identity.get('pfr_id') or '').strip() if identity else ''
    if pfr_id and pfr_id in pfr_games[season]:
        return pfr_games[season][pfr_id], 'PFR'
    key = resolve_key(drafted_name, sleeper[season])
    sleeper_row = sleeper[season].get(key) if key else None
    if sleeper_row and sleeper_row['raw_gp'] is not None:
        return sleeper_row['raw_gp'], 'Sleeper raw gp'
    return 0, 'zero'


corrected = {}
changed = []
removed = []
for draft_year, drafted_name in draft_entries:
    stat_key = f'{draft_year}|{norm_name(drafted_name)}'
    old = old_stats.get(stat_key)
    total_games = 0
    seasons_played = 0
    last_year = None
    sources = []
    for season in range(max(draft_year, 2019), LAST_COMPLETE_SEASON + 1):
        games, source = games_played(drafted_name, season)
        sources.append((season, games, source))
        if games > 0:
            total_games += games
            seasons_played += 1
            last_year = season
    if total_games <= 0:
        if old:
            removed.append((stat_key, old.get('games'), sources))
        continue
    identity = identities.get(drafted_name) or {}
    points = float((old or {}).get('points', 0) or 0)
    position = (old or {}).get('pos') or identity.get('position') or ''
    row = {
        'ppg': round(points / total_games, 6),
        'points': round(points, 2),
        'games': total_games,
        'seasons': seasons_played,
        'through': last_year,
        'pos': position,
    }
    corrected[stat_key] = row
    if not old or old.get('games') != total_games or abs(float(old.get('ppg',0)) - row['ppg']) > 0.0005:
        changed.append((stat_key, old, row, sources))

# Hard regression guard for the bug that exposed the denominator problem.
etienne = corrected.get('2021|travisetienne')
if not etienne:
    raise RuntimeError('Travis Etienne corrected career row missing')
if etienne['games'] != 66 or abs(etienne['points'] - 787.60) > 0.01 or abs(etienne['ppg'] - 11.933333) > 0.00001:
    raise RuntimeError(f'Etienne denominator regression: {etienne}')

# Additional season-level guards where Sleeper raw gp is known to differ from official PFR appearances.
for name, season, expected in [('Joe Burrow',2022,16),("Ja'Marr Chase",2022,12),('Cam Akers',2020,13)]:
    got, source = games_played(name, season)
    if got != expected or source != 'PFR':
        raise RuntimeError(f'Games-played calibration failed: {name} {season} got {got} via {source}, expected {expected} PFR')

career_json = json.dumps(corrected, separators=(',',':'), ensure_ascii=False)
html, count = re.subn(
    r'const careerDraftStats=\{.*?\};\n',
    f'const careerDraftStats={career_json};\n',
    html,
    count=1,
    flags=re.S,
)
if count != 1:
    raise RuntimeError('careerDraftStats replacement failed')
INDEX.write_text(html, encoding='utf-8')

print(f'Corrected games-played denominators: {len(changed)} career draft events changed; {len(removed)} phantom-only outcomes removed.')
print(f"Travis Etienne: {etienne['points']:.1f} points / {etienne['games']} games = {etienne['ppg']:.3f} PPG")
for key, old, new, _ in changed[:25]:
    print(f" - {key}: {(old or {}).get('games')} -> {new['games']} games; {(old or {}).get('ppg')} -> {new['ppg']} PPG")
