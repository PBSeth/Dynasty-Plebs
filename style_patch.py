from pathlib import Path

p = Path("index.html")
s = p.read_text()

repls = {
    '.champion-card h3{position:relative;z-index:1;margin:7px 0 2px;font:800 18px/1.05 Georgia,serif}':
    '.champion-card h3{position:relative;z-index:1;margin:7px 0 2px;font:800 clamp(13px,2.4vw,18px)/1 Georgia,serif;white-space:nowrap;letter-spacing:-.015em}',
    '.axis-label{font-size:9px;fill:#817666}':
    '.axis-label{font-size:12px;fill:#6f6353;font-weight:700}',
    '.point-label{font-size:8px;fill:#5d5244;font-weight:800;text-anchor:middle}':
    '.point-label{font-size:12px;fill:#3f3529;font-weight:900;text-anchor:middle}',
    '.point-label{font-size:7px}':
    '.point-label{font-size:10px}',
    '<p>Year-by-year regular-season performance. Every manager uses the same scale for each metric.</p>':
    '<p>Year-by-year regular-season performance.</p>',
    '<div class="scale-note">Fixed league-wide scale · identical for every manager</div>':
    ''
}

for old, new in repls.items():
    if old not in s:
        raise SystemExit(f"Expected style target not found: {old[:80]}")
    s = s.replace(old, new)

p.write_text(s)
