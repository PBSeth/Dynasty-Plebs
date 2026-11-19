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

  let market, trades, loading, selected, chartObserver;
  let filteredTrades = [];
  let preferredCheckpoint = 'endpoint';
  let browseScroll = null;
  let currentManager;
  let browseListScroll = 0;
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

  function pickLabel(asset, includeOrigin = false, at = null) {
    const origin = includeOrigin && asset.origin ? ` · ${asset.origin}` : '';
    const resolved = at != null && at >= asset.slotKnownFrom ? asset.resolvedSlot : null;
    const slot = asset.slotKnownAtTrade || resolved || `Round ${asset.round}`;
    return `${asset.season ?? 'Year unknown'} ${slot}${origin}`;
  }

  function learnTrade(trade) {
    const analyzed = metrics.evaluate(trade, market);
    trade.points = analyzed.points;
    trade.window = analyzed.window;
    trade.checkpoints = metrics.checkpoints(analyzed);
    trade.peaks = analyzed.peaks;
    const peaks = analyzed.peaks;
    const latest = analyzed.latest;
    const firstNames = trade.sides.map(side => side.manager.split(' ')[0]);
    trade.lenses = [
      { name: 'At trade', point: analyzed.baseline, originalBalance: true },
      { name: trade.checkpoints.at(-1).name, point: latest },
      ...peaks.map((point, side) => {
        const parts = trade.sides[side].manager.split(' ');
        const name = firstNames.filter(first => first === parts[0]).length > 1 ? parts.at(-1) : parts[0];
        return { name: `${name}’s best`, point, side };
      })
    ];
    const spread = (point, basis = 'changes') => {
      const values = point?.[basis];
      if (!values || !metrics.complete(values)) return -1;
      return margin(values, values.indexOf(Math.max(...values)));
    };
    trade.spreads = {
      peak: Math.max(-1, ...peaks.map(point => spread(point))), day: spread(trade.lenses[0].point, 'values'),
      latest: spread(latest, 'assetValues')
    };
    const terms = [label(trade), trade.date, trade.original, trade.dateEstimate ? 'estimated date' : 'recorded date'];
    for (const side of trade.sides) {
      for (const asset of side.assets || []) {
        terms.push(asset.kind === 'pick' ? pickLabel(asset, true) : asset.name, asset.outcome?.name, asset.outcome?.slot, asset.resolvedSlot);
      }
    }
    terms.push(...(trade.outcomes || []).flat());
    trade.search = terms.join(' ').toLowerCase();
    return trade;
  }

  function packagePreview(side, at = null) {
    if (side.package) return side.package;
    const first = side.assets?.[0];
    if (!first) return '—';
    const name = first.kind === 'pick' ? pickLabel(first, false, at) :
      first.kind === 'faab' ? `$${number.format(first.amount)} FAAB` : first.name;
    return name + (side.assets.length > 1 ? ` + ${side.assets.length - 1}` : '');
  }

  function currentStanding(trade) {
    const values = trade.lenses[1].point?.assetValues;
    const side = trade.sides.findIndex(side => side.manager === managerSelect.value);
    if (!values || !metrics.complete(values) || side < 0) return { value: '—',
      label: trade.gradeBlocked && trade.issues?.some(issue => /pick.*year|pick year/i.test(issue)) ? 'Check pick year' : 'Unrated', state: 'unrated' };
    const edge = metrics.margin(values, side);
    const leaders = trade.sides.filter((_, index) => values[index] === Math.max(...values));
    const name = leaders[0].manager.split(' ');
    const shortName = trade.sides.filter(side => side.manager.split(' ')[0] === name[0]).length > 1 ? name.at(-1) : name[0];
    return { value: edge === 0 ? 'Even' : signed(edge),
      label: leaders.length > 1 ? 'Tied lead' : `${shortName} leads`,
      state: edge > 0 ? 'ahead' : edge < 0 ? 'behind' : 'even' };
  }

  function matchingTrades() {
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
    return visible;
  }

  function renderList() {
    const visible = filteredTrades = matchingTrades();
    if (!visible.includes(selected)) {
      selected = visible[0];
      if (routedId()) history.replaceState(null, '', selected ? managerRoute(selected.id) : managerRoute());
    }
    count.textContent = `${visible.length} trade${visible.length === 1 ? '' : 's'}`;
    results.replaceChildren(...visible.map(trade => {
      const item = document.createElement('li');
      const endpoint = trade.lenses[1].point;
      const at = endpoint ? market[endpoint.i]?.[2] : null;
      const received = packagePreview(trade.sides.find(side => side.manager === managerSelect.value), at);
      const others = trade.sides.filter(side => side.manager !== managerSelect.value);
      const outgoingLabel = others.length === 1 ? 'Sent' : 'Others';
      const outgoing = others.map(side => packagePreview(side, at)).join(' / ');
      const caption = trade.date ? tradeDate(trade) : 'Date unknown';
      const standing = currentStanding(trade);
      const showPartner = !partner.value || others.length > 1;
      const edgeLabel = trade.lenses[1].name;
      const accessible = `${counterpart(trade)}; ${caption}; received ${received}; ${outgoingLabel.toLowerCase()} ${outgoing}; ${managerSelect.value} value edge ${edgeLabel.toLowerCase()}: ${standing.value}; ${standing.label}`;
      item.innerHTML = `<a href="${managerRoute(trade.id)}" aria-label="${esc(accessible)}"${marked(trade, selected?.id)}>
        <span class="trade-list-main">
          ${showPartner ? `<span class="trade-list-partner">${esc(counterpart(trade))}</span>` : ''}
          <span class="trade-list-date">${esc(caption)}</span>
          <span class="trade-list-package"><small>Received</small><span title="${esc(received)}">${esc(received)}</span></span>
          <span class="trade-list-package"><small>${outgoingLabel}</small><span title="${esc(outgoing)}">${esc(outgoing)}</span></span>
        </span>
        <span class="trade-list-edge" data-state="${standing.state}"><small>${esc(edgeLabel)}</small><strong>${standing.value}</strong><span>${esc(standing.label)}</span></span>
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
        `<li>${year} ${esc(slot)} <span class="trade-pick-outcome">(${esc(player)})</span></li>`
      ).join('')}</ul>` : ''}`;
    }
    return `<ul>${side.assets.map(asset => {
      if (asset.kind === 'faab') return `<li>$${number.format(asset.amount)} FAAB</li>`;
      if (asset.kind === 'player') return `<li>${esc(asset.name)}</li>`;
      const outcome = asset.outcome;
      const afterDraft = point && !point.original && outcome &&
        market[point.i][2] >= asset.afterDraft;
      const at = point?.original ? (trade.estimatedAt ?? trade.acceptedAt) : point ? market[point.i][2] : null;
      return `<li>${esc(pickLabel(asset, false, at))}${afterDraft ? `<span class="trade-pick-outcome"> (${esc(outcome.name)})</span>` :
        outcome && (!asset.afterDraft || !point) ? `<span class="trade-pick-outcome"> (${esc(outcome.name)})</span>` : ''}</li>`;
    }).join('')}</ul>`;
  }

  function renderDetail() {
    chartObserver?.disconnect();
    if (!selected) {
      detail.innerHTML = '<p class="trade-empty">No trades found.</p>';
      return;
    }
    const trade = selected;
    const position = filteredTrades.indexOf(trade);
    const shortNames = trade.sides.map(side => {
      const parts = side.manager.split(' ');
      return trade.sides.filter(other => other.manager.split(' ')[0] === parts[0]).length > 1 ? parts.at(-1) : parts[0];
    });
    const showChart = trade.points.some(point => point.changes.some(Number.isFinite));
    const summaries = trade.checkpoints.map(checkpoint => {
      const values = checkpoint.originalBalance ? checkpoint.point?.values : checkpoint.point?.changes;
      const available = values && metrics.complete(values);
      const dateLabel = checkpoint.point ? `${checkpoint.originalBalance && trade.dateEstimate ? 'Est. ' : ''}${formatDate(checkpoint.point.date)}`
        : checkpoint.upcoming ? 'Not reached' : 'Values unavailable';
      return `<button type="button" class="trade-summary" data-checkpoint="${checkpoint.key}" aria-pressed="false"${checkpoint.point ? '' : ' disabled'}>
        <span class="trade-summary-label">${esc(checkpoint.name)}${checkpoint.milestone ? `<small>${esc(checkpoint.milestone)}</small>` : ''}</span>
        <time>${esc(dateLabel)}</time>
        <span class="trade-summary-values" style="--side-count:${trade.sides.length}">${trade.sides.map((side, i) => `<span style="--side-color:${colors[i % colors.length]}"><small>${esc(shortNames[i])}</small><b>${signed(available ? margin(values, i) : null)}</b></span>`).join('')}</span>
        <span class="trade-summary-kind">${checkpoint.originalBalance ? 'Original edge' : 'Swing since trade'}</span>
      </button>`;
    }).join('');
    const peakRows = trade.peaks.map((point, side) => {
      const edge = point && metrics.margin(point.changes, side);
      return `<button type="button" class="trade-peak" data-peak="${side}" aria-pressed="false" style="--side-color:${colors[side % colors.length]}"${point ? '' : ' disabled'}>
        <span class="trade-peak-name">${esc(shortNames[side])}’s best</span>
        <strong>${signed(edge)}</strong>
        <time>${point ? formatDate(point.date) : 'Unavailable'}</time>
      </button>`;
    }).join('');
    const windowStatus = trade.gradeBlocked ? 'Not rated' : !trade.window.valid ? 'Window unavailable' : trade.window.closed ? 'Window ended' : 'In progress';
    detail.innerHTML = `
      <div class="trade-detail-nav">
        <button type="button" class="trade-back">Browse trades</button>
        <label class="trade-jump"><span class="trade-sr-only">Jump to trade</span><select aria-label="Jump to trade">${filteredTrades.map((row, i) => `<option value="${esc(row.id)}"${row === trade ? ' selected' : ''}>${i + 1} / ${filteredTrades.length} · ${row.date ? tradeDate(row) : 'Undated'} · ${esc(counterpart(row))}</option>`).join('')}</select></label>
        <div class="trade-stepper" role="group" aria-label="Browse trades">
          <button type="button" data-step="previous" aria-label="Previous trade"${position > 0 ? '' : ' disabled'}>Prev</button>
          <button type="button" data-step="next" aria-label="Next trade"${position >= 0 && position < filteredTrades.length - 1 ? '' : ' disabled'}>Next</button>
        </div>
      </div>
      <div class="trade-detail-heading">
        <p class="trade-execution-date">${trade.date ? tradeDate(trade) : 'Date unknown'}</p>
        <h3 class="trade-manager-names" aria-label="${esc(label(trade))}">${trade.sides.map((side, i) => `<span class="trade-manager-name" style="--side-color:${colors[i % colors.length]}">${esc(side.manager)}</span>`).join('<span class="trade-versus" aria-hidden="true">/</span>')}</h3>
        ${trade.gradeBlocked ? `<p class="trade-data-note">${esc((trade.issues || []).join(' '))}</p>` : ''}
      </div>
      <section class="trade-checkpoints" aria-label="Date checkpoints">
        <div class="trade-section-label"><h4>Checkpoints</h4><span>${esc(windowStatus)}</span></div>
        <div class="trade-summaries" role="group" aria-label="Date checkpoints" data-sides="${trade.sides.length}">${summaries}</div>
      </section>
      ${showChart ? `<section class="trade-chart" aria-label="Value change since trade">
        <div class="trade-chart-body">
          <div class="trade-section-label"><h4>Value change since trade</h4></div>
          <div class="trade-date-navigation">
            <button type="button" data-date-step="-1" aria-label="Earlier valuation date">Earlier</button>
            <select aria-label="Valuation date">${trade.points.map((point, i) => `<option value="${i}">${point.original ? 'At trade · ' : ''}${formatDate(point.date)}</option>`).join('')}</select>
            <button type="button" data-date-step="1" aria-label="Later valuation date">Later</button>
          </div>
          <div class="trade-chart-legend">${trade.sides.map((side, i) => `<span style="--side-color:${colors[i % colors.length]}">${esc(shortNames[i])}<b data-chart-value="${i}"></b></span>`).join('')}</div>
          <canvas role="img" aria-label="Package gains and losses since trade day"></canvas>
          <label class="trade-time-control"><span class="trade-sr-only">Explore valuation dates</span><input aria-label="Date shown" type="range" min="0" max="${trade.points.length - 1}" value="0"></label>
          <p class="trade-window-status">${trade.window.valid ? `${trade.window.extended ? 'Pick-adjusted window' : '3-year window'} · ${trade.window.closed ? 'Cutoff' : 'Ends'} ${trade.window.estimated ? 'approx. ' : ''}${formatDate(trade.window.cutoffDate)}` : esc(trade.window.reason)}${trade.window.stale || trade.window.hasGaps ? ' · Some values unavailable' : ''}</p>
        </div></section>` : '<p class="trade-empty">Trade-day value history unavailable.</p>'}
      <section class="trade-peaks" aria-label="Peak moments">
        <div class="trade-section-label"><h4>Peak moments</h4><span>Best swing within the window</span></div>
        <div class="trade-peak-list" role="group" aria-label="Jump to a peak moment">${peakRows}</div>
      </section>
      <div class="trade-package-date" role="status" aria-live="polite"></div>
      <div class="trade-packages" data-sides="${trade.sides.length}"></div>`;
    const canvas = detail.querySelector('canvas');
    const range = detail.querySelector('input[type="range"]');
    const dateSelect = detail.querySelector('[aria-label="Valuation date"]');
    const packages = detail.querySelector('.trade-packages');
    let pointIndex;
    const chartPoints = trade.points.map(point => ({ ...point, values: point.changes }));
    const paintSelected = () => paintChart(canvas, chartPoints, pointIndex, trade.sides.length);
    function selectPoint(index, checkpointKey = null, peakSide = null) {
      pointIndex = index;
      const point = trade.points[index];
      detail.querySelectorAll('[data-checkpoint]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.checkpoint === checkpointKey)));
      detail.querySelectorAll('[data-peak]').forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.peak) === peakSide)));
      if (range && point) {
        range.value = index;
        range.setAttribute('aria-valuetext', formatDate(point.date));
        dateSelect.value = index;
        detail.querySelectorAll('[data-date-step]').forEach(button => {
          button.disabled = Number(button.dataset.dateStep) < 0 ? index <= 0 : index >= trade.points.length - 1;
        });
        detail.querySelectorAll('[data-chart-value]').forEach(element => {
          element.textContent = signed(point.changes[Number(element.dataset.chartValue)]);
        });
      }
      const basis = point?.original ? 'Trade-day value' : 'Value change since trade';
      detail.querySelector('.trade-package-date').textContent = point ? `${basis} · ${point.original && trade.dateEstimate ? 'Est. ' : ''}${formatDate(point.date)}` : 'Package details · Values unavailable';
      const packageContent = side => side.package || side.assets?.length
        ? assetList(trade, side, point) : '<p class="trade-unrecorded">Not recorded</p>';
      packages.innerHTML = trade.sides.map((side, i) => `<section style="--side-color:${colors[i % colors.length]}" aria-label="${esc(side.manager)}’s side of the trade">
          <h4 class="trade-package-name">${esc(side.manager)}</h4>
          <div class="trade-received" aria-label="${esc(side.manager)} received">
            <h5>Received</h5>${packageContent(side)}
            <p class="trade-total"><span>${point?.original ? 'Trade-day value' : 'Value change'}</span>${point?.original ? signed(point.values[i]) : signed(point?.changes[i])}</p>
          </div>
        </section>`).join('');
      if (canvas && point) paintSelected();
    }
    const keepPosition = update => {
      const top = window.scrollY, left = window.scrollX;
      update();
      requestAnimationFrame(() => window.scrollTo({ top, left, behavior: 'instant' }));
    };
    const navigateTrade = id => {
      const row = filteredTrades.find(row => row.id === id);
      if (!row) return;
      history.pushState(null, '', managerRoute(id));
      setSelected(id);
      // Always land at the next trade's checkpoints, even when switching from
      // its predecessor's package details near the bottom of the page.
      detail.scrollIntoView({ block: 'start', behavior: 'instant' });
    };
    detail.querySelectorAll('[data-step]').forEach(button => button.addEventListener('click', () => {
      const target = filteredTrades[position + (button.dataset.step === 'previous' ? -1 : 1)];
      if (!target) return;
      const step = button.dataset.step;
      navigateTrade(target.id);
      const replacement = detail.querySelector(`[data-step="${step}"]`);
      if (replacement && !replacement.disabled) replacement.focus({ preventScroll: true });
    }));
    detail.querySelector('[aria-label="Jump to trade"]').addEventListener('change', event => navigateTrade(event.target.value));
    detail.querySelector('.trade-back').addEventListener('click', () => {
      history.pushState(null, '', managerRoute());
      view.dataset.detailOpen = 'false';
      results.scrollTop = browseListScroll;
      if (window.matchMedia('(max-width: 760px)').matches && browseScroll != null) {
        window.scrollTo({ top: browseScroll, behavior: 'instant' });
      } else view.scrollIntoView({ block: 'start', behavior: 'instant' });
      results.querySelector('[aria-current="true"]')?.focus({ preventScroll: true });
    });
    const chooseDate = index => keepPosition(() => {
      const clamped = Math.max(0, Math.min(trade.points.length - 1, index));
      preferredCheckpoint = 'endpoint';
      selectPoint(clamped, trade.checkpoints.find(checkpoint => checkpoint.point === trade.points[clamped])?.key);
    });
    range?.addEventListener('input', () => chooseDate(Number(range.value)));
    dateSelect?.addEventListener('change', () => chooseDate(Number(dateSelect.value)));
    detail.querySelectorAll('[data-date-step]').forEach(button => button.addEventListener('click', () => chooseDate(pointIndex + Number(button.dataset.dateStep))));
    detail.querySelectorAll('[data-checkpoint]').forEach(button => button.addEventListener('click', () => keepPosition(() => {
      const checkpoint = trade.checkpoints.find(checkpoint => checkpoint.key === button.dataset.checkpoint);
      preferredCheckpoint = checkpoint.key;
      selectPoint(trade.points.indexOf(checkpoint.point), checkpoint.key);
    })));
    detail.querySelectorAll('[data-peak]').forEach(button => button.addEventListener('click', () => keepPosition(() => {
      const side = Number(button.dataset.peak);
      preferredCheckpoint = 'endpoint';
      selectPoint(trade.points.indexOf(trade.peaks[side]), null, side);
    })));
    const initial = trade.checkpoints.find(checkpoint => checkpoint.key === preferredCheckpoint && checkpoint.point)
      || trade.checkpoints.find(checkpoint => checkpoint.key === 'endpoint' && checkpoint.point);
    selectPoint(initial ? trade.points.indexOf(initial.point) : trade.points.length - 1, initial?.key);
    if (canvas && typeof ResizeObserver !== 'undefined') {
      chartObserver = new ResizeObserver(paintSelected);
      chartObserver.observe(canvas);
    }
  }

  function paintChart(canvas, points, active, sides) {
    if (!points[active]) return;
    const context = canvas.getContext?.('2d');
    const width = canvas.clientWidth, height = canvas.clientHeight;
    if (!context || !width || !height) return;
    const scale = window.devicePixelRatio || 1;
    canvas.width = Math.round(width * scale);
    canvas.height = Math.round(height * scale);
    context.scale(scale, scale);
    context.font = '12px Arial';
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
      if (!matchingTrades().includes(trade)) {
        partner.value = '';
        search.value = '';
        season.value = '';
      }
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
    view.dataset.detailOpen = 'false';
    results.scrollTop = 0;
  };
  search.addEventListener('input', filterTrades);
  season.addEventListener('change', filterTrades);
  sort.addEventListener('change', filterTrades);
  partner.addEventListener('change', filterTrades);
  const siteHeader = document.querySelector('body > header');
  if (siteHeader) {
    const measureHeader = () => view.style.setProperty('--trade-header-height', `${siteHeader.getBoundingClientRect().height}px`);
    measureHeader();
    if (typeof ResizeObserver !== 'undefined') new ResizeObserver(measureHeader).observe(siteHeader);
  }
  if (hasRoute()) navigateRoute();
})();
