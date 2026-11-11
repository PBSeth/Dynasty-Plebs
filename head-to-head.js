(() => {
  const managerSelect = document.getElementById('managerSelect');
  const opponentSelect = document.getElementById('headToHeadOpponent');
  const panel = document.getElementById('headToHead');
  const summary = document.getElementById('headToHeadSummary');
  const years = document.getElementById('headToHeadYears');
  const coverage = document.getElementById('headToHeadCoverage');
  const controls = panel.querySelector('.h2h-controls');

  const rememberedOpponents = new Map();
  const scores = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 });
  const points = cents => scores.format(cents / 100);
  const byDate = (a, b) => b.year - a.year || b.week - a.week;
  const count = (games, result) => games.filter(game => game.result === result).length;
  const record = games => {
    const ties = count(games, 'T');
    return [count(games, 'W'), count(games, 'L'), ...(ties ? [ties] : [])].join('–');
  };
  const outcome = { W: 'Win', L: 'Loss', T: 'Tie' };
  const escape = text => String(text).replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[character]);

  let data;
  let loading;
  let matchups;
  let managerIds;

  function indexGames(payload) {
    const index = new Map(Object.keys(payload.managers).map(id => [id, new Map()]));
    function addGame(year, week, manager, opponent, scored, allowed) {
      const opponents = index.get(manager);
      if (!opponents.has(opponent)) opponents.set(opponent, []);
      const margin = scored - allowed;
      const result = margin === 0 ? 'T' : margin > 0 ? 'W' : 'L';
      opponents.get(opponent).push({ year, week, scored, allowed, margin, result });
    }
    for (const [year, season] of Object.entries(payload.seasons)) {
      for (const [week, a, b, scoreA, scoreB] of season.games) {
        addGame(Number(year), week, a, b, scoreA, scoreB);
        addGame(Number(year), week, b, a, scoreB, scoreA);
      }
    }
    for (const opponents of index.values()) {
      for (const meetings of opponents.values()) meetings.sort(byDate);
    }
    return index;
  }

  function metric(label, value, detail = '') {
    return `<div class="h2h-metric"><dt>${label}</dt><dd>${value}${detail}</dd></div>`;
  }

  function marginMetric(label, game) {
    if (!game) return metric(label, '—');
    const detail = `<small>${game.year} W${game.week} · ${points(game.scored)}–${points(game.allowed)}</small>`;
    return metric(label, `${game.margin > 0 ? '+' : '−'}${points(Math.abs(game.margin))}`, detail);
  }

  function resultChip(game) {
    const label = `${game.year} Week ${game.week} ${outcome[game.result]}`;
    return `<span class="h2h-result h2h-${game.result}" title="${label}" aria-label="${label}">${game.result}</span>`;
  }

  function renderMatchup(manager) {
    const opponent = opponentSelect.value;
    const games = matchups.get(manager).get(opponent);
    const groups = new Map();
    let biggestWin;
    let biggestLoss;
    for (const game of games) {
      if (!groups.has(game.year)) groups.set(game.year, []);
      groups.get(game.year).push(game);
      if (game.margin > (biggestWin?.margin ?? 0)) biggestWin = game;
      if (game.margin < (biggestLoss?.margin ?? 0)) biggestLoss = game;
    }
    const recentResult = games[0].result;
    const streakEnd = games.findIndex(game => game.result !== recentResult);
    const streak = streakEnd === -1 ? games.length : streakEnd;
    const managerName = escape(data.managers[manager]);
    const opponentName = escape(data.managers[opponent]);
    const seriesRecord = record(games);
    const yearlyLinks = [...groups].map(([year, meetings]) =>
      `<button type="button" aria-expanded="false" aria-controls="h2h-season-${year}"><span>${year}</span> ${record(meetings)}</button>`
    ).join('');
    summary.innerHTML = `
      <div class="h2h-scoreboard">
        <strong>${managerName}</strong>
        <b aria-label="${managerName} record ${seriesRecord} against ${opponentName}">${seriesRecord}</b>
        <strong>${opponentName}</strong>
      </div>
      <dl class="h2h-metrics">
        ${metric('Meetings', games.length)}
        ${metric('Win %', `${(100 * count(games, 'W') / games.length).toFixed(1)}%`)}
        ${metric('Current Streak', `${recentResult}${streak}`)}
        ${metric('Last 5', `<span class="h2h-recent">${games.slice(0, 5).reverse().map(resultChip).join('')}</span>`)}
        ${marginMetric('Biggest Win', biggestWin)}
        ${marginMetric('Biggest Loss', biggestLoss)}
      </dl>
      <div class="h2h-year-links" role="group" aria-label="Year-by-year records">${yearlyLinks}</div>`;
    years.innerHTML = [...groups].map(([year, meetings]) => `
      <ul id="h2h-season-${year}" aria-label="${year} matchups" hidden>
        ${meetings.map(game => `
          <li><span>Week ${game.week}</span><span>${points(game.scored)}–${points(game.allowed)}</span>${resultChip(game)}</li>`
        ).join('')}
      </ul>`).join('');
  }

  function renderManager() {
    const manager = managerIds.get(managerSelect.value);
    const opponents = matchups.get(manager);
    const ids = opponents ? [...opponents.keys()] : [];
    controls.hidden = ids.length === 0;
    if (!ids.length) {
      summary.textContent = 'No regular-season matchups in the archive for this manager.';
      years.replaceChildren();
      return;
    }
    ids.sort((a, b) => data.managers[a].localeCompare(data.managers[b]));
    opponentSelect.replaceChildren(...ids.map(id => new Option(data.managers[id], id)));
    const previous = rememberedOpponents.get(manager);
    opponentSelect.value = ids.includes(previous) ? previous :
      ids.reduce((most, id) => opponents.get(id).length > opponents.get(most).length ? id : most);
    renderMatchup(manager);
  }

  async function loadArchive() {
    if (loading) return;
    loading = true;
    try {
      const response = await fetch('./head-to-head-data.json');
      if (!response.ok) throw new Error('Head-to-head archive could not be loaded');
      data = await response.json();
      matchups = indexGames(data);
      managerIds = new Map(Object.entries(data.managers).map(([id, name]) => [name, id]));
      const seasons = Object.entries(data.seasons);
      const lastComplete = seasons.filter(([, season]) => season.complete).at(-1)?.[0];
      const completed = lastComplete ? `${seasons[0][0]}–${lastComplete} complete` : '';
      const partial = seasons.filter(([, season]) => !season.complete)
        .map(([year, season]) => `${year} partial (${season.games.length}/${season.expected} games)`);
      coverage.textContent = [completed, ...partial].filter(Boolean).join(' · ');
      renderManager();
    } catch {
      summary.textContent = 'Matchup history is temporarily unavailable.';
      loading = false;
    }
  }

  summary.addEventListener('click', event => {
    const button = event.target.closest('.h2h-year-links button');
    if (!button) return;

    const openButton = summary.querySelector('.h2h-year-links [aria-expanded="true"]');
    if (openButton) {
      openButton.setAttribute('aria-expanded', 'false');
      document.getElementById(openButton.getAttribute('aria-controls')).hidden = true;
    }
    if (button !== openButton) {
      button.setAttribute('aria-expanded', 'true');
      document.getElementById(button.getAttribute('aria-controls')).hidden = false;
    }
  });
  managerSelect.addEventListener('change', () => {
    if (matchups) renderManager();
    else loadArchive();
  });
  opponentSelect.addEventListener('change', () => {
    const manager = managerIds.get(managerSelect.value);
    rememberedOpponents.set(manager, opponentSelect.value);
    renderMatchup(manager);
  });
  document.querySelector('[data-view="managers"]').addEventListener('click', loadArchive);
})();
