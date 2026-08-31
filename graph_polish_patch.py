from pathlib import Path

p = Path('index.html')
s = p.read_text()

replacements = [
    (
        '.timeline-svg{width:100%;height:265px;display:block}',
        '.timeline-svg{width:100%;height:265px;display:block;background:#fffaf0;border:2px solid #9d8b6c;border-radius:10px;box-shadow:inset 0 0 0 1px rgba(90,72,45,.08)}'
    ),
    (
        '.axis-label{font-size:9px;fill:#817666}',
        '.axis-label{font-size:10px;fill:#675c4c;font-weight:700}'
    ),
    (
        '.point-label{font-size:8px;fill:#5d5244;font-weight:800;text-anchor:middle}',
        '.point-label{font-size:9px;fill:#4f4538;font-weight:900;text-anchor:middle}'
    ),
    (
        'color:var(--muted);font-size:9px;font-weight:900}.timeline-legend span',
        'color:#625746;font-size:10px;font-weight:900}.timeline-legend span'
    ),
    (
        '.timeline-svg{height:238px}.point-label{font-size:7px}',
        '.timeline-svg{height:242px}.point-label{font-size:8px}'
    ),
]

for old, new in replacements:
    if old in s:
        s = s.replace(old, new, 1)
    elif new not in s:
        raise SystemExit(f'Expected graph style anchor not found: {old}')

p.write_text(s)
print('Polished manager graphs: larger labels, stronger contrast, and a solid framed plotting area.')
