/* Trade-day-relative comparisons shared by the graph and summary cards. */
(function (root) {
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
  const api = { analyze, margin, complete };
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.PLEBS_TRADE_METRICS = api;
})(typeof window === 'undefined' ? globalThis : window);
