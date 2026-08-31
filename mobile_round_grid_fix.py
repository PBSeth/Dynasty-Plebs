from pathlib import Path

OLD = ".draft-intel{grid-template-columns:1fr!important}"
NEW = ".draft-intel{grid-template-columns:repeat(2,minmax(0,1fr))!important}"
FILES = [Path("index.html"), Path("final_user_notes_patch.py")]

for path in FILES:
    src = path.read_text(encoding="utf-8")
    if OLD in src:
        src = src.replace(OLD, NEW)
    elif NEW not in src:
        raise RuntimeError(f"Expected mobile draft-intel grid rule not found in {path}")
    path.write_text(src, encoding="utf-8")

print("Restored compact 2x2 mobile rookie round grid in site CSS and the source UI patch.")
