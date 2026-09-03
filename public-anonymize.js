const fs=require('fs');
const path=require('path');

const root=path.resolve('dist');
if(!fs.existsSync(root))throw new Error('dist/ missing; refusing to anonymize outside built artifact');

// Public demo aliases only. This file exists on the public-generic branch, never main.
// Dave/David Carnes are intentionally the same alias.
const aliases={
  'Seth Miller':'Manager A',
  'Travis Page':'Manager B',
  'Matt Metz':'Manager C',
  'Jordan Martin':'Manager D',
  'Payton Docheff':'Manager E',
  'Bo Tiller':'Manager F',
  'Matt Clawson':'Manager G',
  'Alex Agueros':'Manager H',
  'Luke Miller':'Manager I',
  'Dave Carnes':'Manager J',
  'David Carnes':'Manager J',
  'Clint Hudson':'Manager K',
  'Ryan Lipkin':'Manager L',
  'Matthew Piontek':'Manager M',
  'Mason Good':'Manager N',
  'Kevin Long':'Manager O',
  'Tim Bell':'Manager P',
  'Josh Ponath':'Manager Q'
};

const textExt=new Set(['.html','.js','.css','.json','.webmanifest','.svg','.txt']);
const files=[];
function walk(dir){
  for(const ent of fs.readdirSync(dir,{withFileTypes:true})){
    const full=path.join(dir,ent.name);
    if(ent.isDirectory())walk(full);
    else if(textExt.has(path.extname(ent.name).toLowerCase())||ent.name.endsWith('.webmanifest'))files.push(full);
  }
}
walk(root);

const pairs=Object.entries(aliases).sort((a,b)=>b[0].length-a[0].length);
for(const file of files){
  let s=fs.readFileSync(file,'utf8');
  for(const [real,alias] of pairs)s=s.split(real).join(alias);
  fs.writeFileSync(file,s);
}

// Hard privacy gate: a public build fails if any known real manager name survives.
const leaks=[];
for(const file of files){
  const s=fs.readFileSync(file,'utf8');
  for(const real of Object.keys(aliases))if(s.includes(real))leaks.push(`${path.relative(root,file)}: ${real}`);
}
if(leaks.length)throw new Error('Public-name anonymization leak:\n'+leaks.join('\n'));

// Visible marker without altering the Dynasty Plebs branding.
const index=path.join(root,'index.html');
let html=fs.readFileSync(index,'utf8');
html=html.replace('<title>Dynasty Plebs</title>','<title>Dynasty Plebs — Public Demo</title>');
html=html.replace('</head>','<meta name="robots" content="noindex,nofollow">\n</head>');
fs.writeFileSync(index,html);

console.log(`Public demo anonymized: ${Object.keys(aliases).length} manager-name variants across ${files.length} built text assets.`);
console.log('Privacy gate passed: no known real manager names remain in dist/.');
