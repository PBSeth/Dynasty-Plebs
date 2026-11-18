# Plebs independent market estimates

This implementation uses dated, openly available inputs rather than importing a restricted calculator-history feed. It is a retrospective estimate model, not a claim that KTC or FantasyCalc published these historical numbers.

## Inputs and calibration

- 371 immutable DynastyProcess 1QB source revisions from February 2019 through November 13, 2026 supply the historical player and unmade-pick inputs. The established historical pick-input reconstruction remains the first stage.
- Small, individually checked FantasyCalc and KTC comparisons supply a broad current player/pick curve reference: 16 assets, two provider families, November 17 quotes against November 13 rank inputs. KTC variants are not counted as independent providers. These are calibration examples, not a bulk live data feed.
- The CC0 SafeLeagues transaction archive supplies actual early-year packages. Filtering 12-team, one-QB, single-copy dynasty leagues and deduplicating overlapping seasons yields 5,492 unique trades. Requiring fresh preceding rankings and complete supported asset packages leaves 2,527. Budget assets, ambiguous slot IDs, missing prices, unsupported packages and stale inputs are excluded rather than silently valued at zero.
- Of those, 1,517 trades fit the consolidation parameter. Another 685 from excluded leagues and 325 from later dates provide package diagnostics. The value-curve shape is fixed before fitting consolidation: allowing both a completely flat curve and a free count adjustment to fit trade equality is not identifiable.

The market-reference calibration is retrospective and uses 2026 comparisons. The later-date split is later than the consolidation training period; it is not a claim that the entire model was trained before 2021. Source leagues and expert rankings use PPR rather than a dedicated half-PPR sample. No player-specific overrides are used.

## One curve and one package rule

Published source values are converted back to their implied ranking proxy. A fitted elite exponential plus a replacement-depth component then prices both players and picks on one 10,000-point scale. The replacement rank is fixed at 444, matching Plebs' 12 teams times 30 roster, three taxi and four reserve positions. It prevents a nonzero floor from assigning substantial value to unlimited replacement-level assets.

The curve has two fitted parameters. A third parameter, learned separately from completed trade packages, supplies a consolidation allowance. In a fully priced two-sided trade, it applies only when the side receiving fewer positive-value pieces also receives the strongest player. Its allowance is the strongest player's value times the per-extra-piece coefficient times the piece-count difference. Pure-pick swaps and incomplete or multiway packages receive no invented consolidation allowance. Zero-value pieces do not create extra allowance.

The resulting adjusted totals are comparative trade values; an allowance is not another asset owned by the manager. The original trade-grade comparison retains this allowance. The graph, received-value changes, current swing and manager-best swings subtract the allowance from each snapshot before comparing with the trade-day asset baseline. This prevents a changing package allowance from masquerading as asset appreciation. This is our own estimated package rule, not an implementation of KTC's proprietary adjustment.

## Historical safeguards

Trade-day inputs come from the most recent source published before execution or the existing labeled date estimate. At trade time, an unmade pick stays a pick regardless of its eventual selection. Only post-draft observations can switch to the documented player. FAAB remains separately listed. Existing incomplete-trade and missing-price guards, original packages, recorded dates, date-estimation windows, source revisions and pick outcomes remain intact.

The same fixed asset curve prices all four lenses. No new calculator joining the source mix can create an artificial historical peak. Growth peaks are the largest observed asset-only swings since the trade-day baseline at available source snapshots, not proof of an unobserved daily maximum.

## March 11, 2025 trade audit

Trade `sleeper-1205285790439981056` compares Seth Miller's first-round pick with Dave Carnes' Derrick Henry, first-round pick and third-round pick. The original snapshot contains no verified `slotKnownAtTrade` fields for these picks. The final draft outcomes identify 1.01/Jeanty, 1.02/Hampton and 3.06/Hunter, but the captured draft-order object does not establish when that order was fixed. Do not backfill the original grade from the eventual player selections or assume the draft creation/start timestamp records the order-setting time.

At the March 7, 2025 preceding snapshot, generic pick/player values total 4,005 for Seth and 9,892 for Dave. At the November 13, 2026 snapshot, actual asset values total 6,908 and 8,220 respectively. Therefore the received-asset changes are +2,903 and -1,672; the net swing since trade is +4,575 to Seth. Dave's current asset package still leads by 1,312. The previous +9,392 swing mistakenly included a 4,817-point consolidation allowance on Seth's package. Original-grade sensitivity to the unconfirmed slots remains a separate input limitation, not a reason to insert hindsight values.

## Validation and reproduction

`open-market-validation.json` contains all aggregate diagnostics. The metric is the absolute log gap between the two sides of actual completed trades, which measures market-clearing consistency. It is not winner-prediction accuracy or a community-consensus label.

`fit_open_market.py --cache <captures> --benchmarks <small-checked-quote-fixture>` fits the frozen configuration in `trade-value-model.json`. It requires numpy, scipy and pyarrow. Raw SafeLeagues captures come from `https://github.com/dynastyprocess/data-mfl_public`, directories `safeleagues/league` and `safeleagues/transactions`, partitions 2019–2021. The raw files are cached and not republished by the site.

`python refresh-trade-archive.py --cache <captures> --offline` rebuilds the site archive using only the standard library. `--source-values --output <baseline.json>` retains an audit-only baseline mode. `verify_archive.py` checks archive integrity, no later draft outcomes in original grades, quote timing, monotonicity, missing-data guards and the five current player/pick ratio comparisons.

The site serves frozen estimates; page loads do not call these providers. The public page keeps a short estimate credit and a consolidation line rather than a methodology wall. The configuration and aggregate validation preserve the details for review.
