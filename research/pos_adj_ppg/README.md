# Draft-Adjusted PPG research

This directory is the reproducible research layer for Dynasty Plebs rookie-draft grading. It is intentionally isolated from the production site until the benchmark passes validation.

## Public metric

**Draft-Adjusted PPG = Career PPG - Expected Career PPG(position, actual sequential rookie draft slot)**

A positive value means the rookie produced more career-to-date Dynasty Plebs points per game than the historical expectation for a rookie of the same position taken at that draft cost. A negative value means the opposite.

The public site label is **Draft-Adjusted PPG**. Internally, older research filenames may still use `pos_adj_ppg` so the audit trail remains stable.

## Locked decisions

- Outcome stays **career-to-date PPG**. There is no career-age normalization or historical age curve.
- Dynasty Plebs scoring is the outcome source of truth: 0.04/pass yard, 6/pass TD, -4/INT, 0.1/rush yard, 6/rush TD, 0.5/reception, 0.1/receiving yard, 6/receiving TD, -2/fumble lost, 2/two-point conversion, and 6/return TD.
- Historical expectation is external. No Dynasty Plebs manager, pick, win total, or current league result is allowed to train the benchmark.
- The benchmark uses the standard **12-team Dynasty Rookie** track from Fantasy Football Calculator, not its separate 2-QB ADP product.
- Training ADP classes are 2014-2022. Outcomes are scored through the last complete NFL season (2025).
- Only QB/RB/WR/TE are eligible.
- A row must represent a true rookie in its ADP year. Historical source rows for a player who had already appeared in an NFL regular-season game before that ADP year are removed.
- The production metric remains consistent with the current site eligibility rule: a rookie must have recorded at least one NFL regular-season game to receive Career PPG / Draft-Adjusted PPG.
- Veteran selections in Dynasty Plebs remain in the historical draft board but are excluded from rookie grading.
- **Draft cost is chronological, not formulaic.** Overall slot is the actual sequential selection number within that league draft year. Compensatory picks count as real selections and shift every later pick. Example: if Round 3 contains a 3.13 compensatory pick, that selection is overall 37 and the following 4.01 is overall 38.
- Each position gets its own expectation curve.
- Nearby draft slots inform one another via smoothing. Exact-slot sample means are not used.
- Smoothing bandwidth is selected independently by position using leave-one-draft-class-out validation against the final monotone curve. Deep slots widen adaptively until effective local historical support reaches 12 observations.
- The final expectation curve is constrained to be non-increasing with later draft slots. A later pick cannot have a higher historical expectation merely because of sample noise.
- Manager Draft-Adjusted PPG is the arithmetic mean of the eligible pick-level residuals. Round cards average those same residuals within the displayed round bucket; Round 4+ is only a display grouping, never the expectation model.

## Primary external source

Fantasy Football Calculator archived Dynasty Rookie ADP / REST API:

`https://fantasyfootballcalculator.com/api/v1/adp/rookie?position=all&teams=12&year=YEAR`

FFC states that ADP is based on human mock-draft selections, filters computer selections, and makes the JSON API available for reuse with attribution. The build records source metadata and SHA-256 hashes so the exact input can be audited later.

Secondary methodological cross-check: Dynasty League Football has described its long-running main historical rookie ADP as 1QB since 2014 and has separately documented materially different hit behavior by position. DLF is a research cross-check, not an input to the fitted curve.

## Generated artifacts

Running `python research/pos_adj_ppg/build_pos_adj_ppg_curve_v4.py` produces the current frozen research inputs/curve. Running `python research/pos_adj_ppg/audit_plebs_application.py` then applies that frozen curve to the complete recovered Plebs draft history.

- `adp_snapshot.json` — normalized FFC observations and source metadata used in the fit.
- `source_manifest.json` — source URLs, hashes, row counts, exclusions, and scoring definition.
- `pos_adj_ppg_curve.json` — versioned expected PPG table by position and exact overall rookie slot.
- `validation_report.md` — matching coverage, scoring calibration, LOSO results, selected bandwidths, baseline comparisons, sensitivity tests, support, and curve anchors.
- `plebs_application_audit.csv` — one row per recovered Plebs draft selection with chronological overall slot, Career PPG, expected PPG, and Draft-Adjusted PPG.
- `plebs_application_report.md` — manager-level aggregation and application integrity checks.

The build is fail-closed: scoring calibration, source shape, sample coverage, monotonicity, support, compensatory-pick sequencing, veteran exclusion, residual arithmetic, and validation invariants must pass or no production implementation should be accepted.

## Production gate

Nothing in this directory changes `index.html` by itself. Production wiring should happen only after the generated reports have been reviewed and the fitted table is committed. The eventual site implementation should read a frozen, versioned expectation table rather than recomputing a model in the browser.
