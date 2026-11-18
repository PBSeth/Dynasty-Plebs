(() => {
  const nav = document.querySelector('[data-view="managers"]');
  const managerSelect = document.getElementById('managerSelect');
  const partner = document.getElementById('tradePartner');
  const search = document.getElementById('tradeSearch');
  const season = document.getElementById('tradeSeason');
  const sort = document.getElementById('tradeSort');
  const count = document.getElementById('tradeCount');
  const results = document.getElementById('tradeResults');
  const detail = document.getElementById('tradeDetail');
  const view = document.getElementById('trades');
  const number = new Intl.NumberFormat('en-US');
  const date = new Intl.DateTimeFormat('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC'
  });
  const formatDate = value => date.format(new Date(value + 'T00:00:00Z'));
  const tradeDate = trade => `${trade.dateEstimate ? 'Est. ' : ''}${formatDate(trade.date)}`;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[c]);
  const colors = ['#7e3125', '#415e4f', '#705586'];
  const metrics = window.PLEBS_TRADE_METRICS;
  const signed = value => !Number.isFinite(value) ? '—' : `${value > 0 ? '+' : value < 0 ? '−' : ''}${number.format(Math.abs(value))}`;
  const stackedName = name => {
    const [first, ...last] = name.split(' ');
    return `<span>${esc(first)}</span><span>${esc(last.join(' '))}</span>`;
  };

  let market, trades, loading, selected, chartObserver;
  let browseScroll = 0;
  let currentManager;
  let browseListScroll = 0;
  const fullyPriced = values => values.every(Number.isFinite);
  const label = trade => trade.sides.map(side => side.manager).join(' / ');
  const hasRoute = () => /^#(?:trades|managers)(?:\/|$)/.test(location.hash);
  const routeParts = () => location.hash.slice(1).split('/');
  const routedId = () => routeParts()[0] === 'trades' ? routeParts()[1] : routeParts()[3];
  const managerRoute = (id) => `#managers/${encodeURIComponent(managerSelect.value)}/trades${id ? '/' + id : ''}`;
  const belongsToManager = trade => trade.sides.some(side => side.manager === managerSelect.value);
  const counterpart = trade => trade.sides.filter(side => side.manager !== managerSelect.value).map(side => side.manager).join(' / ');
  const marked = (trade, id) => trade.id === id ? ' aria-current="true"' : '';

  function margin(values, side) {
    return values[side] - Math.max(...values.filter((_, index) => index !== side));
  }

  function pickLabel(asset) {
    const origin = asset.origin ? ` · ${asset.origin}` : '';
    const slot = asset.slotKnownAtTrade || `Round ${asset.round}`;
    return `${asset.season ?? 'Year unknown'} ${slot}${origin}`;
  }

  function learnTrade(trade) {
    trade.points = [];
    const adjustments = new Map((trade.timelineAdjustments || []).map(([i, ...values]) => [i, values]));
    const day = trade.day;
    if (day) trade.points.push({ i: day[0], date: trade.date, values: day[1], adjustments: trade.dayAdjustments, original: true });
    trade.points.push(...(trade.timeline || []).map(([i, ...values]) => ({ i, date: market[i][0], values, adjustments: adjustments.get(i) })));
    const analyzed = metrics.analyze(trade.points, trade.sides);
    trade.points = analyzed.points;
    const peaks = analyzed.peaks;
    const latest = analyzed.latest;
    const firstNames = trade.sides.map(side => side.manager.split(' ')[0]);
    trade.lenses = [
      { name: 'At trade', point: analyzed.baseline, originalBalance: true },
      { name: 'Now', point: latest },
      ...peaks.map((point, side) => {
        const parts = trade.sides[side].manager.split(' ');
        const name = firstNames.filter(first => first === parts[0]).length > 1 ? parts.at(-1) : parts[0];
        return { name: `${name}’s best`, point, side };
      })
    ];
    const spread = (point, original = false) => {
      const values = original ? point?.values : point?.changes;
      if (!values || !metrics.complete(values)) return -1;
      return margin(values, values.indexOf(Math.max(...values)));
    };
    trade.spreads = {
      peak: Math.max(-1, ...peaks.map(spread)), day: spread(trade.lenses[0].point, true),
      latest: spread(trade.lenses[1].point)
    };
    const terms = [label(trade), trade.date, trade.original, trade.dateEstimate ? 'estimated date' : 'recorded date'];
    for (const side of trade.sides) {
      for (const asset of side.assets || []) {
        terms.push(asset.kind === 'pick' ? pickLabel(asset) : asset.name, asset.outcome?.name, asset.outcome?.slot);
      }
    }
    terms.push(...(trade.outcomes || []).flat());
    trade.search = terms.join(' ').toLowerCase();
    return trade;
  }

  function renderList() {
    const terms = search.value.trim().toLowerCase().split(/\s+/);
    const visible = trades.filter(trade =>
      belongsToManager(trade) && (!partner.value || trade.sides.some(side => side.manager === partner.value)) &&
      (!season.value || (season.value === 'estimated' ? trade.dateEstimate :
        (trade.season ?? 'undated') === (Number(season.value) || season.value))) &&
      terms.every(term => trade.search.includes(term))
    );
    if (sort.value !== 'recent') {
      visible.sort((a, b) => b.spreads[sort.value] - a.spreads[sort.value]);
    }
    if (!visible.includes(selected)) {
      selected = visible[0];
      if (routedId()) history.replaceState(null, '', selected ? managerRoute(selected.id) : managerRoute());
    }
    count.textContent = `${visible.length} trade${visible.length === 1 ? '' : 's'}`;
    results.replaceChildren(...visible.map(trade => {
      const item = document.createElement('li');
      const sortedGap = trade.spreads[sort.value];
      const preview = trade.sides.map(side => {
        if (side.package) return side.package;
        const first = side.assets?.[0];
        if (!first) return '—';
        const name = first.kind === 'pick' ? `${first.season ?? '?'} R${first.round}` : first.kind === 'faab' ? `$${first.amount} FAAB` : first.name;
        return name + (side.assets.length > 1 ? ` + ${side.assets.length - 1}` : '');
      }).join(' ↔ ');
      const caption = (trade.date ? tradeDate(trade) : 'Date unknown') +
        (trade.gradeBlocked ? ' · Unrated' : '');
      item.innerHTML = `<a href="${managerRoute(trade.id)}"${marked(trade, selected?.id)}>
        <strong>${esc(counterpart(trade))}</strong><span class="trade-preview">${esc(preview)}</span><small>${esc(caption)}${Number.isFinite(sortedGap) && sortedGap >= 0 ? ` · ${number.format(sortedGap)} gap` : ''}</small>
      </a>`;
      return item;
    }));
    renderDetail();
  }

  function setSelected(id) {
    const trade = trades.find(row => row.id === id);
    if (!trade || !belongsToManager(trade)) return;
    view.dataset.detailOpen = 'true';
    if (selected === trade) return;
    selected = trade;
    for (const link of results.querySelectorAll('a')) {
      if (link.getAttribute('href') === managerRoute(id)) link.setAttribute('aria-current', 'true');
      else link.removeAttribute('aria-current');
    }
    renderDetail();
  }

  function assetList(trade, side, point) {
    if (side.package) {
      const outcomes = (trade.outcomes || []).filter(([manager]) => manager === side.manager);
      return `<p>${esc(side.package)}</p>${outcomes.length ? `<ul class="trade-pick-outcomes">${outcomes.map(([, year, slot, player]) =>
        `<li>${year} ${esc(slot)} <span>became ${esc(player)}</span></li>`
      ).join('')}</ul>` : ''}`;
    }
    return `<ul>${side.assets.map(asset => {
      if (asset.kind === 'faab') return `<li>$${number.format(asset.amount)} FAAB</li>`;
      if (asset.kind === 'player') return `<li>${esc(asset.name)}</li>`;
      const outcome = asset.outcome;
      const afterDraft = point && !point.original && outcome &&
        market[point.i][2] >= asset.afterDraft;
      return `<li>${esc(pickLabel(asset))}${afterDraft ? `<small>${esc(outcome.slot)} became ${esc(outcome.name)}</small>` :
        outcome && (!asset.afterDraft || !point) ? `<small>Drafted: ${esc(outcome.name)}</small>` : ''}</li>`;
    }).join('')}</ul>`;
  }

  function renderDetail() {
    chartObserver?.disconnect();
    if (!selected) {
      detail.innerHTML = '<p class="trade-empty">No trades found.</p>';
      return;
    }
    const trade = selected;
    const latest = trade.lenses[1].point;
    const showChart = trade.points.filter(point => point.changes.some(Number.isFinite)).length > 1;
    const anniversary = new Date(`${trade.date}T00:00:00Z`);
    anniversary.setUTCFullYear(anniversary.getUTCFullYear() + 3);
    const threeYearEnd = Math.max(0, trade.points.findLastIndex(point => Date.parse(point.date) <= anniversary.getTime()));
    const bounds = trade.dateEstimate;
    const routes = [...results.querySelectorAll('a')].map(link => link.getAttribute('href'));
    const position = routes.indexOf(managerRoute(trade.id));
    const previousRoute = position > 0 ? routes[position - 1] : null;
    const nextRoute = position >= 0 ? routes[position + 1] : null;
    const currentValues = latest?.changes;
    const currentSide = currentValues && metrics.complete(currentValues) ? currentValues.indexOf(Math.max(...currentValues)) : -1;
    const currentGap = currentSide < 0 ? null : margin(currentValues, currentSide);
    const summaries = trade.lenses.map((lens, index) => {
      const values = lens.originalBalance ? lens.point?.values : lens.point?.changes;
      const available = values && metrics.complete(values);
      return `<button type="button" class="trade-summary" data-lens="${index}" aria-pressed="false"${lens.point ? '' : ' disabled'}>
        <span class="trade-summary-label">${esc(lens.name)}</span>
        <span class="trade-summary-kind">${lens.originalBalance ? 'Original edge' : 'Swing since trade'}</span>
        <span class="trade-summary-values">${trade.sides.map((side, i) => `<span style="--side-color:${colors[i % colors.length]}"><small>${stackedName(side.manager)}</small><b>${signed(available ? margin(values, i) : null)}</b></span>`).join('')}</span>
        <time>${lens.point ? `${lens.point.original && bounds ? 'Est. ' : ''}${formatDate(lens.point.date)}` : 'Unavailable'}</time>
      </button>`;
    }).join('');
    detail.innerHTML = `
      <div class="trade-detail-nav">
        <button type="button" class="trade-back">← Back to trades</button>
        <div class="trade-stepper" role="group" aria-label="Browse trades">
          <button type="button" data-step="previous" aria-label="Previous trade"${previousRoute ? '' : ' disabled'}>‹ Prev</button>
          <button type="button" data-step="next" aria-label="Next trade"${nextRoute ? '' : ' disabled'}>Next ›</button>
        </div>
      </div>
      <div class="trade-detail-heading">
        <h3 class="trade-manager-names" aria-label="${esc(label(trade))}">${trade.sides.map((side, i) => `<span class="trade-manager-name" style="--side-color:${colors[i % colors.length]}">${stackedName(side.manager)}</span>`).join('<span class="trade-versus" aria-hidden="true">↔</span>')}</h3>
      </div>
      <div class="trade-current" aria-label="Since trade">
        <small>Since trade</small>
        <strong style="--side-color:${currentSide < 0 ? 'var(--ink)' : colors[currentSide % colors.length]}">${currentGap == null ? 'Not rated' : currentGap === 0 ? 'Even' : signed(currentGap)}</strong>
        <span>${currentGap == null ? 'Values unavailable' : currentGap === 0 ? 'Neither manager leads' : esc(trade.sides[currentSide].manager)}</span>
      </div>
      ${showChart ? `<section class="trade-chart" aria-label="Value change since trade">
        <div class="trade-chart-body">
          <div class="trade-chart-windows" role="group" aria-label="Graph time window">
            <button type="button" data-window="3y" aria-pressed="true">3 years</button>
            <button type="button" data-window="all" aria-pressed="false">All time</button>
          </div>
          <div class="trade-chart-legend">${trade.sides.map((side, i) => `<span style="--side-color:${colors[i % colors.length]}">${esc(side.manager)}</span>`).join('')}</div>
          <canvas role="img" aria-label="Package gains and losses since trade day"></canvas>
          <label class="trade-time-control"><input aria-label="Date shown" type="range" min="0" max="${threeYearEnd}" value="0"><span class="trade-chart-date"></span></label>
        </div></section>` : '<p class="trade-empty">Trade-day value history unavailable.</p>'}
      <div class="trade-summaries" role="group" aria-label="Trade summaries">${summaries}</div>
      <div class="trade-package-date"></div>
      <div class="trade-packages"></div>`;
    const canvas = detail.querySelector('canvas');
    const range = detail.querySelector('input[type="range"]');
    const packages = detail.querySelector('.trade-packages');
    let graphWindow = '3y', pointIndex = Math.min(trade.points.length - 1, threeYearEnd);
    const graphEnd = () => graphWindow === '3y' ? threeYearEnd : trade.points.length - 1;
    const paintSelected = () => paintChart(canvas, trade.points.slice(0, graphEnd() + 1).map(point => ({...point, values: point.changes})), pointIndex, trade.sides.length);
    function updateWindow() {
      detail.querySelectorAll('[data-window]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.window === graphWindow)));
      if (range) range.max = graphEnd();
    }
    function selectPoint(index, lensIndex = -1) {
      pointIndex = index;
      if (index > graphEnd()) { graphWindow = 'all'; updateWindow(); }
      const point = trade.points[index];
      detail.querySelectorAll('[data-lens]').forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.lens) === lensIndex)));
      if (range && point) {
        range.value = index;
        range.setAttribute('aria-valuetext', formatDate(point.date));
        detail.querySelector('.trade-chart-date').textContent = formatDate(point.date);
      }
      detail.querySelector('.trade-package-date').textContent = point ? `Change since trade · ${formatDate(point.date)}` : 'Package details';
      const packageContent = side => side.package || side.assets?.length
        ? assetList(trade, side, point) : '<p class="trade-unrecorded">Not recorded</p>';
      packages.innerHTML = trade.sides.map((side, i) => {
        // A two-manager exchange identifies the outgoing package exactly. A
        // multi-manager receipt alone does not identify who supplied each asset.
        const sent = trade.sides.length === 2 ? trade.sides[1 - i] : null;
        return `<section style="--side-color:${colors[i % colors.length]}" aria-label="${esc(side.manager)}’s side of the trade">
          <h4 class="trade-package-name">${stackedName(side.manager)}</h4>
          <div class="trade-received" aria-label="${esc(side.manager)} received">
            <h5>Received</h5>
            ${packageContent(side)}
            <p class="trade-total"><span>Received value change</span>${signed(point?.changes[i])}</p>
          </div>
          ${sent ? `<div class="trade-sent" aria-label="${esc(side.manager)} sent"><h5>Sent</h5>${packageContent(sent)}</div>` : ''}
        </section>`;
      }).join('');
      if (canvas) paintSelected();
    }
    const keepPosition = update => {
      const top = window.scrollY, left = window.scrollX;
      update();
      requestAnimationFrame(() => window.scrollTo({ top, left, behavior: 'instant' }));
    };
    detail.querySelectorAll('[data-step]').forEach(button => button.addEventListener('click', () => {
      const step = button.dataset.step;
      const target = step === 'previous' ? previousRoute : nextRoute;
      if (!target) return;
      keepPosition(() => {
        history.pushState(null, '', target);
        setSelected(routedId());
        const replacement = detail.querySelector(`[data-step="${step}"]`);
        if (replacement && !replacement.disabled) replacement.focus({ preventScroll: true });
      });
    }));
    detail.querySelector('.trade-back').addEventListener('click', () => {
      history.pushState(null, '', managerRoute());
      view.dataset.detailOpen = 'false';
      results.scrollTop = browseListScroll;
      window.scrollTo({ top: browseScroll, behavior: 'instant' });
    });
    range?.addEventListener('input', () => keepPosition(() => selectPoint(Number(range.value))));
    detail.querySelectorAll('[data-window]').forEach(button => button.addEventListener('click', () => keepPosition(() => {
      graphWindow = button.dataset.window; updateWindow();
      if (pointIndex > graphEnd()) selectPoint(graphEnd());
      else if (canvas) paintSelected();
    })));
    detail.querySelectorAll('[data-lens]').forEach(button => button.addEventListener('click', () => keepPosition(() => {
      const lensIndex = Number(button.dataset.lens);
      selectPoint(trade.points.indexOf(trade.lenses[lensIndex].point), lensIndex);
    })));
    selectPoint(pointIndex, pointIndex >= 0 && trade.points[pointIndex] === latest ? 1 : -1);
    if (canvas && typeof ResizeObserver !== 'undefined') {
      chartObserver = new ResizeObserver(paintSelected);
      chartObserver.observe(canvas);
    }
  }

  function paintChart(canvas, points, active, sides) {
    const context = canvas.getContext?.('2d');
    const width = canvas.clientWidth, height = canvas.clientHeight;
    if (!context || !width || !height) return;
    const scale = window.devicePixelRatio || 1;
    canvas.width = Math.round(width * scale);
    canvas.height = Math.round(height * scale);
    context.scale(scale, scale);
    context.font = '11px Arial';
    const values = points.flatMap(point => point.values.filter(Number.isFinite));
    if (!values.length) return;
    const maximum = Math.max(100, Math.ceil(Math.max(0, ...values) / 500) * 500);
    const minimum = Math.min(0, Math.floor(Math.min(0, ...values) / 500) * 500);
    const length = maximum - minimum || 1;
    const start = Date.parse(points[0].date), end = Date.parse(points.at(-1).date);
    const x = index => 47 + (width - 61) * (Date.parse(points[index].date) - start) / (end - start || 1);
    const y = value => height - 28 - (height - 42) * (value - minimum) / length;
    for (let tick = 0; tick < 4; tick++) {
      const value = minimum + length * tick / 3;
      context.strokeStyle = '#d9c8aa';
      context.beginPath();
      context.moveTo(47, y(value));
      context.lineTo(width - 14, y(value));
      context.stroke();
      context.fillStyle = '#655844';
      context.fillText(signed(Math.round(value)), 1, y(value) + 4);
    }
    context.strokeStyle = '#ab9474';
    context.beginPath();
    context.moveTo(x(active), 8);
    context.lineTo(x(active), height - 25);
    context.stroke();
    context.fillStyle = '#655844';
    const axisDate = value => new Date(value).toLocaleDateString('en-US', { month: 'short', year: 'numeric', timeZone: 'UTC' });
    context.textAlign = 'left';
    context.fillText(axisDate(points[0].date), 47, height - 5);
    context.textAlign = 'right';
    context.fillText(axisDate(points.at(-1).date), width - 14, height - 5);
    context.textAlign = 'left';
    for (let side = 0; side < sides; side++) {
      let gap = true;
      context.strokeStyle = context.fillStyle = colors[side % colors.length];
      context.lineWidth = 2;
      context.beginPath();
      for (const [index, point] of points.entries()) {
        const value = point.values[side];
        if (!Number.isFinite(value)) {
          gap = true;
          continue;
        }
        if (gap) context.moveTo(x(index), y(value));
        else context.lineTo(x(index), y(value));
        gap = false;
      }
      context.stroke();
      if (Number.isFinite(points[active].values[side])) {
        context.beginPath();
        context.arc(x(active), y(points[active].values[side]), 4, 0, Math.PI * 2);
        context.fill();
      }
    }
  }

  async function load() {
    const response = await Promise.all(['trade-workbook-archive.json', 'trade-valuations.json', 'trade-history.json'].map(async path => {
      const fetched = await fetch(path);
      if (!fetched.ok) throw new Error(path);
      return fetched.json();
    }));
    const [workbook, rated, historical] = response;
    market = rated.market;
    const dated = new Map(historical.trades.map(trade => [trade.id, trade]));
    for (const trade of rated.trades) dated.set(trade.id, trade);
    const undated = [];
    const picks = new Map();
    for (const [row, ...outcome] of workbook.outcomes) {
      if (!picks.has(row)) picks.set(row, []);
      picks.get(row).push(outcome);
    }
    for (const [row, sides, notes, original] of workbook.ledger) {
      const id = `workbook-${row}`;
      const base = { id, row, notes, original, outcomes: picks.get(row) };
      if (dated.has(id)) Object.assign(dated.get(id), base);
      else undated.unshift({ ...base, sides: sides.map(([manager, pack]) => ({ manager, package: pack })) });
    }
    trades = [...dated.values(), ...undated].filter(trade => trade.status !== 'reversed').map(learnTrade);
    trades.sort((a, b) => (b.estimatedAt || b.acceptedAt || 0) - (a.estimatedAt || a.acceptedAt || 0) || (b.row || 0) - (a.row || 0));
    const seasons = [...new Set(rated.trades.map(trade => trade.season).filter(Boolean))].sort((a, b) => b - a);
    season.innerHTML += seasons.map(year => `<option value="${year}">${year}</option>`).join('');
    season.innerHTML += '<option value="estimated">Estimated dates</option>';
    syncRoute();
    if (routedId()) view.scrollIntoView({ block: 'start' });
  }

  function updateManager() {
    const manager = managerSelect.value;
    if (currentManager === manager) return;
    currentManager = manager;
    const partners = [...new Set(trades.filter(belongsToManager).flatMap(trade =>
      trade.sides.filter(side => side.manager !== manager).map(side => side.manager)))].sort((a, b) => a.localeCompare(b));
    partner.replaceChildren(new Option('All managers', ''), ...partners.map(name => new Option(name, name)));
    search.value = '';
    season.value = '';
    sort.value = 'recent';
    selected = null;
    results.scrollTop = 0;
    view.dataset.detailOpen = 'false';
  }

  function syncRoute() {
    if (!trades) return;
    const parts = routeParts();
    const id = routedId();
    const trade = id && trades.find(row => row.id === id);
    let manager;
    if (parts[0] === 'managers' && parts[1]) {
      try { manager = decodeURIComponent(parts[1]); } catch { /* Ignore malformed saved links. */ }
    } else if (trade) manager = trade.sides[0].manager;
    if (manager && [...managerSelect.options].some(option => option.value === manager) && managerSelect.value !== manager) {
      managerSelect.value = manager;
      managerSelect.dispatchEvent(new Event('change'));
    }
    updateManager();
    if (trade && belongsToManager(trade)) {
      // A shared trade link takes precedence over a previous partner/search filter.
      if (partner.value && !trade.sides.some(side => side.manager === partner.value)) partner.value = '';
      search.value = '';
      season.value = '';
      selected = trade;
    }
    renderList();
    view.dataset.detailOpen = String(Boolean(trade && belongsToManager(trade)));
    if (hasRoute()) history.replaceState(null, '', managerRoute(trade && belongsToManager(trade) ? trade.id : undefined));
  }

  function openArchive() {
    if (trades) {
      updateManager();
      return;
    }
    loading ||= load().catch(() => {
      count.textContent = 'Trade archive could not load. Select Managers to try again.';
      loading = null;
    });
  }

  nav.addEventListener('click', openArchive);
  managerSelect.addEventListener('change', () => {
    if (trades) {
      updateManager();
      if (hasRoute()) history.replaceState(null, '', managerRoute());
      renderList();
    } else openArchive();
  });
  document.querySelectorAll('.navtabs button:not([data-view="managers"])').forEach(button =>
    button.addEventListener('click', () => {
      if (hasRoute()) history.replaceState(null, '', location.pathname + location.search);
    })
  );
  function navigateRoute() {
    if (!hasRoute()) return;
    nav.click();
    if (trades) syncRoute();
    if (routeParts()[2] === 'trades' || routeParts()[0] === 'trades') {
      requestAnimationFrame(() => view.scrollIntoView({ block: 'start' }));
    }
  }
  window.addEventListener('hashchange', navigateRoute);
  window.addEventListener('popstate', navigateRoute);
  results.addEventListener('click', event => {
    const link = event.target.closest('a');
    if (!link || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    browseScroll = window.scrollY || 0;
    browseListScroll = results.scrollTop;
    history.pushState(null, '', link.getAttribute('href'));
    setSelected(routedId());
    if (window.matchMedia('(max-width: 760px)').matches) {
      view.scrollIntoView({ block: 'start' });
      detail.querySelector('.trade-back')?.focus({ preventScroll: true });
    }
  });
  const filterTrades = () => {
    if (!trades) return;
    if (hasRoute()) history.replaceState(null, '', managerRoute());
    renderList();
    results.scrollTop = 0;
  };
  search.addEventListener('input', filterTrades);
  season.addEventListener('change', filterTrades);
  sort.addEventListener('change', filterTrades);
  partner.addEventListener('change', filterTrades);
  if (hasRoute()) navigateRoute();
})();
