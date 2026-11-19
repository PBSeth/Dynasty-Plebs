# Trade evaluation window

Every production trade comparison is prepared by `PLEBS_TRADE_METRICS.evaluate`.
`analyze` is the underlying relative-value operation, not an unbounded UI entry
point. The raw archive remains untrimmed so source evidence can be audited.

## Deadline

- Three calendar years after the original trade date; clamp February 29 to
  February 28 in a non-leap anniversary year.
- Extend, if necessary, through the last day of February following the second
  NFL season of the latest draft class originally included in the deal.
  A 2027 pick gets through February 2029, whether it becomes a star or a bust.
- Pick round, selected player, actual draft timestamp, re-trades, retirement,
  prices and manager identity never move the deadline. No per-player patches.
- Unknown pick years or missing/invalid trade dates do not acquire a guessed
  deadline or a new grade. Existing estimated trade dates remain estimates;
  they receive an estimated-cutoff label rather than false precision.

## Observations and comparisons

Use only published archive rows dated between the trade date and the earlier
of the deadline and the latest source snapshot date. No interpolation and no
synthetic point at the deadline. Original unmade picks keep original pick
prices; selected players enter only through the existing documented timing.

The bounded points feed the graph, slider, package dates and prices, both
manager peaks, endpoint swing, list value edge and edge sorting. The original
grade retains its comparison allowance; later growth excludes allowances.
List edge remains remaining package value; detail swing remains the difference
in changes from the original baseline. These are intentionally distinct views.

Active windows say `Now` / `In progress`. Ended windows say `At cutoff` /
`Window ended`; the endpoint card shows the actual quote date. Estimated trade
dates use `Est. cutoff`. An ended period is not proof of complete pricing.

The endpoint is the final available source row on or before the deadline,
never the final *complete* row. Null values remain null. If that row is more
than 45 calendar days before the evaluation end, the endpoint is unavailable.
Older observed peaks remain inspectable; missing values are indicated beside
the graph. Grades blocked by existing provenance checks remain blocked.

There is no career-wide trade-value sum in the current production UI. Any
future rollup must consume these bounded evaluations, retain unavailable values
as unavailable, and distinguish active from ended windows. Do not sum peaks
as realized gains or assume received assets were held throughout the window.

## Ranking omissions

A missing quote is not zero. Previously observed names receive an estimated
unranked zero only after at least 30 days absent across at least two broad
feeds (each covering the configured replacement-rank number of identified
players). Reappearance resets the clock. Brief/narrow-feed gaps stay missing,
and no later evidence fills earlier gaps backward. Explicit published prices
and the existing rank-curve replacement floor are unchanged.

This is still estimated market value, not fantasy production or championship
value. Three years is an agreed evaluation policy, not a statistically proven
optimal holding period. Evaluate future policy changes across the archive,
rather than selecting an endpoint that improves individual outcomes.

## Checks

Run `node research/trade_ui/verify-window.cjs`, `verify-relative.cjs`, and
`verify-list.cjs`, plus `python research/market_estimates/verify_quote_recovery.py
--cache <source-cache>`. Window tests cover post-cutoff spikes, future classes,
outcome independence, leap years, missing/invalid dates, estimated dates,
active windows, missing/stale endpoints, multi-manager trades and source
preservation. Quote tests include a real temporary omission and synthetic
reappearance, feed-depth and absence-duration checks.
