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
