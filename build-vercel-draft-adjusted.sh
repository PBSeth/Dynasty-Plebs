#!/bin/sh
set -eu

# Preserve the known-good workbook-backed production build, then layer only the
# frozen, audited Draft-Adjusted PPG artifact and its presentation code on top.
sh build-vercel.sh

cp draft-adjusted-ppg.js draft-adjusted-ui.js final-ui-fix.js dist/

node <<'NODE'
const fs=require('fs');
const path='dist/index.html';
let html=fs.readFileSync(path,'utf8');
const needle='<script src="regression-fix.js?v=1"></script>';
if((html.match(new RegExp(needle.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'g'))||[]).length!==1){
  throw new Error('Expected exactly one regression-fix script tag');
}
const layered='<script src="draft-adjusted-ppg.js?v=2"></script>\n'+needle+'\n<script src="draft-adjusted-ui.js?v=2"></script>\n<script src="final-ui-fix.js?v=3"></script>';
html=html.replace(needle,layered);
fs.writeFileSync(path,html);
NODE

node --check dist/draft-adjusted-ppg.js
node --check dist/draft-adjusted-ui.js
node --check dist/final-ui-fix.js
grep -Fq 'draft-adjusted-ppg.js?v=2' dist/index.html
grep -Fq 'draft-adjusted-ui.js?v=2' dist/index.html
grep -Fq 'final-ui-fix.js?v=3' dist/index.html
grep -Fq 'draft-adjusted-ppg-v2' dist/draft-adjusted-ppg.js
grep -Fq 'Career PPG minus the expected Career PPG for a rookie at the same position and draft slot.' dist/draft-adjusted-ui.js
grep -Fq "#draftBoard .dp-compact-owner" dist/final-ui-fix.js
grep -Fq "#managerTimeline .dp-series" dist/final-ui-fix.js
