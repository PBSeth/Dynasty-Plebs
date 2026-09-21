const fs=require('fs');
const src=fs.readFileSync('index.html','utf8');
const start='const careerDraftStats=';
const end=';\nconst rookieBoards=';
const a=src.indexOf(start),b=src.indexOf(end,a+start.length);
if(a<0||b<0)throw new Error('careerDraftStats source block not found');
const obj=src.slice(a+start.length,b);
const outcomes=JSON.parse(obj);

for(const [key,row] of Object.entries(outcomes)){
  if(row?.excluded==='veteran')continue;
  if(Number.isFinite(row?.games)&&row.games<0)throw new Error(`Negative games in ${key}`);
  if(Number.isFinite(row?.games)&&row.games>0){
    if(!Number.isFinite(row.points)||!Number.isFinite(row.ppg))throw new Error(`Incomplete scored outcome in ${key}`);
    const expected=row.points/row.games;
    if(Math.abs(expected-row.ppg)>0.00001)throw new Error(`Career PPG math drift in ${key}: ${row.points}/${row.games} != ${row.ppg}`);
  }
}

const etienne=outcomes['2021|travisetienne'];
if(!etienne||etienne.games!==66||Math.abs(etienne.points-787.6)>0.001||Math.abs(etienne.ppg-11.933333)>0.00001){
  throw new Error(`Travis Etienne career denominator regression: ${JSON.stringify(etienne)}`);
}
const burrow=outcomes['2020|joeburrow'];
if(!burrow||burrow.games!==77||Math.abs(burrow.ppg-22.251688)>0.00001){
  throw new Error(`Joe Burrow career denominator regression: ${JSON.stringify(burrow)}`);
}

fs.writeFileSync('dist/draft-outcomes.js',`window.DRAFT_OUTCOMES=${obj};\n`);
console.log(`Draft outcome supplemental data extracted and audited (${Object.keys(outcomes).length} rows).`);
