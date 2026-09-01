import json
import re
from pathlib import Path

INDEX = Path('index.html')

# SOURCE OF TRUTH: Dynasty Plebs Google Sheet.
# This table is a frozen integrity snapshot of manager participation by season.
# Do not change it from screenshots, Sleeper handles, inferred ownership, or site output.
# Update only after reconciling against the Google Sheet north star.
EXPECTED_YEARS = {
    'Alex Agueros': [2019, 2020, 2021, 2022, 2023, 2024, 2025],
    'Bo Tiller': [2019, 2020, 2021, 2022, 2023, 2024, 2025],
    'Clint Hudson': [2023, 2024, 2025],
    'David Carnes': [2019, 2020, 2021, 2022, 2023, 2024, 2025],
    'Jordan Martin': [2019, 2020, 2021, 2022, 2023, 2024, 2025],
    'Kevin Long': [2019, 2020],
    'Luke Miller': [2021, 2022, 2023, 2024, 2025],
    'Mason Good': [2019, 2020, 2021],
    'Matt Clawson': [2019, 2020, 2021, 2022, 2023, 2024, 2025],
    'Matt Metz': [2019, 2020, 2021, 2022, 2023, 2024, 2025],
    'Matthew Piontek': [2019, 2020, 2021],
    'Payton Docheff': [2019, 2020, 2021, 2022, 2023, 2024, 2025],
    'Ryan Lipkin': [2024, 2025],
    'Seth Miller': [2019, 2020, 2021, 2022, 2023, 2024, 2025],
    'Tim Bell': [2022],
    'Travis Page': [2019, 2020, 2021, 2022, 2023, 2024, 2025],
}

EXPECTED_MANAGERS_BY_YEAR = {
    2019: {'David Carnes','Bo Tiller','Matt Metz','Travis Page','Matthew Piontek','Jordan Martin','Alex Agueros','Matt Clawson','Mason Good','Seth Miller','Payton Docheff','Kevin Long'},
    2020: {'Matthew Piontek','Seth Miller','David Carnes','Mason Good','Travis Page','Bo Tiller','Jordan Martin','Kevin Long','Matt Clawson','Alex Agueros','Matt Metz','Payton Docheff'},
    2021: {'Matthew Piontek','Seth Miller','Alex Agueros','Bo Tiller','Matt Metz','Jordan Martin','Mason Good','David Carnes','Matt Clawson','Travis Page','Luke Miller','Payton Docheff'},
    2022: {'Seth Miller','Matt Metz','Tim Bell','Bo Tiller','Jordan Martin','Payton Docheff','Alex Agueros','Luke Miller','Travis Page','David Carnes','Matt Clawson'},
    2023: {'Jordan Martin','Seth Miller','Travis Page','Payton Docheff','Matt Metz','Bo Tiller','Matt Clawson','Clint Hudson','David Carnes','Alex Agueros','Luke Miller'},
    2024: {'Travis Page','Jordan Martin','Matt Metz','Matt Clawson','Seth Miller','Payton Docheff','Bo Tiller','Clint Hudson','Alex Agueros','Luke Miller','David Carnes','Ryan Lipkin'},
    2025: {'Travis Page','Matt Metz','Seth Miller','Jordan Martin','Clint Hudson','Payton Docheff','Bo Tiller','Matt Clawson','Luke Miller','Alex Agueros','David Carnes','Ryan Lipkin'},
}

src = INDEX.read_text(encoding='utf-8')
m = re.search(r'const seasons=(\[.*?\]);\nconst champions=', src, re.S)
if not m:
    raise RuntimeError('Could not parse seasons from index.html')
seasons = json.loads(m.group(1))

actual_years = {}
for season in seasons:
    year = int(season['y'])
    actual_names = [row[0] for row in season.get('r', [])]
    if len(actual_names) != len(set(actual_names)):
        raise RuntimeError(f'{year}: duplicate manager identity found: {actual_names}')
    expected = EXPECTED_MANAGERS_BY_YEAR.get(year)
    if expected is None:
        raise RuntimeError(f'{year}: season is not represented in the Google-Sheet manager-history snapshot')
    if set(actual_names) != expected:
        missing = sorted(expected - set(actual_names))
        extra = sorted(set(actual_names) - expected)
        raise RuntimeError(f'{year}: manager history drifted from Google Sheet. Missing={missing}; Extra={extra}')
    for name in actual_names:
        actual_years.setdefault(name, []).append(year)

actual_years = {k: sorted(v) for k, v in actual_years.items()}
if actual_years != EXPECTED_YEARS:
    all_names = sorted(set(actual_years) | set(EXPECTED_YEARS))
    drift = {
        name: {'expected': EXPECTED_YEARS.get(name), 'actual': actual_years.get(name)}
        for name in all_names
        if EXPECTED_YEARS.get(name) != actual_years.get(name)
    }
    raise RuntimeError(f'Manager tenure drifted from Google Sheet north star: {drift}')

print('Manager-history audit passed against frozen Google Sheet north-star snapshot.')
print('Kevin Long: 2019-2020 (2 seasons); Luke Miller: 2021-2025 (5 seasons); Tim Bell: 2022 (1 season).')
