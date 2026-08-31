import collections
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

INDEX = Path('index.html')
ESPN_LEAGUE_ID = 30017097
SLEEPER_BASE = 'https://api.sleeper.app/v1'

# Locked Dynasty Plebs formula from the league sheet/history:
# Legacy = Reg-season Win% + .05*seasons + .05*playoff wins + .50*championships
# Playoff byes count as playoff wins.

def norm(value):
    return re.sub(r'[^a-z0-9]', '', str(value or '').lower())


def get_json(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Dynasty-Plebs legacy-score updater)',
        'Accept': 'application/json,text/plain,*/*',
    })
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.load(response)


def parse_site(src):
    sm = re.search(r'const seasons=(\[.*?\]);\nconst champions=', src, re.S)
    cm = re.search(r'const champions=(\[.*?\]);', src, re.S)
    if not sm or not cm:
        raise RuntimeError('Could not parse seasons/champions from index.html')
    return json.loads(sm.group(1)), json.loads(cm.group(1))


src = INDEX.read_text(encoding='utf-8')
seasons, champions = parse_site(src)
canonical_names = {norm(row[0]): row[0] for s in seasons for row in s['r']}
team_owner = {(s['y'], norm(row[1])): row[0] for s in seasons for row in s['r']}

# A few historical ESPN account-display variants can differ from the canonical site name.
name_aliases = {
    'matthewmetz': 'Matt Metz',
    'mattmetz': 'Matt Metz',
    'matthewpiontek': 'Matthew Piontek',
    'davidcarnes': 'David Carnes',
    'mattclawson': 'Matt Clawson',
    'paytondocheff': 'Payton Docheff',
}


def canon_person(value):
    n = norm(value)
    return canonical_names.get(n) or name_aliases.get(n)


def espn_payload(year):
    urls = [
        f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/leagues/{ESPN_LEAGUE_ID}?view=mMatchupScore&view=mTeam',
        f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/leagueHistory/{ESPN_LEAGUE_ID}?seasonId={year}&view=mMatchupScore&view=mTeam',
        f'https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/leagues/{ESPN_LEAGUE_ID}?view=mMatchupScore&view=mTeam',
    ]
    errors = []
    for url in urls:
        try:
            data = get_json(url)
            if isinstance(data, list):
                data = data[0]
            if isinstance(data, dict) and data.get('schedule'):
                return data
        except Exception as exc:
            errors.append(f'{type(exc).__name__}: {exc}')
    raise RuntimeError(f'ESPN {year} playoff data unavailable: ' + ' | '.join(errors))


def espn_manager_map(year, data):
    members = {str(m.get('id')): m for m in data.get('members', [])}
    out = {}
    for team in data.get('teams', []):
        tid = team.get('id')
        manager = None
        for owner_id in team.get('owners') or []:
            m = members.get(str(owner_id), {})
            for field in ('displayName', 'firstName', 'lastName'):
                manager = canon_person(m.get(field)) or manager
            if manager:
                break
        if not manager:
            candidates = [
                team.get('name'),
                ' '.join(x for x in (team.get('location'), team.get('nickname')) if x),
            ]
            for candidate in candidates:
                manager = team_owner.get((year, norm(candidate)))
                if manager:
                    break
        if manager:
            out[tid] = manager
    return out


def espn_playoff_wins(year):
    data = espn_payload(year)
    manager_by_team = espn_manager_map(year, data)
    playoff = [g for g in data.get('schedule', []) if str(g.get('playoffTierType', '')).upper() == 'WINNERS_BRACKET']
    if not playoff:
        raise RuntimeError(f'ESPN {year}: no WINNERS_BRACKET games found')

    wins = collections.Counter()
    appearances = collections.defaultdict(list)
    periods = sorted({int(g.get('matchupPeriodId') or 0) for g in playoff if g.get('matchupPeriodId') is not None})
    period_rank = {p: i + 1 for i, p in enumerate(periods)}

    for game in playoff:
        period = int(game.get('matchupPeriodId') or periods[0])
        sides = [game.get('home'), game.get('away')]
        present = [s for s in sides if isinstance(s, dict) and s.get('teamId') in manager_by_team]
        for side in present:
            appearances[side['teamId']].append(period_rank[period])
        if len(present) == 1:
            # ESPN can encode a bye as a one-sided winners-bracket matchup.
            wins[manager_by_team[present[0]['teamId']]] += 1
        elif len(present) == 2:
            winner = str(game.get('winner') or '').upper()
            if winner == 'HOME':
                winning_team = game['home'].get('teamId')
            elif winner == 'AWAY':
                winning_team = game['away'].get('teamId')
            else:
                hp = float(game['home'].get('totalPoints') or 0)
                ap = float(game['away'].get('totalPoints') or 0)
                if abs(hp - ap) < 1e-9:
                    raise RuntimeError(f'ESPN {year}: unresolved playoff tie {game}')
                winning_team = game['home'].get('teamId') if hp > ap else game['away'].get('teamId')
            wins[manager_by_team[winning_team]] += 1

    # Some ESPN brackets omit a bye matchup entirely. First appearance in a later
    # winners-bracket round therefore represents one or more earned playoff byes.
    for team_id, rounds in appearances.items():
        first = min(rounds)
        if first > 1:
            wins[manager_by_team[team_id]] += first - 1

    print(f'ESPN {year} playoff wins incl byes:', dict(sorted(wins.items())))
    return wins


SLEEPER_CANON = {
    'mcnutted86': 'Jordan Martin',
    'peedawg': 'Payton Docheff',
    'justintreyreed': 'Bo Tiller',
    'sharkmoons': 'Bo Tiller',
    'mrplows': 'Clint Hudson',
    'pbseth': 'Seth Miller',
    'tomahawkchop6': 'Travis Page',
    'matthewmetz1985': 'Matt Metz',
    'abogueros': 'Alex Agueros',
    'imjustluke': 'Luke Miller',
    'shuturmuth': 'David Carnes',
    'rjlipkin': 'Ryan Lipkin',
    'clawdaddy69': 'Matt Clawson',
}


def sleeper_playoff_wins(year):
    user = get_json(f'{SLEEPER_BASE}/user/PBSeth')
    leagues = get_json(f"{SLEEPER_BASE}/user/{user['user_id']}/leagues/nfl/{year}")
    candidates = [l for l in leagues if 'pleb' in str(l.get('name', '')).lower()]
    if len(candidates) != 1:
        raise RuntimeError(f'Sleeper {year}: expected one Plebs league, found {len(candidates)}')
    lid = candidates[0]['league_id']
    bracket = get_json(f'{SLEEPER_BASE}/league/{lid}/winners_bracket')
    rosters = get_json(f'{SLEEPER_BASE}/league/{lid}/rosters')
    users = get_json(f'{SLEEPER_BASE}/league/{lid}/users')
    users_by_id = {u.get('user_id'): u for u in users}
    manager_by_roster = {}
    for roster in rosters:
        u = users_by_id.get(roster.get('owner_id'), {})
        handle = norm(u.get('username') or u.get('display_name'))
        manager = SLEEPER_CANON.get(handle) or canon_person(u.get('display_name'))
        if manager:
            manager_by_roster[roster.get('roster_id')] = manager

    wins = collections.Counter()
    first_round = {}
    for match in bracket:
        r = int(match.get('r') or 1)
        for key in ('t1', 't2'):
            rid = match.get(key)
            if rid in manager_by_roster:
                first_round[rid] = min(first_round.get(rid, r), r)
        winner = match.get('w')
        if winner in manager_by_roster:
            wins[manager_by_roster[winner]] += 1

    # Sleeper commonly starts bye teams in Round 2 rather than emitting a Round 1
    # bye object. Count that missing round as the required playoff win/bye credit.
    for rid, r in first_round.items():
        if r > 1:
            wins[manager_by_roster[rid]] += r - 1

    print(f'Sleeper {year} playoff wins incl byes:', dict(sorted(wins.items())))
    return wins


playoff_wins = collections.Counter()
for year in range(2019, 2024):
    playoff_wins.update(espn_playoff_wins(year))
for year in (2024, 2025):
    playoff_wins.update(sleeper_playoff_wins(year))

champ_count = collections.Counter(c['manager'] for c in champions)
regular = collections.defaultdict(lambda: {'w': 0, 'l': 0, 'seasons': 0})
for season in seasons:
    for manager, _team, w, l, _pf, _pa in season['r']:
        regular[manager]['w'] += w
        regular[manager]['l'] += l
        regular[manager]['seasons'] += 1

legacy = {}
legacy_inputs = {}
for manager, reg in regular.items():
    games = reg['w'] + reg['l']
    win_pct = reg['w'] / games if games else 0
    p_wins = int(playoff_wins.get(manager, 0))
    titles = int(champ_count.get(manager, 0))
    score = win_pct + reg['seasons'] * 0.05 + p_wins * 0.05 + titles * 0.50
    legacy[manager] = round(score, 6)
    legacy_inputs[manager] = {
        'winPct': round(win_pct, 6),
        'seasons': reg['seasons'],
        'playoffWins': p_wins,
        'titles': titles,
    }

print('Dynasty Plebs legacy scores:')
for manager, score in sorted(legacy.items(), key=lambda kv: (-kv[1], kv[0])):
    print(f'  {manager}: {score:.3f} {legacy_inputs[manager]}')

legacy_line = 'const legacyScores=' + json.dumps(legacy, separators=(',', ':'), ensure_ascii=False) + ';\nconst legacyInputs=' + json.dumps(legacy_inputs, separators=(',', ':'), ensure_ascii=False) + ';'
if re.search(r'const legacyScores=.*?;\nconst legacyInputs=.*?;', src, re.S):
    src = re.sub(r'const legacyScores=.*?;\nconst legacyInputs=.*?;', legacy_line, src, count=1, flags=re.S)
else:
    m = re.search(r'(const champions=\[.*?\];)', src, re.S)
    if not m:
        raise RuntimeError('Champions constant not found for legacy insertion')
    src = src[:m.end()] + '\n' + legacy_line + src[m.end():]

INDEX.write_text(src, encoding='utf-8')
print('Inserted exact Plebs legacy-score inputs and outputs into index.html')
