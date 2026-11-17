const assert = require('node:assert/strict');
const fs = require('node:fs');
const { analyze, margin } = require('../../trade-metrics.js');
const sides = [{manager:'A'}, {manager:'B'}];
const source = [
  { date:'2020-01-01', original:true, values:[100,200] },
  { date:'2020-02-01', values:[120,210] },
  { date:'2020-03-01', values:[160,220] }
];
const result = analyze(source, sides);
assert.deepEqual(result.points.map(p => p.changes), [[0,0],[20,10],[60,20]]);
assert.equal(margin(result.latest.changes,0),40);
assert.equal(margin(result.latest.values,0),-60);
assert.equal(result.peaks[0],result.points[2]);
assert.equal(result.peaks[1],result.baseline);
assert.equal(source[0].changes,undefined);
const missing = analyze([{original:true,values:[100,null]},{values:[120,210]}],sides);
assert.deepEqual(missing.latest.changes,[20,null]);
assert.equal(missing.peaks[0],null);
assert.equal(missing.peaks[1],null);
assert.deepEqual(analyze([{values:[120,210]}],sides).points[0].changes,[null,null]);
const archive = JSON.parse(fs.readFileSync('trade-valuations.json','utf8'));
let checked=0;
for(const t of archive.trades){
 const points=[];
 if(t.day) points.push({original:true,date:t.date,values:t.day[1]});
 points.push(...(t.timeline||[]).map(([i,...values])=>({date:archive.market[i][0],values})));
 const a=analyze(points,t.sides);
 if(a.baseline) a.baseline.changes.forEach(v=>assert.ok(v===null||v===0));
 for(const p of a.points) p.changes.forEach((v,i)=>{
  if(v!==null) assert.equal(v,p.values[i]-a.baseline.values[i]);
 });
 if(t.id==='sleeper-1412868254434676736'){
  assert.deepEqual(a.latest.changes,[1428,115]);
  assert.equal(margin(a.latest.changes,0),1313);
  assert.equal(margin(a.baseline.values,0),1378);
 }
 checked++;
}
console.log(`Verified trade-day zero, gains vs raw prices, both manager peaks, missing-data guards, and ${checked} archive records.`);
