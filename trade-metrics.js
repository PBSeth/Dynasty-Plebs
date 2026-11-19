/* Trade-day-relative comparisons shared by the graph and summary cards. */
(function (root) {
  const DAY = 86400000;
  const MAX_SNAPSHOT_AGE_DAYS = 45;
  const dateValue = value => {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
    const timestamp = Date.parse(value + 'T00:00:00Z');
    return Number.isFinite(timestamp) && new Date(timestamp).toISOString().slice(0, 10) === value ? timestamp : null;
  };
  const isoDate = timestamp => new Date(timestamp).toISOString().slice(0, 10);
  // Clamp leap-day anniversaries rather than rolling them into March.
  function anniversary(timestamp, years) {
    const source = new Date(timestamp), year = source.getUTCFullYear() + years;
    const month = source.getUTCMonth();
    const day = Math.min(source.getUTCDate(), new Date(Date.UTC(year, month + 1, 0)).getUTCDate());
    return Date.UTC(year, month, day);
  }

  function evaluationWindow(trade, asOf) {
    const start = dateValue(trade.date), observed = dateValue(asOf);
    const picks = (trade.sides || []).flatMap(side => side.assets || []).filter(asset => asset.kind === 'pick');
    const knownYears = picks.every(pick => Number.isInteger(pick.season) && pick.season >= 1900 && pick.season < 9997);
    if (start == null || observed == null || !knownYears) {
      return { valid: false, reason: !knownYears ? 'Pick year unavailable' : 'Date unavailable', estimated: Boolean(trade.dateEstimate) };
    }
    const baseEnd = anniversary(start, 3);
    // A draft class's second NFL season ends the following February. Use the
    // whole month, independent of annual playoff schedules or player outcomes.
    const pickEnd = picks.length ? Date.UTC(Math.max(...picks.map(pick => pick.season)) + 2, 2, 1) - DAY : baseEnd;
    const cutoff = Math.max(baseEnd, pickEnd);
    return { valid: true, startDate: trade.date, cutoffDate: isoDate(cutoff),
      endDate: isoDate(Math.min(cutoff, observed)), closed: observed >= cutoff,
      extended: cutoff > baseEnd, estimated: Boolean(trade.dateEstimate) };
  }
  const complete = values => values.length > 1 && values.every(Number.isFinite);
  const margin = (values, side) => complete(values)
    ? values[side] - Math.max(...values.filter((_, index) => index !== side)) : null;
  // A package-comparison allowance is not an asset a manager owns. Keep it
  // in the original grade, but exclude it from every asset-growth comparison.
  const assetValues = point => point?.values.map((value, side) => {
    const allowance = point.adjustments?.[side] ?? 0;
    return Number.isFinite(value) && Number.isFinite(allowance) ? value - allowance : null;
  });
  function analyze(points, sides) {
    const baseline = points.find(point => point.original);
    const baselineAssets = assetValues(baseline);
    const relative = points.map(point => {
      const assets = assetValues(point);
      return { ...point, assetValues: assets,
        changes: assets.map((value, side) => Number.isFinite(value) &&
          Number.isFinite(baselineAssets?.[side]) ? value - baselineAssets[side] : null)
      };
    });
    const base = relative.find(point => point.original);
    const candidates = relative.filter(point => complete(point.changes));
    const peaks = sides.map((_, side) => candidates.reduce((best, point) =>
      !best || margin(point.changes, side) > margin(best.changes, side) ? point : best, null));
    const latest = relative.at(-1);
    return { points: relative, baseline: base, peaks,
      latest: latest && !latest.original ? latest : null };
  }
  // All production comparisons must enter through this function. Keep the
  // source archive intact, but never expose post-window quotes to any lens.
  function evaluate(trade, market) {
    const window = evaluationWindow(trade, market.at(-1)?.[0]);
    const adjustments = new Map((trade.timelineAdjustments || []).map(([i, ...values]) => [i, values]));
    const points = [];
    if (window.valid && !trade.gradeBlocked && trade.day) points.push({ i: trade.day[0], date: trade.date,
      values: trade.day[1], adjustments: trade.dayAdjustments, original: true });
    if (window.valid && !trade.gradeBlocked) for (const [i, ...values] of trade.timeline || []) {
      const date = market[i]?.[0];
      if (dateValue(date) != null && date >= trade.date && date <= window.endDate) {
        points.push({ i, date, values, adjustments: adjustments.get(i) });
      }
    }
    const analyzed = analyze(points.filter(point => point.date <= window.endDate), trade.sides);
    const endpoint = analyzed.latest;
    window.stale = Boolean(window.valid && (!endpoint ||
      (dateValue(window.endDate) - dateValue(endpoint.date)) / DAY > MAX_SNAPSHOT_AGE_DAYS));
    window.hasGaps = analyzed.points.some(point => !complete(point.assetValues));
    // A missing/stale endpoint stays unavailable; do not select an earlier
    // complete quote or a later quote merely because it produces a grade.
    if (window.stale) analyzed.latest = null;
    return { ...analyzed, window };
  }
  // Milestones use the last published observation on or before the target.
  // Never borrow a future price, skip an incomplete row, or duplicate the
  // three-year anniversary when it is also the closed window's cutoff.
  function checkpoints(evaluation) {
    const { points, baseline, latest, window } = evaluation;
    const start = dateValue(window.startDate), end = dateValue(window.endDate);
    const at = (target, key, name) => {
      const targetDate = target == null ? null : isoDate(target);
      const upcoming = target != null && end != null && target > end;
      const candidate = !upcoming && targetDate
        ? points.filter(point => !point.original && point.date <= targetDate).at(-1) : null;
      const point = candidate && (target - dateValue(candidate.date)) / DAY <= MAX_SNAPSHOT_AGE_DAYS ? candidate : null;
      return { key, name, targetDate, point, upcoming };
    };
    const result = [{ key: 'original', name: 'At trade', point: baseline, targetDate: window.startDate, originalBalance: true }];
    result.push(at(start == null ? null : anniversary(start, 1), 'year1', '1 year'));
    const third = start == null ? null : anniversary(start, 3);
    const endpoint = { key: 'endpoint', name: !window.valid ? 'Window end' : window.closed
      ? (window.estimated ? 'Est. cutoff' : 'At cutoff') : 'Now', point: latest,
      targetDate: window.endDate };
    if (window.closed && third != null && isoDate(third) === window.cutoffDate) {
      endpoint.milestone = '3 years';
    } else result.push(at(third, 'year3', '3 years'));
    result.push(endpoint);
    return result;
  }
  const api = { analyze, evaluate, evaluationWindow, checkpoints, margin, complete, MAX_SNAPSHOT_AGE_DAYS };
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.PLEBS_TRADE_METRICS = api;
})(typeof window === 'undefined' ? globalThis : window);
