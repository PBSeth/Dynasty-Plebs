from pathlib import Path
code=Path('patch_rookies.py').read_text()
old="s2=re.sub(r'function renderDraftIntel\\(\\)\\{.*?\\n\\}',new,s,count=1,flags=re.S)"
new="s2=re.sub(r'function renderDraftIntel\\(\\)\\{.*?(?=function renderRookies\\(\\)\\{)',new+'\\n',s,count=1,flags=re.S)"
if old not in code:
    raise SystemExit('target patch expression not found')
exec(compile(code.replace(old,new),'patch_rookies.py','exec'))
