const assert = require('node:assert/strict');
const fs = require('node:fs');
const { evaluate, checkpoints } = require('../../trade-metrics.js');
const market = ['2020-02-29','2021-02-26','2021-03-05','2023-02-24','2023-03-03','2024-02-23','2024-03-01'].map(date=>[date,'',Date.parse(date+'T12:00:00Z')]);
const base = {date:'2020-02-29',sides:[{manager:'A',assets:[]},{manager:'B',assets:[]}],day:[0,[100,200]],timeline:[[1,120,210],[2,9999,1],[3,160,220],[4,99999,1],[5,180,240],[6,0,0]]};
const snapshot=JSON.stringify(base);
const closed=checkpoints(evaluate(base,market));
assert.deepEqual(closed.map(p=>p.name),['At trade','1 year','At cutoff']);
assert.equal(closed[1].targetDate,'2021-02-28');
assert.equal(closed[1].point.date,'2021-02-26');
assert.equal(closed[2].point.date,'2023-02-24');
assert.equal(closed[2].milestone,'3 years');
assert.equal(JSON.stringify(base),snapshot);
const active=checkpoints(evaluate(base,market.slice(0,1)));
assert.deepEqual(active.map(p=>p.name),['At trade','1 year','3 years','Now']);
assert.equal(active[1].upcoming,true);
assert.equal(active[1].point,null);
assert.equal(active[2].upcoming,true);
const extended=structuredClone(base);
extended.sides[1].assets=[{kind:'pick',season:2022}];
const pickClosed=checkpoints(evaluate(extended,market));
assert.deepEqual(pickClosed.map(p=>p.name),['At trade','1 year','3 years','At cutoff']);
assert.equal(pickClosed[2].point.date,'2023-02-24');
assert.equal(pickClosed[3].point.date,'2024-02-23');
const gap=structuredClone(base);
gap.timeline[0]=[1,null,210];
assert.equal(checkpoints(evaluate(gap,market))[1].point.changes[0],null);
const stale={...base,timeline:base.timeline.filter(p=>p[0]!==1)};
assert.equal(checkpoints(evaluate(stale,market))[1].point,null,'do not borrow the post-anniversary spike');
const blocked=checkpoints(evaluate({...base,gradeBlocked:true},market));
assert.ok(blocked.every(p=>!p.point));
const unknown=checkpoints(evaluate({...base,date:undefined},market));
assert.ok(unknown.every(p=>!p.point));
const data=JSON.parse(fs.readFileSync('trade-valuations.json','utf8'));
let checked=0;
for(const trade of data.trades.filter(t=>t.status!=='reversed')){
 const e=evaluate(trade,data.market), c=checkpoints(e);
 assert.equal(c.filter(p=>p.key==='endpoint').length,1);
 if(e.window.closed && !e.window.extended) assert.equal(c.length,3);
 for(const p of c){
  if(!p.point) continue;
  assert.ok(e.points.includes(p.point));
  assert.ok(p.point.date<=p.targetDate);
  assert.ok(p.point.date<=e.window.endDate);
 }
 checked++;
}
console.log(`Passed anniversary snapshots, leap days, upcoming dates, cutoff deduplication, future-pick extensions, missing/stale prices, and ${checked} archived trades.`);
