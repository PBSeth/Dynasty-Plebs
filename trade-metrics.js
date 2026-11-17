/* Trade-day-relative comparisons shared by the graph and summary cards. */
(function (root) {
  const complete = values => values.length > 1 && values.every(Number.isFinite);
  const margin = (values, side) => complete(values)
    ? values[side] - Math.max(...values.filter((_, index) => index !== side)) : null;
  function analyze(points, sides) {
    const baseline = points.find(point => point.original);
    const relative = points.map(point => ({
      ...point,
      changes: point.values.map((value, side) => Number.isFinite(value) &&
        Number.isFinite(baseline?.values[side]) ? value - baseline.values[side] : null)
    }));
    const base = relative.find(point => point.original);
    const candidates = relative.filter(point => complete(point.changes));
    const peaks = sides.map((_, side) => candidates.reduce((best, point) =>
      !best || margin(point.changes, side) > margin(best.changes, side) ? point : best, null));
    const latest = relative.at(-1);
    return { points: relative, baseline: base, peaks,
      latest: latest && !latest.original ? latest : null };
  }
  const api = { analyze, margin, complete };
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.PLEBS_TRADE_METRICS = api;
})(typeof window === 'undefined' ? globalThis : window);
