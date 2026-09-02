# POS ADJ PPG research

This directory is the reproducible research layer for Dynasty Plebs rookie-draft grading. It is intentionally isolated from the production site until the benchmark passes validation.

## Public metric

**POS ADJ PPG = Career PPG - Expected Career PPG(position, rookie draft slot)**

A positive value means the rookie produced more career-to-date Dynasty Plebs points per game than the historical expectation for a rookie of the same position taken at that exact 12-team draft cost. A negative value means the opposite.

The public site label is **POS ADJ PPG**. `PAP` may be used only as an internal shorthand.

## Locked decisions

- Outcome stays **career-to-date PPG**. There is no career-age normalization or historical age curve.
- Dynasty Plebs scoring is the outcome source of truth: 0.04/pass yard, 6/pass TD, -4/INT, 0.1/rush yard, 6/rush TD, 0.5/reception, 0.1/receiving yard, 6/receiving TD, -2/fumble lost, 2/two-point conversion, and 6/return TD.
- Historical expectation is external. No Dynasty Plebs manager, pick, win total, or current league result is allowed to train the benchmark.
- The benchmark uses the standard **12-team Dynasty Rookie** track from Fantasy Football Calculator, not its separate 2-QB ADP product.
- Training ADP classes are 2014-2022. Outcomes are scored through the last complete NFL season (2025).
- Only QB/RB/WR/TE are eligible.
- A row must represent a true rookie in its ADP year. Historical source rows for a player who had already appeared in an NFL regular-season game before that ADP year are removed.
- The production metric remains consistent with the current site eligibility rule: a rookie must have recorded at least one NFL regular-season game to receive Career PPG / POS ADJ PPG.
- Veteran selections in Dynasty Plebs remain in the historical draft board but are excluded from rookie grading.
- Draft cost uses the actual Plebs slot: `overall slot = (round - 1) * 12 + pick-in-round`.
- Each position gets its own expectation curve.
- Nearby draft slots inform one another via smoothing. Exact-slot sample means are not used.
- Smoothing bandwidth is selected independently by position using leave-one-draft-class-out validation. A one-standard-error rule favors the smoother model when predictive error is effectively tied.
- The final expectation curve is constrained to be non-increasing with later draft slots. A later pick cannot have a higher historical expectation merely because of sample noise.
- Manager POS ADJ PPG is the arithmetic mean of the eligible pick-level residuals. Round cards average those same residuals within the displayed round bucket; Round 4+ is only a display grouping, never the expectation model.

## Primary external source

Fantasy Football Calculator archived Dynasty Rookie ADP / REST API:

`https://fantasyfootballcalculator.com/api/v1/adp/rookie?position=all&teams=12&year=YEAR`

FFC states that ADP is based on human mock-draft selections, filters computer selections, and makes the JSON API available for reuse with attribution. The build records source metadata and SHA-256 hashes so the exact input can be audited later.

Secondary methodological cross-check: Dynasty League Football has described its long-running main historical rookie ADP as 1QB since 2014 and has separately documented materially different hit behavior by position. DLF is a research cross-check, not an input to the fitted curve.

## Generated artifacts

Running `python research/pos_adj_ppg/build_pos_adj_ppg_curve.py` produces:

- `adp_snapshot.json` — normalized FFC observations and source metadata used in the fit.
- `source_manifest.json` — source URLs, hashes, row counts, exclusions, and scoring definition.
- `pos_adj_ppg_curve.json` — versioned expected PPG table by position and exact overall rookie slot.
- `validation_report.md` — matching coverage, scoring calibration, LOSO results, selected bandwidths, baseline comparisons, sensitivity tests, support, and curve anchors.

The build is fail-closed: scoring calibration, source shape, sample coverage, monotonicity, and validation invariants must pass or no research artifact is accepted.

## Production gate

Nothing in this directory changes `index.html` by itself. Production wiring should happen only after the generated report has been reviewed and the fitted table is committed. The eventual site implementation should read a frozen, versioned expectation table rather than recomputing a model in the browser.
