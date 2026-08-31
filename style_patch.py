from pathlib import Path

p = Path("index.html")
s = p.read_text()

repls = {
    '.champion-card h3{position:relative;z-index:1;margin:7px 0 2px;font:800 18px/1.05 Georgia,serif}':
    '.champion-card h3{position:relative;z-index:1;margin:7px 0 2px;font:800 clamp(13px,2.4vw,18px)/1 Georgia,serif;white-space:nowrap;letter-spacing:-.015em}',
    '.axis-label{font-size:9px;fill:#817666}':
    '.axis-label{font-size:12px;fill:#6f6353;font-weight:700}',
    '.point-label{font-size:8px;fill:#5d5244;font-weight:800;text-anchor:middle}':
    '.point-label{font-size:12px;fill:#3f3529;font-weight:900;text-anchor:middle}',
    '.point-label{font-size:7px}':
    '.point-label{font-size:10px}',
    '<p>Year-by-year regular-season performance. Every manager uses the same scale for each metric.</p>':
    '<p>Year-by-year regular-season performance.</p>',
    '<div class="scale-note">Fixed league-wide scale · identical for every manager</div>':
    '',
    "pf:{label:'Points For',get:s=>s.pf":
    "pf:{label:'PF',get:s=>s.pf",
    "pa:{label:'Points Against',get:s=>s.pa":
    "pa:{label:'PA',get:s=>s.pa"
}

for old, new in repls.items():
    if old not in s:
        raise SystemExit(f"Expected style target not found: {old[:80]}")
    s = s.replace(old, new)

old_wall = "const wall=[['Highest Team PPG',highPPG.ppg.toFixed(1),highPPG.m,String(highPPG.year)],['Lowest Team PPG',lowPPG.ppg.toFixed(1),lowPPG.m,String(lowPPG.year)],['Best Scoring Margin / Game',(bestMargin.margin>=0?'+':'')+bestMargin.margin.toFixed(1),bestMargin.m,String(bestMargin.year)],['Worst Scoring Margin / Game',worstMargin.margin.toFixed(1),worstMargin.m,String(worstMargin.year)],['Career Regular-Season Wins',String(careerWins),winLeaders.map(x=>x.m).join(' & '),''],['Career Win %',winDec(careerPct.p),careerPct.m,careerPct.s+' seasons'],['Most Career Points',nf.format(careerPF.pf),careerPF.m,careerPF.s+' seasons'],['Highest Single-Season PF',nf.format(highPF.pf),highPF.m,String(highPF.year)]];"

new_wall = r"""function seasonStreakLeaders(type){
  let best=0,runs=[];
  const save=(manager,start,end,count)=>{
    if(!count)return;
    const run={manager,start,end,count};
    if(count>best){best=count;runs=[run]}
    else if(count===best)runs.push(run);
  };
  history.forEach((rows,manager)=>{
    const sorted=[...rows].sort((a,b)=>a.year-b.year);
    let count=0,start=null,lastYear=null;
    for(const s of sorted){
      const qualifies=type==='winning'?s.w>s.l:s.w<s.l;
      const adjacent=lastYear===null||s.year===lastYear+1;
      if(!adjacent||!qualifies){
        save(manager,start,lastYear,count);
        count=0;start=null;
      }
      if(qualifies){
        if(count===0)start=s.year;
        count++;
      }
      lastYear=s.year;
    }
    save(manager,start,lastYear,count);
  });
  const names=[...new Set(runs.map(r=>r.manager))].join(' · ');
  const ranges=runs.map(r=>`${r.manager.split(' ')[0]} ${r.start}–${String(r.end).slice(-2)}`).join(' · ');
  return{count:best,names,ranges};
}
const winningStreak=seasonStreakLeaders('winning'),losingStreak=seasonStreakLeaders('losing');
const wall=[['Highest Team PPG',highPPG.ppg.toFixed(1),highPPG.m,String(highPPG.year)],['Lowest Team PPG',lowPPG.ppg.toFixed(1),lowPPG.m,String(lowPPG.year)],['Best Scoring Margin / Game',(bestMargin.margin>=0?'+':'')+bestMargin.margin.toFixed(1),bestMargin.m,String(bestMargin.year)],['Worst Scoring Margin / Game',worstMargin.margin.toFixed(1),worstMargin.m,String(worstMargin.year)],['Most Consecutive Winning Seasons',String(winningStreak.count),winningStreak.names,winningStreak.ranges],['Most Consecutive Losing Seasons',String(losingStreak.count),losingStreak.names,losingStreak.ranges],['Career Regular-Season Wins',String(careerWins),winLeaders.map(x=>x.m).join(' & '),''],['Career Win %',winDec(careerPct.p),careerPct.m,careerPct.s+' seasons'],['Most Career Points',nf.format(careerPF.pf),careerPF.m,careerPF.s+' seasons'],['Highest Single-Season PF',nf.format(highPF.pf),highPF.m,String(highPF.year)]];"""

if old_wall not in s:
    raise SystemExit("Expected Wall of Fame data target not found")
s = s.replace(old_wall, new_wall)

p.write_text(s)
