#!/bin/sh
set -eu

# Preserve the known-good workbook-backed production build, then layer only the
# frozen, audited Draft-Adjusted PPG artifact and the stable final presentation layer.
sh build-vercel.sh

cp draft-adjusted-ppg.js draft-adjusted-ui.js final-ui-stable.js legacy-axis-fix.js manifest.webmanifest plebs-icon.svg dist/

node <<'NODE'
const fs=require('fs');
const path='dist/index.html';
let html=fs.readFileSync(path,'utf8');
const needle='<script src="regression-fix.js?v=1"></script>';
if((html.match(new RegExp(needle.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'g'))||[]).length!==1){
  throw new Error('Expected exactly one regression-fix script tag');
}
const layered='<script src="draft-adjusted-ppg.js?v=2"></script>\n'+needle+'\n<script src="draft-adjusted-ui.js?v=2"></script>';
html=html.replace(needle,layered);
const headLayers='\n<link rel="manifest" href="/manifest.webmanifest?v=1">\n<link rel="icon" type="image/svg+xml" href="/plebs-icon.svg?v=1">\n<meta name="apple-mobile-web-app-capable" content="yes">\n<meta name="apple-mobile-web-app-title" content="Dynasty Plebs">\n';
if(!html.includes('</head>'))throw new Error('Expected closing head tag');
html=html.replace('</head>',headLayers+'</head>');
const endLayers='<script src="final-ui-stable.js?v=2"></script>\n<script src="legacy-axis-fix.js?v=1"></script>\n';
if(!html.includes('</body>'))throw new Error('Expected closing body tag');
html=html.replace('</body>',endLayers+'</body>');
fs.writeFileSync(path,html);
NODE

node --check dist/draft-adjusted-ppg.js
node --check dist/draft-adjusted-ui.js
node --check dist/final-ui-stable.js
node --check dist/legacy-axis-fix.js
grep -Fq 'draft-adjusted-ppg.js?v=2' dist/index.html
grep -Fq 'draft-adjusted-ui.js?v=2' dist/index.html
grep -Fq 'final-ui-stable.js?v=2' dist/index.html
grep -Fq 'legacy-axis-fix.js?v=1' dist/index.html
grep -Fq 'manifest.webmanifest?v=1' dist/index.html
grep -Fq 'plebs-icon.svg?v=1' dist/index.html
grep -Fq 'draft-adjusted-ppg-v2' dist/draft-adjusted-ppg.js
grep -Fq 'Career PPG minus the expected Career PPG for a rookie at the same position and draft slot.' dist/draft-adjusted-ui.js
grep -Fq '#draftBoard .dp-compact-owner' dist/final-ui-stable.js
grep -Fq '#managerTimeline .dp-series' dist/final-ui-stable.js
grep -Fq 'Avg PF/Game' dist/final-ui-stable.js
grep -Fq 'Draft Class Average' dist/final-ui-stable.js
grep -Fq 'activeFirstSort' dist/final-ui-stable.js
grep -Fq 'dp-intel-card>b' dist/final-ui-stable.js
grep -Fq 'STEP=500' dist/legacy-axis-fix.js
