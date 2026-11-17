# Dynasty Plebs

League-history archive for Dynasty Plebs, with completed league history beginning in 2019 plus the current rookie-draft and future-pick ledger.

## Source of truth

`Dynasty Plebs.xlsx` is the authoritative source for Dynasty Plebs league data. Site corrections and future updates should be checked against that workbook first rather than reconstructed from screenshots or memory.

The workbook currently governs:

- Regular-season records and win percentages
- Playoff records
- Legacy Score inputs and results
- Final yearly finishes and championships
- Rookie draft history
- 2027 projected draft order and pick ownership
- Potential compensation picks
- Trade log

Sleeper, ESPN screenshots, and other historical captures can be used as supporting evidence or for metadata that is not represented in the workbook, but they do not supersede workbook values.

## Legacy Score

Dynasty Plebs uses the locked formula:

`Legacy Score = Reg Season Win % × (1 + 0.05 × Service Time + 0.05 × Playoff Wins + 0.50 × Championships) × 1000`

Playoff bye weeks count as playoff wins for the Legacy formula.

## Identity rule

Sleeper handles and older ESPN identities are merged only when the supplied history makes the match clear. Unknown identities remain separate rather than being guessed.

## App

Static HTML/CSS/JS deployed through Vercel. The production build uses the modular workbook-verified data bundle (`data-v3-01.js` through `data-v3-07.js`) with `app-v2.js` and `site-v2.css`.

## Trade Review

The workbook-backed trade log and matched draft picks live in `trade-workbook-archive.json`. The row numbers refer to the workbook’s Trade Log tab. The site merges those entries with the completed Sleeper trades in `trade-valuations.json`. The dated archive keeps each received package, the time Sleeper recorded completion, and the linked pick outcomes. Workbook trades keep their original wording and stay ungraded until their dates and asset details are verified.

`python3 refresh-trade-archive.py --cache /path/to/cache` rebuilds the dated archive from the Sleeper league chain and the [DynastyProcess value archive](https://github.com/DynastyProcess/data/commits/master/files/values.csv). Use `--league-id` to start from a newer Sleeper season and `--offline` to repeat a build against the same captured inputs. The production build serves the frozen output, so page loads and deployments do not depend on either API.

The snapshot array holds a publication date, source revision, and timestamp for each 1QB value file. The trade-day index points to the most recent source published at or before completion. Follow-up totals are sampled on published dates, with one closing snapshot per day. The peak for each manager is their largest signed margin over the strongest other package on a common post-trade snapshot. Latest uses the newest archived snapshot.

Unspent picks use the published round price. A documented draft slot on trade day may use its exact slot price. When only exact slot prices are available, the round value is the median of the 12 published slots. Live Sleeper pick outcomes use the league’s reported linear draft order and draft results. The pick stays a pick through trade-day calculation and switches to the drafted player after the recorded draft completion, since per-pick timestamps are unavailable. FAAB is listed separately. Missing market prices leave a package ungraded. The market source and [its license](trade-market-LICENSE.txt) are linked in the site.

To add a dated workbook trade, pass `--dated-workbook-trades` a JSON array using the dated archive trade shape. Each record needs its existing `workbook-<row>` ID, a verified `acceptedAt` timestamp in epoch milliseconds, a `dateSource`, and the managers’ original asset packages. Include `slotKnownAtTrade` only with contemporaneous evidence. On a resolved pick, record the outcome alongside the pick and include `afterDraft` as an epoch-millisecond timestamp. The builder merges the priced record with the original workbook row in the site.
