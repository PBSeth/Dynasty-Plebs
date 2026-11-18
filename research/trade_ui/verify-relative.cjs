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
const allowances = analyze([
 {original:true,values:[150,200],adjustments:[50,0]},
 {values:[220,210],adjustments:[100,0]},
 {values:[160,220]}
],sides);
assert.deepEqual(allowances.points.map(p=>p.changes),[[0,0],[20,10],[60,20]]);
assert.deepEqual(allowances.baseline.values,[150,200]);
assert.equal(allowances.peaks[0],allowances.points[2]);
assert.deepEqual(analyze([{original:true,values:[100,null],adjustments:[10,0]},
 {values:[120,210],adjustments:[20,0]}],sides).latest.changes,[10,null]);
const archive = JSON.parse(fs.readFileSync('trade-valuations.json','utf8'));
let checked=0;
for(const t of archive.trades){
 const points=[];
 const adjustments=new Map((t.timelineAdjustments||[]).map(([i,...values])=>[i,values]));
 if(t.day) points.push({original:true,date:t.date,values:t.day[1],adjustments:t.dayAdjustments});
 points.push(...(t.timeline||[]).map(([i,...values])=>({date:archive.market[i][0],values,adjustments:adjustments.get(i)})));
 const a=analyze(points,t.sides);
 if(a.baseline) a.baseline.changes.forEach(v=>assert.ok(v===null||v===0));
 for(const p of a.points) p.changes.forEach((v,i)=>{
  if(v!==null) assert.equal(v,p.values[i]-(p.adjustments?.[i]??0)-
    (a.baseline.values[i]-(a.baseline.adjustments?.[i]??0)));
 });
 if(t.id==='sleeper-1412868254434676736'){
  assert.deepEqual(a.latest.changes,[841,115]);
  assert.equal(margin(a.latest.changes,0),726);
  assert.equal(margin(a.baseline.values,0),1378);
 }
 if(t.id==='sleeper-1205285790439981056'){
  assert.deepEqual(a.latest.assetValues,[6908,8220]);
  assert.deepEqual(a.latest.changes,[495,-3524]);
  assert.equal(margin(a.latest.changes,0),4019);
  assert.equal(margin(a.latest.assetValues,0),-1312);
 }
 checked++;
}
console.log(`Verified trade-day zero, gains vs raw prices, both manager peaks, missing-data guards, and ${checked} archive records.`);
