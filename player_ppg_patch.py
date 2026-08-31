from pathlib import Path

p = Path("index.html")
s = p.read_text()

old_css = ".pick b{display:block;margin-top:5px;font-size:14px}.ppg-badge{white-space:nowrap;border-radius:999px;background:#eee2cb;color:#594937;padding:3px 6px;font-size:8px;font-weight:900}"
new_css = ".pick-name-row{display:flex;align-items:center;justify-content:space-between;gap:9px;margin-top:5px}.pick-name-row b{display:block;font-size:14px;line-height:1.2;min-width:0}.ppg-badge{white-space:nowrap;flex:0 0 auto;border-radius:999px;background:#eee2cb;color:#594937;padding:4px 7px;font-size:9px;font-weight:900}"
if old_css not in s:
    raise SystemExit("rookie pick CSS target not found")
s = s.replace(old_css, new_css)

old_card = "`<div class=\"pick\" style=\"--pick-color:${managerColors[selectedManager]||'#b78a3d'}\"><div class=\"meta\"><span>${p.pick}</span>${Number.isFinite(p.ppg)?`<span class=\"ppg-badge\">3Y ${p.ppg.toFixed(1)} PPG</span>`:''}</div><b>${p.player}</b></div>`"
new_card = "`<div class=\"pick\" style=\"--pick-color:${managerColors[selectedManager]||'#b78a3d'}\"><div class=\"meta\"><span>${p.pick}</span></div><div class=\"pick-name-row\"><b>${p.player}</b>${Number.isFinite(p.ppg)?`<span class=\"ppg-badge\">3Y ${p.ppg.toFixed(1)} PPG</span>`:''}</div></div>`"
if old_card not in s:
    raise SystemExit("rookie pick card target not found")
s = s.replace(old_card, new_card)

p.write_text(s)
