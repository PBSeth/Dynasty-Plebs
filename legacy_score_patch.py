import collections
import json
import re
import urllib.request
from pathlib import Path

INDEX = Path('index.html')
SLEEPER_BASE = 'https://api.sleeper.app/v1'

# Dynasty Plebs uses the exact Fantasy Ranch Legacy Score formula:
# Score = RegSeasonWinPct * (1 + .05*ServiceTime + .05*PlayoffWins + .50*Championships) * 1000
# Playoff bye weeks count as playoff wins.
#
# ESPN 2019-2023 is locked from the supplied Final Standings. In a six-team playoff,
# final playoff place determines wins including byes: champion=3, runner-up=2,
# semifinal losers (3rd/4th)=1, quarterfinal losers (5th/6th)=0.

ESPN_PLAYOFF_WINS = {
    2019: {
        'David Carnes': 3,
        'Bo Tiller': 2,
        'Matt Metz': 1,
        'Travis Page': 1,
    },
    2020: {
        'Matthew Piontek': 3,
        'Seth Miller': 2,
        'David Carnes': 1,
        'Mason Good': 1,
    },
    2021: {
        'Matthew Piontek': 3,
        'Seth Miller': 2,
        'Alex Agueros': 1,
        'Bo Tiller': 1,
    },
    2022: {
        'Seth Miller': 3,
        'Matt Metz': 2,
        'Tim Bell': 1,
        'Bo Tiller': 1,
    },
    2023: {
        'Jordan Martin': 3,
        'Seth Miller': 2,
        'Travis Page': 1,
        'Payton Docheff': 1,
    },
}

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


def canon_person(value):
    n = norm(value)
    aliases = {
        'matthewmetz': 'Matt Metz',
        'mattmetz': 'Matt Metz',
        'matthewpiontek': 'Matthew Piontek',
        'davidcarnes': 'David Carnes',
        'mattclawson': 'Matt Clawson',
        'paytondocheff': 'Payton Docheff',
    }
    return canonical_names.get(n) or aliases.get(n)


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

    # Sleeper normally omits a Round 1 object for bye teams. The missing first round
    # therefore earns one playoff-win credit, matching the locked league formula.
    for rid, r in first_round.items():
        if r > 1:
            wins[manager_by_roster[rid]] += r - 1

    print(f'Sleeper {year} playoff wins incl byes:', dict(sorted(wins.items())))
    return wins


playoff_wins = collections.Counter()
for year, values in ESPN_PLAYOFF_WINS.items():
    playoff_wins.update(values)
    print(f'ESPN {year} playoff wins incl byes:', values)
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
    service_time = reg['seasons']
    p_wins = int(playoff_wins.get(manager, 0))
    titles = int(champ_count.get(manager, 0))
    multiplier = 1 + (service_time * 0.05) + (p_wins * 0.05) + (titles * 0.50)
    score = win_pct * multiplier * 1000
    legacy[manager] = round(score, 3)
    legacy_inputs[manager] = {
        'winPct': round(win_pct, 6),
        'serviceTime': service_time,
        'playoffWins': p_wins,
        'titles': titles,
        'multiplier': round(multiplier, 3),
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
