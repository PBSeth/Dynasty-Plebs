import json
import re
from pathlib import Path

INDEX = Path('index.html')

src = INDEX.read_text(encoding='utf-8')

# Kevin Long was a Dynasty Plebs manager in both 2019 and 2020. The recovered
# 2020 standings row for Team Short was previously attached to Luke Miller.
# Rookie-draft ownership corroborates the handoff: Kevin made 2020 selections,
# while Luke's Plebs tenure begins in 2021.
seasons_m = re.search(r'const seasons=(\[.*?\]);\nconst champions=', src, re.S)
if not seasons_m:
    raise RuntimeError('Could not parse seasons from index.html')
seasons = json.loads(seasons_m.group(1))

y2020 = next((s for s in seasons if int(s.get('y', -1)) == 2020), None)
if not y2020:
    raise RuntimeError('2020 season not found')
rows = y2020.get('r') or []

kevin_rows = [r for r in rows if r and r[0] == 'Kevin Long']
luke_rows = [r for r in rows if r and r[0] == 'Luke Miller']

if kevin_rows:
    # Idempotent rerun: verify the corrected row is the expected Team Short season.
    if len(kevin_rows) != 1 or kevin_rows[0][1:] != ['Team Short', 8, 5, 1499.76, 1479.86]:
        raise RuntimeError(f'Unexpected Kevin Long 2020 row: {kevin_rows}')
    if luke_rows:
        raise RuntimeError(f'2020 contains both Kevin Long and Luke Miller after correction: {luke_rows}')
else:
    if len(luke_rows) != 1:
        raise RuntimeError(f'Expected one Luke Miller 2020 row to reassign, found: {luke_rows}')
    row = luke_rows[0]
    if row[1:] != ['Team Short', 8, 5, 1499.76, 1479.86]:
        raise RuntimeError(f'Luke Miller 2020 row did not match the recovered Team Short season: {row}')
    row[0] = 'Kevin Long'

# Lock the manager-tenure correction with exact season counts.
manager_seasons = {}
for season in seasons:
    for row in season.get('r', []):
        manager_seasons[row[0]] = manager_seasons.get(row[0], 0) + 1
if manager_seasons.get('Kevin Long') != 2:
    raise RuntimeError(f"Kevin Long should have 2 seasons, found {manager_seasons.get('Kevin Long')}")
if manager_seasons.get('Luke Miller') != 5:
    raise RuntimeError(f"Luke Miller should have 5 seasons (2021-2025), found {manager_seasons.get('Luke Miller')}")

seasons_json = json.dumps(seasons, separators=(',', ':'), ensure_ascii=False)
src = src[:seasons_m.start(1)] + seasons_json + src[seasons_m.end(1):]

# Compact All-Time labels requested for mobile.
src = src.replace("pf:{label:'Points For'", "pf:{label:'PF'")
src = src.replace("pa:{label:'Points Against'", "pa:{label:'PA'")

# Shared singular/plural helper for every displayed career season count.
if 'const seasonLabel=' not in src:
    anchor = "const nf=new Intl.NumberFormat('en-US',{maximumFractionDigits:2});const winDec=v=>v.toFixed(3).replace(/^0/,'');"
    if anchor not in src:
        raise RuntimeError('Could not find number-format helper anchor for seasonLabel')
    src = src.replace(anchor, anchor + "const seasonLabel=n=>`${n} ${n===1?'season':'seasons'}`;", 1)

src = src.replace("careerPct.s+' seasons'", 'seasonLabel(careerPct.s)')
src = src.replace("careerPF.s+' seasons'", 'seasonLabel(careerPF.s)')
src = src.replace("sub:x=>`${x.s} seasons`", 'sub:x=>seasonLabel(x.s)')
src = src.replace("<p>${c.s} seasons · ${h[0].year}–${latest.year}</p>", "<p>${seasonLabel(c.s)} · ${h[0].year}–${latest.year}</p>")

INDEX.write_text(src, encoding='utf-8')
print('Corrected 2020 Team Short ownership: Kevin Long (2 seasons); Luke Miller begins 2021 (5 seasons).')
print('All-Time labels use PF / PA and career season counts use singular/plural grammar.')
