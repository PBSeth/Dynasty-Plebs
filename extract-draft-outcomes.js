const fs=require('fs');
const src=fs.readFileSync('index.html','utf8');
const start='const careerDraftStats=';
const end=';\nconst rookieBoards=';
const a=src.indexOf(start),b=src.indexOf(end,a+start.length);
if(a<0||b<0)throw new Error('careerDraftStats source block not found');
const obj=src.slice(a+start.length,b);
fs.writeFileSync('dist/draft-outcomes.js',`window.DRAFT_OUTCOMES=${obj};\n`);
console.log('Draft outcome supplemental data extracted.');
