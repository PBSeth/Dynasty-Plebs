const fs = require('fs');
const vm = require('vm');

const sandbox = { window: {} };
vm.createContext(sandbox);

for (let i = 1; i <= 7; i++) {
  const file = `data-v3-${String(i).padStart(2, '0')}.js`;
  vm.runInContext(fs.readFileSync(file, 'utf8'), sandbox, { filename: file });
}

if (!sandbox.window.__PLEBS_DATA_SRC) throw new Error('Missing modular Dynasty Plebs data source.');
vm.runInContext(sandbox.window.__PLEBS_DATA_SRC, sandbox, { filename: 'combined-workbook-data.js' });

const D = sandbox.window.DATA;
if (!D) throw new Error('Combined data did not create window.DATA.');

function assert(condition, message) {
  if (!condition) throw new Error(`Workbook data verification failed: ${message}`);
}
function close(a, b, tolerance = 1e-6) {
  return Math.abs(Number(a) - Number(b)) <= tolerance;
}

const regularChecks = {
  'Jordan Martin': ['60-32', 0.6522],
  'Travis Page': ['60-32', 0.6522],
  'Seth Miller': ['56-36', 0.6087],
  'Matt Metz': ['51-41', 0.5543],
  'Clint Hudson': ['15-13', 0.5357],
  'Alex Agueros': ['44-48', 0.4783],
  'Bo Tiller': ['37-42', 0.4684],
  'Dave Carnes': ['41-51', 0.44565],
  'Payton Docheff': ['39-53', 0.4239],
  'Luke Miller': ['25-39', 0.3906],
  'Matt Clawson': ['34-58', 0.3696],
  'Ryan Lipkin': ['4-24', 0.14286],
  'Josh Ponath': ['9-4', 0.6923],
  'Matthew Piontek': ['26-12', 0.6842],
  'Tim Bell': ['13-13', 0.5],
  'Kevin Long': ['12-14', 0.4615],
  'Mason Good': ['26-38', 0.40625]
};

for (const [manager, [record, winPct]] of Object.entries(regularChecks)) {
  assert(D.regular[manager], `missing regular-season row for ${manager}`);
  assert(D.regular[manager].total === record, `${manager} regular record expected ${record}, got ${D.regular[manager].total}`);
  assert(close(D.regular[manager].winPct, winPct), `${manager} win % drifted`);
}

const formulaChecks = {
  'Seth Miller': [0.6087, 12, 7, 2, 1795.665],
  'Travis Page': [0.6522, 6, 7, 1, 1402.23],
  'Jordan Martin': [0.6522, 5, 7, 1, 1369.62],
  'Dave Carnes': [0.44565, 4, 7, 1, 913.5825],
  'Matt Metz': [0.5543, 5, 7, 0, 886.88],
  'Alex Agueros': [0.4783, 1, 7, 0, 669.62],
  'Payton Docheff': [0.4239, 4, 7, 0, 657.045],
  'Bo Tiller': [0.4684, 2, 6, 0, 655.76],
  'Clint Hudson': [0.5357, 0, 2, 0, 589.27],
  'Matt Clawson': [0.3696, 0, 7, 0, 498.96],
  'Luke Miller': [0.3906, 0, 5, 0, 488.25],
  'Ryan Lipkin': [0.14286, 0, 2, 0, 157.146],
  'Matthew Piontek': [0.6842, 6, 3, 2, 1676.29],
  'Josh Ponath': [0.6923, 2, 1, 0, 796.145],
  'Tim Bell': [0.5, 1, 2, 0, 575],
  'Mason Good': [0.40625, 1, 5, 0, 528.125],
  'Kevin Long': [0.4615, 0, 2, 0, 507.65]
};

for (const [manager, [winPct, playoffWins, service, titles, expectedScore]] of Object.entries(formulaChecks)) {
  const f = D.formulaInputs[manager];
  assert(f, `missing Legacy formula row for ${manager}`);
  assert(close(f.winPct, winPct), `${manager} Legacy base win % drifted`);
  assert(f.playoffWins === playoffWins, `${manager} Legacy playoff wins expected ${playoffWins}, got ${f.playoffWins}`);
  assert(f.service === service, `${manager} service time expected ${service}, got ${f.service}`);
  assert(f.titles === titles, `${manager} championship count expected ${titles}, got ${f.titles}`);
  const recalculated = winPct * (1 + 0.05 * service + 0.05 * playoffWins + 0.50 * titles) * 1000;
  assert(close(recalculated, expectedScore), `${manager} locked Legacy formula no longer reproduces workbook score`);
  assert(close(f.score, expectedScore), `${manager} stored Legacy score input drifted`);
  assert(D.legacy[manager] && D.legacy[manager].score === Math.round(expectedScore), `${manager} displayed Legacy score drifted`);
}

assert(Array.isArray(D.champions) && D.champions.length === 7, 'champion history must contain 2019-2025');
assert(D.champions.map(x => `${x.year}:${x.manager}`).join('|') === [
  '2019:Dave Carnes',
  '2020:Matthew Piontek',
  '2021:Matthew Piontek',
  '2022:Seth Miller',
  '2023:Jordan Martin',
  '2024:Seth Miller',
  '2025:Travis Page'
].join('|'), 'champion history drifted');

assert(Array.isArray(D.currentManagers) && D.currentManagers.length === 12, 'active manager list must contain 12 managers');
assert(new Set(D.currentManagers).size === 12, 'active manager list contains duplicates');
assert(Array.isArray(D.trades) && D.trades.length === 165, `trade log expected 165 entries, got ${D.trades?.length}`);
assert(D.trades[164] === 'Seth trades Terry McLaurin and a 2025 2nd (TBD) to Clint for DK Metcalf and a 2025 4th (TBD)', 'last workbook trade entry drifted');

assert(Array.isArray(D.future2027), 'missing 2027 pick ledger');
const base2027 = D.future2027.filter(x => !x.supplemental);
const extra2027 = D.future2027.filter(x => x.supplemental);
assert(base2027.length === 60, `2027 base pick ledger expected 60 picks, got ${base2027.length}`);
assert(extra2027.length === 2, `2027 supplemental ledger expected 2 Seth picks, got ${extra2027.length}`);
assert(extra2027.every(x => x.owner === 'Seth Miller' && [4, 5].includes(x.round)), '2027 supplemental picks drifted');

assert(D.compPicks['Ryan Lipkin']?.includes('Darius Slayton '), 'Ryan comp-pick row drifted');
assert(D.compPicks['Jordan Martin']?.includes('Joe Flacco') && D.compPicks['Jordan Martin']?.includes('Spencer Rattler'), 'Jordan comp-pick row drifted');
assert(D.compPicks['Matt Metz']?.includes('Kendrick Bourne'), 'Metz comp-pick row drifted');
assert(D.compPicks['Seth Miller']?.some(x => String(x).trim() === "D'Onte Thornton"), 'Seth comp-pick row drifted');

console.log('Dynasty Plebs workbook data verification passed.');
