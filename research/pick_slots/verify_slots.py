"""Check recovered slots, their timing and the three recovered ownership chains."""
import argparse
import copy
import importlib.util
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('archive', ROOT / 'refresh-trade-archive.py')
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)

parser = argparse.ArgumentParser()
parser.add_argument('--cache', required=True, type=Path)
parser.add_argument('--baseline', type=Path)
args = parser.parse_args()
read = lambda path: json.loads(path.read_text())
values = read(ROOT / 'trade-valuations.json')
market = archive.snapshots(args.cache, True, read(ROOT / 'trade-value-model.json'))
assert len(values['trades']) == 241 and len(market) == 371
by_id = {t['id']: t for t in values['trades']}
recovered = 0
for trade in values['trades']:
    at = trade.get('estimatedAt', trade.get('acceptedAt'))
    for side in trade['sides']:
        for asset in side.get('assets', []):
            if not asset.get('resolvedSlot'):
                continue
            recovered += 1
            assert asset['resolvedSlot'] == asset['outcome']['slot']
            assert int(asset['resolvedSlot'].split('.')[0]) == asset['round']
            assert asset['slotKnownFrom'] == int(datetime(asset['season'], 1, 1, tzinfo=archive.CENTRAL).timestamp() * 1000)
            if asset.get('slotKnownAtTrade'):
                assert at >= asset['slotKnownFrom']
                if trade.get('dateEstimate'):
                    assert trade['dateEstimate']['earliest'] >= f"{asset['season']}-01-01"
    if not trade.get('day'):
        continue
    snapshot = market[trade['day'][0]]
    assert archive.grade(snapshot, trade, at, original=True)[0] == trade['day'][1]
    changed = copy.deepcopy(trade)
    for side in changed['sides']:
        for asset in side['assets']:
            if asset['kind'] == 'pick':
                asset['outcome'] = {'name': 'Deliberately Unpriced Future Player'}
                asset['afterDraft'] = 0
    # Eventual player identity cannot affect an original pick grade.
    assert archive.grade(snapshot, changed, at, original=True)[0] == trade['day'][1]

trade = by_id['sleeper-1205285790439981056']
assert trade['sides'][0]['assets'][0]['slotKnownAtTrade'] == '1.01'
assert [a.get('slotKnownAtTrade') for a in trade['sides'][1]['assets']] == [None, '1.02', '3.06']
assert trade['day'][1] == [6413, 11744]
probe = copy.deepcopy(trade['sides'][0]['assets'][0])
probe.pop('slotKnownAtTrade')
snapshot = market[trade['day'][0]]
assert snapshot.pick(probe, probe['slotKnownFrom'] - 1) == 4005
assert snapshot.pick(probe, probe['slotKnownFrom']) == 6413
# This date estimate straddles the offseason: do not declare its order certain.
assert not by_id['workbook-124']['sides'][1]['assets'][1].get('slotKnownAtTrade')

# The full recorded second-round path uniquely connects the three anonymous
# workbook picks. Check every original-owner transfer against its stated sender.
cache = args.cache / 'sleeper'
users = {u['user_id']: u['display_name'].lower() for u in read(cache / 'league-1180190434163908608-users.json')}
names = {r['roster_id']: archive.HANDLES[users[r['owner_id']]] for r in read(cache / 'league-1180190434163908608-rosters.json')}
raw = {}
for path in cache.glob('league-*-transactions-*.json'):
    for row in read(path):
        if row['type'] == 'trade' and row['status'] == 'complete':
            raw['sleeper-' + row['transaction_id']] = row
owners = {name: name for name in names.values()}
chain_checks = 0
for trade in sorted(values['trades'], key=lambda t: t.get('estimatedAt', t.get('acceptedAt', 0))):
    for side in trade['sides']:
        for asset in side.get('assets', []):
            if asset['kind'] != 'pick' or asset.get('season') != 2025 or asset['round'] != 2:
                continue
            origin = asset['origin']
            if trade['id'].startswith('sleeper-'):
                pick = next(p for p in raw[trade['id']]['draft_picks'] if p['season'] == '2025' and p['round'] == 2 and names[p['roster_id']] == origin)
                sender = names[pick['previous_owner_id']]
            else:
                sender = next(s['manager'] for s in trade['sides'] if s is not side)
            assert owners[origin] == sender, (trade['id'], origin, sender, owners[origin])
            owners[origin] = side['manager']
            chain_checks += 1

if args.baseline:
    old = read(args.baseline)
    assert old['market'] == values['market']
    for before in old['trades']:
        after = by_id[before['id']]
        for key in ['date', 'acceptedAt', 'estimatedAt', 'dateEstimate', 'status', 'gradeBlocked']:
            assert before.get(key) == after.get(key), (before['id'], key)
        # Recovering metadata and row 133's documented assignment must never
        # add/remove players or draft picks from the underlying exchange.
        identity = lambda a: (a['kind'], a.get('name'), a.get('season'), a.get('round'), a.get('amount'))
        assert Counter(identity(a) for s in before['sides'] for a in s['assets']) == Counter(identity(a) for s in after['sides'] for a in s['assets'])
        assert [(s['manager'], s.get('originalPackage')) for s in before['sides']] == [(s['manager'], s.get('originalPackage')) for s in after['sides']]
        if before.get('day') and not any(a['kind'] == 'pick' for s in before['sides'] for a in s['assets']):
            assert before['day'] == after['day']
print(f'Passed {recovered} recovered-slot entries, all original-grade no-hindsight checks, 241 preserved records and {chain_checks} second-round transfers.')
