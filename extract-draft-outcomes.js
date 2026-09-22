const fs=require('fs');

const src=fs.readFileSync('index.html','utf8');
const start='const careerDraftStats=';
const end=';\nconst rookieBoards=';
const a=src.indexOf(start),b=src.indexOf(end,a+start.length);
if(a<0||b<0)throw new Error('careerDraftStats source block not found');
const outcomes=JSON.parse(src.slice(a+start.length,b));

// The draft-adjusted artifact is the audited rookie-event ledger. Use it to make
// the production outcome file complete for every completed true-rookie pick and
// to preserve the player's rookie position even if Sleeper later changed it.
const adjSrc=fs.readFileSync('draft-adjusted-ppg.js','utf8').trim();
const adjPrefix='window.DRAFT_ADJUSTED_PPG=';
if(!adjSrc.startsWith(adjPrefix))throw new Error('draft-adjusted-ppg.js format changed');
const adjusted=JSON.parse(adjSrc.slice(adjPrefix.length).replace(/;\s*$/,''));
let zeroGameAdded=0, positionFixed=0;
for(const [key,pick] of Object.entries(adjusted.picks||{})){
  const year=Number(key.slice(0,4));
  if(year>adjusted.throughSeason)continue;
  if(pick.status==='scored'){
    if(!outcomes[key]){
      outcomes[key]={
        ppg:0,
        points:0,
        games:0,
        seasons:0,
        through:adjusted.throughSeason,
        pos:pick.pos,
        zeroGameOutcome:true
      };
      zeroGameAdded++;
    }else{
      if(Number.isFinite(pick.careerPpg)&&Math.abs(Number(outcomes[key].ppg)-pick.careerPpg)>0.00001){
        throw new Error(`Career PPG disagrees with draft-adjusted ledger for ${key}`);
      }
      if(pick.pos&&outcomes[key].pos!==pick.pos){
        outcomes[key].pos=pick.pos;
        positionFixed++;
      }
    }
  }else if(pick.status==='veteran_excluded'&&outcomes[key]&&pick.pos&&outcomes[key].pos!==pick.pos){
    outcomes[key].pos=pick.pos;
    positionFixed++;
  }
}

for(const [key,row] of Object.entries(outcomes)){
  if(row?.excluded==='veteran')continue;
  if(Number.isFinite(row?.games)&&row.games<0)throw new Error(`Negative games in ${key}`);
  if(Number.isFinite(row?.games)&&row.games>0){
    if(!Number.isFinite(row.points)||!Number.isFinite(row.ppg))throw new Error(`Incomplete scored outcome in ${key}`);
    const expected=row.points/row.games;
    if(Math.abs(expected-row.ppg)>0.00001)throw new Error(`Career PPG math drift in ${key}: ${row.points}/${row.games} != ${row.ppg}`);
  }
}

const completed=Object.entries(adjusted.picks||{}).filter(([key])=>Number(key.slice(0,4))<=adjusted.throughSeason);
const completedRookies=completed.filter(([,p])=>p.status==='scored');
const completedVeterans=completed.filter(([,p])=>p.status==='veteran_excluded');
if(completed.length!==397||completedRookies.length!==390||completedVeterans.length!==7){
  throw new Error(`Completed draft-event census drifted: total=${completed.length}, rookies=${completedRookies.length}, veterans=${completedVeterans.length}`);
}
for(const [key,pick] of completedRookies){
  const row=outcomes[key];
  if(!row||!Number.isFinite(row.ppg)||row.pos!==pick.pos){
    throw new Error(`Incomplete completed rookie outcome after merge: ${key}`);
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

fs.writeFileSync('dist/draft-outcomes.js',`window.DRAFT_OUTCOMES=${JSON.stringify(outcomes)};\n`);
console.log(`Draft outcomes audited: ${Object.keys(outcomes).length} rows; ${zeroGameAdded} zero-game rookies added; ${positionFixed} rookie positions normalized.`);
