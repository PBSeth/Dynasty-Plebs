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

Trade `sleeper-1205285790439981056` is now priced as 2025 1.01 versus Derrick Henry + 2025 1.02 + 2025 3.06. The recovered positions come from the original-roster draft order, with the manager confirming that offseason positions were already known. Jeanty, Hampton and Hunter do not contribute their player values to the original grade.

At the March 7, 2025 preceding snapshot, exact pick/player values total 6,413 for Seth and 11,744 for Dave. At the November 13, 2026 snapshot, actual asset values total 6,908 and 8,220 respectively. Therefore the received-asset changes are +495 and -3,524; the net swing since trade is +4,019 to Seth. Dave's current asset package still leads by 1,312. The former +9,392 swing included a 4,817-point consolidation allowance and generic rather than exact original slots.

## Pick-slot recovery

`research/pick_slots/recovery-audit.json` records the recovery totals and remaining unresolved inputs. Missing slots are restored from the workbook outcome table or the original-roster positions in completed Sleeper drafts. January 1 of the pick year is the conservative offseason boundary used for resolved positions, based on the manager's confirmation that offseason slots were known. A future pick traded in the preceding season remains generic in its original grade and switches to a slot-specific pick quote only after that boundary. An estimated execution window that crosses the boundary is not marked as definitely slot-known at trade; its sensitivity analysis evaluates both sides of the boundary. Existing explicitly recorded slots are retained.

The dated source calculator reconstruction also retains discounted exact-slot projections for future years. This supports early-offseason trades when the available preceding source snapshot still uses the previous rookie class. It uses the same dated source curve and future discount, never a later player valuation.

Explicit possessives in the workbook recover 19 previously unlinked future picks. Three more 2025 seconds have unique ownership paths across all recorded workbook/Sleeper transfers, verified against every recorded sender. Workbook row 133's future third is restored to Luke's received package, as the original wording states.

The live spreadsheet's original cell fills supply final drafting ownership, with the color legend taken from manager-name cells. These owners agree with the Sleeper draft results. Reversing all later recorded pick transfers identifies the pair of fourths in workbook row 164 as 4.09 (Damien Martinez) and 4.12 (Tai Felton): Metz's third drafted fourth, 4.11 (Shedeur Sanders), arrived in a separate later recorded trade. This is a reconstruction from final ownership and recorded transfers. `sheet-color-evidence.json` preserves the cell references, fills, source hash and inference. Left-hand manager labels in the sheet are not treated as original pick identities because some differ from Sleeper's recorded order.

The manager confirmed that the fifth Seth received from Dave in workbook row 150 was Dave's own pick. It is restored as 2025 5.02 (Chimere Dike), while the missing intervening ownership event remains a historical-log gap. The manager also approved locking in the fourth Seth received from Clint in workbook row 165 as Dave's 2025 4.02 (Ollie Gordon II). Dave had sent this fourth to Clint in workbook row 155 on June 4, 2024, before Clint's September 4 trade with Seth. All four previously anonymous pick identities are now resolved. The unrecorded intervening ownership events remain historical-log gaps; no extra trades are invented to fill them. The 4.02 linkage is recorded as a user-approved reconstruction.

## Missing current quotes and 2024 selections

A previously quoted player who disappears from a later ranking feed covering at least 444 identified players receives an explicit zero estimate. This applies only after the player has appeared in a dated source; unknown identities and missing quotes before first appearance remain unavailable. No later player quote is imported into an earlier snapshot. Trade details disclose these current zero estimates, and the archive records their names. This resolves out-of-feed veterans such as Robert Woods without treating every missing identity as worthless.

For documented 2024 pick outcomes missing a selection timestamp, completed Sleeper roster-setup player lists provide a conservative upper bound. The setup cannot supply rookie slots or the actual selection date. A pick switches to its documented player only after that upper bound, while original grades continue to use pick values. This repairs the 2024 5.07/Clyde Edwards-Helaire transition and the same gap in other 2024 selections.

The list previews use the latest known slot, independently of whether that slot was known when traded. Workbook row 160 therefore displays 2025 4.05 (Tory Horton in details), while its 2024 original grade continues to use a future fourth.

`research/pick_slots/kamara-year-evidence.json` resolves the year typos in rows 98 and 122. Dave's 2023 first passes to Travis in row 86, to Seth in the Godwin trade (row 98), and to Clawson in the November 2022 Kamara trade (row 122). Bo's 2023 second passes to Seth in row 117, then to Clawson in row 122. The 2023 draft's 1.05 (Quentin Johnston) and 2.10 (Marvin Mims) cells both use Clawson's ownership fill. The 2022 1.05 uses Travis's fill and follows a separate recorded Alex-to-Travis transfer. Together the source colors and acquisition chains support correcting the two trades' mislabeled pick years to 2023 while retaining the ESPN dates. Original workbook wording is preserved alongside correction provenance. Both November 2022 original pick values remain generic future-round values; exact slots and eventual players do not affect the original grade.

## Validation and reproduction

`open-market-validation.json` contains all aggregate diagnostics. The metric is the absolute log gap between the two sides of actual completed trades, which measures market-clearing consistency. It is not winner-prediction accuracy or a community-consensus label.

`fit_open_market.py --cache <captures> --benchmarks <small-checked-quote-fixture>` fits the frozen configuration in `trade-value-model.json`. It requires numpy, scipy and pyarrow. Raw SafeLeagues captures come from `https://github.com/dynastyprocess/data-mfl_public`, directories `safeleagues/league` and `safeleagues/transactions`, partitions 2019–2021. The raw files are cached and not republished by the site.

`python refresh-trade-archive.py --cache <captures> --offline` rebuilds the site archive using only the standard library. `--source-values --output <baseline.json>` retains an audit-only baseline mode. `verify_archive.py` checks archive integrity, no later draft outcomes in original grades, quote timing, monotonicity, missing-data guards and the five current player/pick ratio comparisons.

The site serves frozen estimates; page loads do not call these providers. The public page keeps a short estimate credit and a consolidation line rather than a methodology wall. The configuration and aggregate validation preserve the details for review.
