import json,re
from pathlib import Path

p=Path('index.html')
s=p.read_text()

# Re-decoded directly from the 2025 Google Sheet cell colors.
# Left Pick Order column is the color legend; player-cell fill is the actual owner.
audited_2025=[
    ["Seth Miller","David Carnes","Alex Agueros","Luke Miller","Matt Clawson","Clint Hudson","Bo Tiller","David Carnes","Matt Metz","Ryan Lipkin","Matt Metz","David Carnes"],
    ["David Carnes","Alex Agueros","Alex Agueros","David Carnes","David Carnes","Clint Hudson","Bo Tiller","Matt Clawson","Clint Hudson","Ryan Lipkin","Ryan Lipkin","Alex Agueros"],
    ["Luke Miller","Luke Miller","Alex Agueros","Ryan Lipkin","Travis Page","Travis Page","Bo Tiller","Luke Miller","Matt Metz","Luke Miller","David Carnes","Ryan Lipkin"],
    ["Seth Miller","Seth Miller","Seth Miller","Ryan Lipkin","Luke Miller","Clint Hudson","Bo Tiller","Payton Docheff","Matt Metz","Seth Miller","Matt Metz","Matt Metz"],
    ["Seth Miller","Alex Agueros","Alex Agueros","Luke Miller","Travis Page","Clint Hudson","Bo Tiller","Payton Docheff","Matt Metz","Ryan Lipkin","Payton Docheff","Ryan Lipkin"]
]

m=re.search(r'const rookieBoards=(\{.*?\});\nconst nf=',s,re.S)
if not m:
    raise SystemExit('rookieBoards not found')
boards=json.loads(m.group(1))
if '2025' not in boards:
    raise SystemExit('2025 rookie board not found')
boards['2025']['ownersByRound']=audited_2025

# Hard sanity check from the source screenshot: Jaxson Dart is the 7th Round 3 cell,
# whose dark-brown fill matches Bo Tiller in the Pick Order color legend.
players=boards['2025']['rounds'][2]
idx=players.index('Jaxson Dart')
assert audited_2025[2][idx]=='Bo Tiller'

s=s[:m.start(1)]+json.dumps(boards,separators=(',',':'))+s[m.end(1):]
p.write_text(s)
print('Applied audited 2025 ownership map; Jaxson Dart -> Bo Tiller')
