const assert = require('node:assert/strict');
const fs = require('node:fs');
const { evaluate, evaluationWindow, complete } = require('../../trade-metrics.js');
const market = ['2020-03-11','2021-03-11','2023-03-10','2023-03-11','2023-03-12',
  '2024-02-28','2024-02-29','2024-03-01','2026-11-13'].map(date => [date, '', Date.parse(date+'T12:00:00Z')]);
const base = { date:'2020-03-11', sides:[{manager:'A',assets:[]},{manager:'B',assets:[]}],
  day:[0,[150,200]],dayAdjustments:[50,0],timeline:[[1,120,210],[2,160,220],[3,170,230],
  [4,99999,1],[5,180,225],[6,190,230],[7,999999,1],[8,0,0]] };
const before = JSON.stringify(base);
const a = evaluate(base,market);
assert.equal(a.window.cutoffDate,'2023-03-11');
assert.equal(a.window.closed,true);
assert.equal(a.window.extended,false);
assert.equal(a.latest.date,'2023-03-11');
assert.deepEqual(a.latest.changes,[70,30]);
assert.equal(a.peaks[0].date,'2023-03-10'); // Keep the earliest date of a tied peak.
assert.ok(a.points.every(p=>p.date<=a.window.cutoffDate));
assert.equal(JSON.stringify(base),before,'source history must remain intact');
assert.deepEqual(a.baseline.values,[150,200],'original grade retains allowance');

// Future selections get two full seasons, including February. Neither player
// identity, draft timestamp nor eventual performance determines the cutoff.
const pick = structuredClone(base);
pick.sides[1].assets=[{kind:'pick',season:2022,round:1,afterDraft:0,outcome:{name:'Star'}}];
const b = evaluate(pick,market);
assert.equal(b.window.cutoffDate,'2024-02-29');
assert.equal(b.window.extended,true);
assert.equal(b.latest.date,'2024-02-29');
pick.sides[1].assets[0].outcome={name:'Bust'};
pick.sides[1].assets[0].afterDraft=9999999999999;
assert.deepEqual(evaluate(pick,market).window,b.window);
pick.sides[0].assets=[{kind:'pick',season:2021,round:4}];
assert.equal(evaluate(pick,market).window.cutoffDate,'2024-02-29');
assert.equal(evaluationWindow({date:'2025-03-11',sides:[{assets:[{kind:'pick',season:2027}]}]},'2030-01-01').cutoffDate,'2029-02-28');
assert.equal(evaluationWindow({date:'2020-02-29',sides:[]},'2026-01-01').cutoffDate,'2023-02-28');
assert.equal(evaluationWindow({...base,date:'2020-02-30'},'2026-01-01').valid,false);
assert.equal(evaluationWindow({...base,date:undefined},'2026-01-01').valid,false);
assert.equal(evaluationWindow({...base,sides:[{assets:[{kind:'pick'}]}]},'2026-01-01').valid,false);
assert.equal(evaluate({...base,dateEstimate:{earliest:'2020-02-01',latest:'2020-04-01'}},market).window.estimated,true);

// Active windows use only the latest published snapshot, not the wall clock
// or an invented point at the future deadline.
const activeMarket=market.slice(0,2);
const active=evaluate(base,activeMarket);
assert.equal(active.window.closed,false);
assert.equal(active.window.endDate,'2021-03-11');
assert.equal(active.latest.date,'2021-03-11');
assert.equal(active.points.length,2);
assert.equal(evaluate({...base,gradeBlocked:true},market).latest,null);

// No post-cutoff filling, nearest-complete substitution or stale frozen grade.
const gap=structuredClone(base);
gap.timeline[2]=[3,null,230];
const c=evaluate(gap,market);
assert.equal(c.latest.date,'2023-03-11');
assert.deepEqual(c.latest.changes,[null,30]);
assert.equal(complete(c.latest.changes),false);
const stale=evaluate({...base,timeline:[[1,120,210],[4,99999,1]]},market);
assert.equal(stale.latest,null);
assert.equal(stale.window.stale,true);
const missingBase=evaluate({...base,day:[0,[null,200]]},market);
assert.equal(complete(missingBase.latest.changes),false);
assert.ok(missingBase.peaks.every(p=>p===null));
const multi=evaluate({...base,sides:[...base.sides,{manager:'C',assets:[]}],
  day:[0,[100,200,300]],dayAdjustments:[],timeline:[[3,130,210,315],[4,0,99999,0]]},market);
assert.equal(multi.latest.date,'2023-03-11');
assert.equal(multi.peaks[0].date,'2023-03-11');

const archive=JSON.parse(fs.readFileSync('trade-valuations.json','utf8'));
let ended=0,activeCount=0,extended=0,missingEndpoint=0;
for(const trade of archive.trades.filter(t=>t.status!=='reversed')){
  const e=evaluate(trade,archive.market);
  if(!e.window.valid) continue;
  if(e.window.closed) ended++; else activeCount++;
  if(e.window.extended) extended++;
  if(!e.latest || !complete(e.latest.changes)) missingEndpoint++;
  for(const point of e.points){
    assert.ok(point.date>=trade.date && point.date<=e.window.endDate,trade.id);
  }
  for(const point of [e.latest,...e.peaks].filter(Boolean)) assert.ok(e.points.includes(point),trade.id);
  assert.ok(!e.latest || !e.latest.original);
}
console.log(JSON.stringify({verified:'bounded graph, all lenses, original grades, future picks, leap days, missing endpoints, source preservation, and full archive',ended,active:activeCount,extended,missingEndpoint}));
