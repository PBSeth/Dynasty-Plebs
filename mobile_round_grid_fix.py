from pathlib import Path

INDEX = Path("index.html")
src = INDEX.read_text(encoding="utf-8")

old = ".draft-intel{grid-template-columns:1fr!important}"
new = ".draft-intel{grid-template-columns:repeat(2,minmax(0,1fr))!important}"

if old in src:
    src = src.replace(old, new, 1)
elif new not in src:
    raise RuntimeError("Expected mobile draft-intel grid rule not found")

INDEX.write_text(src, encoding="utf-8")
