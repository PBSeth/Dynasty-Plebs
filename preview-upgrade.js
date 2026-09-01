/* Dynasty Plebs audit preview upgrade. Workbook-derived DATA is authoritative. */
(() => {
  try {
    if (!window.DATA && window.__PLEBS_DATA_SRC) (0, eval)(window.__PLEBS_DATA_SRC);
  } catch (err) {
    console.error('Dynasty Plebs DATA bootstrap failed', err);
  }
  const WB = window.DATA || {};
  if (!WB.regular || !WB.legacy || !WB.drafts) return;

  const canon = n => n === 'David Carnes' ? 'Dave Carnes' : n;
  const classicName = n => n === 'Dave Carnes' ? 'David Carnes' : n;
  const parseRecord = rec => {
    if (!rec || typeof rec !== 'string' || !rec.includes('-')) return { w: 0, l: 0 };
    const [w, l] = rec.split('-').map(Number);
    return { w: Number.isFinite(w) ? w : 0, l: Number.isFinite(l) ? l : 0 };
  };
  const fmtInt = n => Math.round(Number(n) || 0).toLocaleString('en-US');
  const norm = s => String(s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]/g, '');
  const oldStats = typeof careerDraftStats !== 'undefined' ? careerDraftStats : {};
  const oldColors = typeof managerColors !== 'undefined' ? managerColors : {};
  const colorFor = n => oldColors[n] || oldColors[classicName(n)] || '#8a6b3b';

  const activeManagers = Object.entries(WB.regular)
    .filter(([, d]) => d?.yearly?.['2025'])
    .map(([m]) => m);

  function activeYears(manager) {
    return Object.entries(WB.regular[manager]?.yearly || {})
      .filter(([, rec]) => rec)
      .map(([y]) => Number(y))
      .sort((a, b) => a - b);
  }

  function legacyScoreAt(manager, year) {
    const reg = WB.regular[manager];
    if (!reg) return null;
    const years = activeYears(manager);
    const started = years.filter(y => y <= year);
    if (!started.length) return null;
    const last = years.at(-1);
    if (year >= last && Number.isFinite(WB.legacy[manager]?.score)) return WB.legacy[manager].score;
    let w = 0, l = 0, playoffWins = 0;
    started.forEach(y => {
      const r = parseRecord(reg.yearly[String(y)]);
      w += r.w; l += r.l;
      const pr = parseRecord(WB.playoffs?.[manager]?.yearly?.[String(y)]);
      playoffWins += pr.w;
    });
    const service = started.length;
    const titles = (WB.champions || []).filter(c => c.manager === manager && Number(c.year) <= year).length;
    const pct = (w + l) ? w / (w + l) : 0;
    return pct * (1 + .05 * service + .05 * playoffWins + .50 * titles) * 1000;
  }

  function cumulativeRecord(manager, year) {
    let w = 0, l = 0;
    Object.entries(WB.regular[manager]?.yearly || {}).forEach(([ys, rec]) => {
      if (Number(ys) <= year && rec) {
        const r = parseRecord(rec); w += r.w; l += r.l;
      }
    });
    return { w, l };
  }

  function rankAtYear(manager, year) {
    const target = legacyScoreAt(manager, year);
    if (!Number.isFinite(target)) return null;
    const scores = Object.keys(WB.regular)
      .map(m => legacyScoreAt(m, year))
      .filter(Number.isFinite)
      .sort((a, b) => b - a);
    return 1 + scores.filter(v => v > target + 1e-9).length;
  }

  function currentLegacyRank(manager) {
    const value = WB.legacy[manager]?.score;
    if (!Number.isFinite(value)) return null;
    const vals = Object.values(WB.legacy).map(x => x?.score).filter(Number.isFinite).sort((a, b) => b - a);
    return 1 + vals.filter(v => v > value + 1e-9).length;
  }

  function enhanceProfile(name) {
    const manager = canon(name);
    const reg = WB.regular[manager];
    const leg = WB.legacy[manager];
    const profile = document.getElementById('profile');
    if (!profile || !reg || !leg) return;
    const years = activeYears(manager);
    const rank = currentLegacyRank(manager);
    const hero = profile.querySelector('.record-hero');
    if (hero) {
      hero.className = 'record-hero dp-legacy-hero';
      hero.innerHTML = `<div class="dp-legacy-label">Legacy Score</div><div class="dp-legacy-score">${fmtInt(leg.score)}</div>`;
    }
    const stats = profile.querySelector('.profile-stats');
    if (stats) {
      stats.className = 'profile-stats dp-profile-stats';
      stats.innerHTML = `
        <div class="profile-stat legacy-rank"><small>Legacy Rank</small><b>${rank ? `#${rank}` : '—'}</b></div>
        <div class="profile-stat"><small>Reg. Record</small><b>${reg.total || '—'}</b></div>
        <div class="profile-stat"><small>Championships</small><b>${leg.titles ?? 0}</b></div>`;
    }
    const summary = profile.querySelector('.profile-title p');
    if (summary && years.length) summary.textContent = `${years.length} seasons · ${years[0]}–${years.at(-1)}`;
    syncSeasonHistory(name);
  }

  function syncSeasonHistory(name) {
    const manager = canon(name);
    const reg = WB.regular[manager];
    const box = document.getElementById('history');
    if (!box || !reg) return;
    const supplemental = (typeof history !== 'undefined' && history?.get) ? (history.get(name) || []) : [];
    const byYear = new Map(supplemental.map(s => [Number(s.year), s]));
    const rows = Object.entries(reg.yearly)
      .filter(([, rec]) => rec)
      .map(([ys, rec]) => ({ year: Number(ys), rec, extra: byYear.get(Number(ys)) }))
      .sort((a, b) => b.year - a.year);
    box.innerHTML = rows.map(r => {
      const x = parseRecord(r.rec);
      const pct = (x.w + x.l) ? (x.w / (x.w + x.l)).toFixed(3).replace(/^0/, '') : '—';
      const team = r.extra?.team || 'League season';
      return `<div class="history-row"><div class="history-year">${r.year}</div><div class="history-team"><strong>${team}</strong></div><div class="history-record">${r.rec}<small>${pct}</small></div></div>`;
    }).join('');
  }

  let managerTimelineMode = 'legacy';

  function renderManagerTimeline(name) {
    const manager = canon(name);
    const years = activeYears(manager);
    const controls = document.getElementById('timelineControls');
    const box = document.getElementById('timelineBox');
    if (!controls || !box || !years.length) return;
    controls.className = 'dp-timeline-controls';
    const modes = [
      ['legacy', 'Legacy'],
      ['rank', 'Rank'],
      ['record', 'Reg. Record']
    ];
    controls.innerHTML = modes.map(([k, label]) => `<button data-dp-mode="${k}" class="${managerTimelineMode === k ? 'on' : ''}">${label}</button>`).join('');
    controls.querySelectorAll('button').forEach(btn => btn.onclick = () => {
      managerTimelineMode = btn.dataset.dpMode;
      renderManagerTimeline(name);
    });

    let data;
    if (managerTimelineMode === 'legacy') {
      data = years.map(y => ({ year: y, value: legacyScoreAt(manager, y), label: fmtInt(legacyScoreAt(manager, y)) }));
    } else if (managerTimelineMode === 'rank') {
      data = years.map(y => ({ year: y, value: rankAtYear(manager, y), label: `#${rankAtYear(manager, y)}` }));
    } else {
      data = years.map(y => {
        const r = cumulativeRecord(manager, y);
        return { year: y, value: r.w, label: `${r.w}-${r.l}` };
      });
    }
    drawTimelineChart(box, data, managerTimelineMode);
  }

  function drawTimelineChart(box, data, mode) {
    const W = 760, H = 260, p = { l: 52, r: 22, t: 26, b: 38 };
    const iw = W - p.l - p.r, ih = H - p.t - p.b;
    const vals = data.map(d => d.value).filter(Number.isFinite);
    if (!vals.length) { box.innerHTML = ''; return; }
    let min = 0, max = Math.max(...vals), ticks = [];
    if (mode === 'rank') {
      min = 1; max = Math.max(2, max);
      const mid = Math.max(1, Math.ceil((min + max) / 2));
      ticks = [...new Set([1, mid, max])];
    } else {
      max = Math.max(mode === 'legacy' ? 250 : 5, max);
      const stepBase = mode === 'legacy' ? 250 : 5;
      const step = Math.max(stepBase, Math.ceil((max / 4) / stepBase) * stepBase);
      max = Math.ceil(max / step) * step;
      ticks = [0, step, step * 2, step * 3, step * 4].filter(v => v <= max);
      if (!ticks.includes(max)) ticks.push(max);
    }
    const x = i => p.l + (data.length === 1 ? iw / 2 : i * iw / (data.length - 1));
    const y = v => mode === 'rank'
      ? p.t + ((v - min) / Math.max(1, max - min)) * ih
      : p.t + ((max - v) / Math.max(1, max - min)) * ih;
    const grid = ticks.map(t => `<line class="dp-grid" x1="${p.l}" x2="${W-p.r}" y1="${y(t)}" y2="${y(t)}"/><text class="dp-axis" x="${p.l-8}" y="${y(t)+3}" text-anchor="end">${mode === 'legacy' ? fmtInt(t) : (mode === 'rank' ? `#${t}` : t)}</text>`).join('');
    const pts = data.map((d, i) => ({ ...d, x: x(i), y: y(d.value) }));
    const path = pts.map((q, i) => `${i ? 'L' : 'M'} ${q.x.toFixed(1)} ${q.y.toFixed(1)}`).join(' ');
    const area = mode === 'rank' ? '' : `${path} L ${pts.at(-1).x.toFixed(1)} ${(p.t+ih).toFixed(1)} L ${pts[0].x.toFixed(1)} ${(p.t+ih).toFixed(1)} Z`;
    const dots = pts.map(q => `<circle class="dp-dot" cx="${q.x}" cy="${q.y}" r="4.5"></circle><text class="dp-point-label" x="${q.x}" y="${Math.max(11, q.y-10)}">${q.label}</text>`).join('');
    const years = pts.map(q => `<text class="dp-axis" x="${q.x}" y="${H-12}" text-anchor="middle">${q.year}</text>`).join('');
    box.className = 'dp-chart-wrap';
    box.innerHTML = `<svg class="dp-chart-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Manager career timeline">${grid}${area ? `<path class="dp-area" d="${area}"/>` : ''}<path class="dp-series" d="${path}"/>${dots}${years}</svg>`;
  }

  function statFor(year, player) {
    const base = norm(player);
    const candidates = [base, base.replace(/lll$/, 'iii'), base.replace(/ii$/, 'iii')];
    for (const k of candidates) {
      const hit = oldStats[`${year}|${k}`];
      if (hit) return hit;
    }
    return null;
  }

  function workbookPicksFor(manager) {
    const out = [];
    Object.entries(WB.drafts).forEach(([ys, draft]) => {
      const year = Number(ys);
      (draft.rounds || []).forEach((round, ri) => (round || []).forEach(pick => {
        if (pick?.owner === manager && pick?.player) out.push({ year, round: ri + 1, slot: pick.slot, player: pick.player, stat: statFor(year, pick.player) });
      }));
    });
    return out;
  }

  function eligibleDraftPicks(manager) {
    return workbookPicksFor(manager).filter(p => p.stat && p.stat.excluded !== 'veteran' && Number.isFinite(p.stat.ppg) && p.stat.pos);
  }

  function draftValueFor(manager, allTagged) {
    const mine = eligibleDraftPicks(manager);
    if (!mine.length) return null;
    const mean = a => a.length ? a.reduce((s, v) => s + v, 0) / a.length : null;
    const bucket = p => Math.min(4, p.round);
    const deltas = mine.map(p => {
      let peers = allTagged.filter(x => x.manager !== manager && x.stat.pos === p.stat.pos && bucket(x) === bucket(p));
      if (peers.length < 2) peers = allTagged.filter(x => x.manager !== manager && x.stat.pos === p.stat.pos);
      if (peers.length < 2) peers = allTagged.filter(x => x.manager !== manager && bucket(x) === bucket(p));
      if (!peers.length) peers = allTagged.filter(x => x.manager !== manager);
      const exp = mean(peers.map(x => x.stat.ppg));
      return Number.isFinite(exp) ? p.stat.ppg - exp : null;
    }).filter(Number.isFinite);
    return mean(deltas);
  }

  function enhanceRookieAnalytics(name) {
    const manager = canon(name);
    const box = document.getElementById('draftIntel');
    if (!box) return;
    box.className = 'draft-intel dp-rookie-analytics';
    const picks = workbookPicksFor(manager).filter(p => p.year <= 2025 && p.stat && p.stat.excluded !== 'veteran');
    const yearly = [...new Set(picks.map(p => p.year))].sort((a, b) => a - b).map(year => ({
      year,
      points: picks.filter(p => p.year === year).reduce((s, p) => s + (Number.isFinite(p.stat?.points) ? p.stat.points : 0), 0)
    }));
    const maxPts = Math.max(1, ...yearly.map(x => x.points));
    const bars = yearly.length ? yearly.map(x => `<div class="dp-rookie-col"><div class="dp-rookie-value">${fmtInt(x.points)}</div><div class="dp-rookie-bar" style="height:${Math.max(3, x.points / maxPts * 100)}%"></div><div class="dp-rookie-year">${x.year}</div></div>`).join('') : '<div class="empty">No scored rookie classes yet.</div>';

    const tagged = activeManagers.flatMap(m => eligibleDraftPicks(m).map(p => ({ ...p, manager: m })));
    const metrics = activeManagers.map(m => ({ manager: m, value: draftValueFor(m, tagged) })).filter(x => Number.isFinite(x.value));
    const mine = metrics.find(x => x.manager === manager);
    const sorted = metrics.map(x => x.value).sort((a, b) => b - a);
    const rank = mine ? 1 + sorted.filter(v => v > mine.value + 1e-9).length : null;
    const pct = rank && sorted.length > 1 ? Math.max(5, ((sorted.length - rank) / (sorted.length - 1)) * 100) : 0;
    box.innerHTML = `<div class="dp-rookie-block"><div class="dp-analytics-title">Rookie Points</div><div class="dp-rookie-chart">${bars}</div><div class="dp-draft-value"><h4>Pos + Round Draft Value</h4><p>Compares each rookie pick to league averages at the same position and round. Higher is better.</p><div class="dp-draft-rank"><span>Rank</span><strong>${rank || '—'}</strong><span>of ${metrics.length || activeManagers.length} active</span>${mine ? `<span class="dp-draft-score">${mine.value >= 0 ? '+' : ''}${mine.value.toFixed(2)} adj PPG/pick</span>` : ''}</div><div class="dp-rankbar"><span style="width:${pct}%"></span></div></div></div>`;
  }

  function enhanceManager(name) {
    enhanceProfile(name);
    renderManagerTimeline(name);
    enhanceRookieAnalytics(name);
  }

  let draftRoundFilter = 'all';
  function renderWorkbookDraftBoard() {
    const yearSelect = document.getElementById('leagueDraftYear');
    const box = document.getElementById('leagueDraftBoard');
    if (!yearSelect || !box) return;
    const year = String(yearSelect.value);
    const draft = WB.drafts[year];
    if (!draft) { box.innerHTML = ''; return; }
    const rounds = draft.rounds || [];
    const total = rounds.reduce((s, r) => s + (r?.length || 0), 0);
    const teams = new Set(rounds.flat().map(p => p?.owner).filter(Boolean)).size;
    const filters = ['all', ...rounds.map((_, i) => String(i + 1))];
    const tabs = `<div class="dp-round-tabs">${filters.map(f => `<button data-round="${f}" class="${draftRoundFilter === f ? 'on' : ''}">${f === 'all' ? 'All Rounds' : `R${f}`}</button>`).join('')}</div>`;
    const visible = rounds.map((round, ri) => ({ round, ri })).filter(x => draftRoundFilter === 'all' || String(x.ri + 1) === draftRoundFilter);
    const html = visible.map(({ round, ri }) => `<section class="dp-compact-round"><h3>Round ${ri + 1}<span>${round.length} picks</span></h3>${round.map(p => `<div class="dp-compact-row"><div class="dp-compact-pick">${ri + 1}.${String(p.slot).padStart(2, '0')}</div><div class="dp-compact-player">${p.player || '—'}</div><div class="dp-compact-owner" style="--owner-color:${colorFor(p.owner)}">${p.owner || '—'}</div></div>`).join('')}</section>`).join('');
    box.innerHTML = `<div class="dp-draft-summary"><span>${total} picks</span><span>${rounds.length} rounds</span><span>${teams} teams</span></div>${tabs}${html}`;
    box.querySelectorAll('.dp-round-tabs button').forEach(btn => btn.onclick = () => { draftRoundFilter = btn.dataset.round; renderWorkbookDraftBoard(); });
  }

  // Replace classic render hooks without touching the classic shell.
  if (typeof renderRookies === 'function') {
    const classicRenderRookies = renderRookies;
    renderRookies = function() {
      classicRenderRookies();
      const name = document.getElementById('managerSelect')?.value || 'Seth Miller';
      enhanceRookieAnalytics(name);
    };
  }
  if (typeof renderManager === 'function') {
    const classicRenderManager = renderManager;
    renderManager = function(name) {
      classicRenderManager(name);
      enhanceManager(name);
    };
  }

  const yearSelect = document.getElementById('leagueDraftYear');
  if (yearSelect) {
    const years = Object.keys(WB.drafts).sort((a, b) => Number(b) - Number(a));
    const keep = years.includes(String(yearSelect.value)) ? String(yearSelect.value) : years[0];
    yearSelect.innerHTML = years.map(y => `<option value="${y}">${y}</option>`).join('');
    yearSelect.value = keep;
    yearSelect.onchange = () => { draftRoundFilter = 'all'; renderWorkbookDraftBoard(); };
    renderWorkbookDraftBoard();
  }

  const managerSelect = document.getElementById('managerSelect');
  enhanceManager(managerSelect?.value || 'Seth Miller');
})();
