const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const metrics = require('../../trade-metrics.js');
const archive = JSON.parse(fs.readFileSync('trade-valuations.json','utf8'));
const source = fs.readFileSync('trade-review.js','utf8');
const controls = Object.fromEntries(['managerSelect','tradePartner','tradeSearch','tradeSeason','tradeSort','tradeCount','tradeResults','tradeDetail','trades'].map(id=>[id,{value:''}]));
controls.managerSelect.value='Seth Miller';
controls.tradeSort.value='recent';
controls.tradeResults.replaceChildren=(...rows)=>{ controls.tradeResults.rows=rows; };
const window={PLEBS_TRADE_METRICS:metrics};
const document={querySelector:()=>({}),getElementById:id=>controls[id],createElement:()=>({innerHTML:''})};
const script=source.slice(0,source.indexOf('  function renderDetail()'))+`
  function renderDetail() {}
  window.listTest={prepare(data){market=data.market;trades=data.trades.filter(t=>t.status!=='reversed').map(learnTrade);},renderList,currentStanding,learnTrade,getTrade(id){return trades.find(t=>t.id===id);}};
})();`;
vm.runInNewContext(script,{document,window,Intl,location:{hash:'#managers/Seth%20Miller/trades'},history:{replaceState(){}}});
const api=window.listTest;
api.prepare(archive);
controls.tradePartner.value='Payton Docheff';
api.renderList();
assert.equal(controls.tradeCount.textContent,'13 trades');
for(const row of controls.tradeResults.rows){
 assert.match(row.innerHTML,/trade-list-edge/);
 assert.match(row.innerHTML,/>Now<\/small>/);
 if(!row.innerHTML.includes('Matthew Piontek')) assert.doesNotMatch(row.innerHTML,/class="trade-list-partner"/);
}
controls.tradePartner.value='';
api.renderList();
assert.ok(controls.tradeResults.rows.every(row=>row.innerHTML.includes('class="trade-list-partner"')));
const recoveredFourth=controls.tradeResults.rows.find(row=>row.innerHTML.includes('trades/workbook-160"'));
assert.match(recoveredFourth.innerHTML,/2025 4\.05/);
assert.match(recoveredFourth.innerHTML,/\+1,551/);
const woods=controls.tradeResults.rows.find(row=>row.innerHTML.includes('trades/workbook-109"'));
assert.match(woods.innerHTML,/2023 2\.01/);
assert.match(woods.innerHTML,/\+2,887/);
const kamara=controls.tradeResults.rows.find(row=>row.innerHTML.includes('trades/workbook-122"'));
assert.match(kamara.innerHTML,/Check pick year/);
// The current package edge is a different question from the gain since trade.
const trade=api.getTrade('sleeper-1205285790439981056');
assert.equal(trade.spreads.latest,1312);
assert.equal(api.currentStanding(trade).value,'−1,312');
assert.equal(api.currentStanding(trade).label,'Dave leads');
assert.equal(metrics.margin(trade.lenses[1].point.changes,0),4019);
controls.managerSelect.value='Dave Carnes';
assert.equal(api.currentStanding(trade).value,'+1,312');
assert.equal(api.currentStanding(trade).state,'ahead');
// Never let an allowance create a current lead, or missing prices create zero.
controls.managerSelect.value='A';
const tie=api.learnTrade({date:'2026-01-01',sides:[{manager:'A',assets:[]},{manager:'B',assets:[]}],day:[0,[20,30]],timeline:[[1,111,100]],timelineAdjustments:[[1,11,0]]});
assert.equal(api.currentStanding(tie).value,'Even');
const missing=api.learnTrade({date:'2026-01-01',sides:[{manager:'A',assets:[]},{manager:'B',assets:[]}],day:[0,[20,30]],timeline:[[1,null,100]]});
assert.equal(api.currentStanding(missing).label,'Unrated');
const multi=api.learnTrade({date:'2026-01-01',sides:[{manager:'A',assets:[]},{manager:'B',assets:[]},{manager:'C',assets:[]}],day:[0,[20,30,40]],timeline:[[1,100,110,90]]});
assert.equal(api.currentStanding(multi).value,'−10');
assert.equal(api.currentStanding(multi).label,'B leads');
// Current-edge sorting follows the very same value shown in the list.
controls.managerSelect.value='Seth Miller';
controls.tradeSort.value='latest';
api.renderList();
const edges=controls.tradeResults.rows.map(row=>{
 const id=row.innerHTML.match(/trades\/([^"/]+)/)[1];
 return api.getTrade(id).spreads.latest;
});
assert.ok(edges.every((edge,i)=>i===0||edges[i-1]>=edge));
console.log('Passed filtered/all-manager rows, received/sent previews, current value vs since-trade swing, signed perspective, missing values, ties, multiway leads and current-edge sorting.');
