const fs=require('fs');
const path='dist/index.html';
let html=fs.readFileSync(path,'utf8');
const logoBrand=/<a class="brand dp-brand-logo" href="#" aria-label="Dynasty Plebs"><img src="\/plebs-logo\.svg\?v=\d+" alt="Dynasty Plebs"><\/a>/;
if(!logoBrand.test(html)) throw new Error('Expected generated Dynasty Plebs image header');
html=html.replace(logoBrand,'<a class="brand" href="#"><strong>Dynasty Plebs</strong><small>Est. 2019</small></a>');
fs.writeFileSync(path,html);
