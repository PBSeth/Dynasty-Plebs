# Dynasty Plebs Draft-Adjusted PPG final audit

## Locked public definition

**Career PPG minus the expected Career PPG for a rookie at the same position and draft slot.**

## Final integrity gates

- Frozen curve: `pos-adj-ppg-v4-research`
- Scored rookie picks: **377**
- Veteran selections excluded: **9**
- Unscored/future rookie picks: **71**
- Position resolved from same-year FFC rookie ADP: **126** draft events
- Position resolved from historical NFL draft data: **147** draft events
- Remaining Plebs/Sleeper position fallbacks: **184** draft events
- Position disagreements corrected across external audits: **3**
- FFC vs NFL draft position conflicts on overlapping identities: **0**.
- Compensatory-pick sequencing: **passed**.
- Career-age adjustment: **none**.
- Plebs manager/results data used to train expectation: **none**.

### Corrected later-position conversions

| Year | Pick | Player | Later metadata | Rookie position |
|---:|---:|---|---|---|
| 2019 | 1.03 | N'Keal Harry | TE | WR |
| 2019 | 2.08 | Hakeem Butler | TE | WR |
| 2020 | 3.08 | Antonio Gandy-Golden | TE | WR |

## Scored position counts

QB 38, RB 129, WR 168, TE 42

## Manager results

| Rank | Manager | Picks | Draft-Adjusted PPG | Avg Career PPG | R1 | R2 | R3 | R4+ |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | Tim Bell | 5 | +1.81 | 6.90 | +7.85 | +2.50 | +1.96 | -1.62 |
| 2 | Travis Page | 23 | +0.98 | 7.35 | +3.57 | -0.61 | -1.58 | +1.43 |
| 3 | Bo Tiller | 25 | +0.91 | 6.67 | +3.09 | -2.83 | +1.34 | +0.22 |
| 4 | Alex Agueros | 31 | +0.45 | 6.83 | -0.35 | +1.20 | +0.02 | +0.77 |
| 5 | Jordan Martin | 24 | +0.36 | 7.07 | +1.59 | -0.22 | +0.81 | -0.66 |
| 6 | Seth Miller | 48 | +0.27 | 6.65 | +1.45 | +0.25 | +3.23 | -1.79 |
| 7 | Luke Miller | 28 | +0.06 | 5.37 | -1.48 | -1.92 | +0.42 | +1.14 |
| 8 | Matt Metz | 37 | -0.15 | 5.50 | +0.83 | +1.01 | -0.13 | -1.55 |
| 9 | Mason Good | 23 | -0.52 | 5.05 | -6.65 | +2.72 | -1.07 | -0.69 |
| 10 | Kevin Long | 5 | -0.54 | 3.90 | — | -4.87 | -2.16 | +1.45 |
| 11 | Ryan Lipkin | 14 | -0.62 | 4.88 | +3.53 | -0.50 | +0.24 | -2.61 |
| 12 | Payton Docheff | 30 | -0.83 | 5.90 | +0.78 | +0.02 | -3.55 | -0.55 |
| 13 | Matt Clawson | 39 | -1.01 | 4.76 | -0.85 | -1.54 | -1.64 | -0.46 |
| 14 | David Carnes | 25 | -1.05 | 5.01 | -1.68 | -0.61 | -1.76 | -0.25 |
| 15 | Josh Ponath | 3 | -1.59 | 9.15 | -0.07 | — | -4.61 | — |
| 16 | Clint Hudson | 8 | -1.66 | 5.51 | +1.76 | -2.89 | -1.88 | -3.14 |
| 17 | Matthew Piontek | 9 | -1.86 | 4.85 | +0.67 | -1.41 | -3.59 | -5.44 |

## Extreme sanity check

- Highest: **Puka Nacua** 2023 6.02 = +12.97
- Lowest: **Jalen Milroe** 2025 4.04 = -11.08

## Production artifact

`draft-adjusted-ppg.js` is generated only from this final audited ledger. The production site consumes the frozen per-pick results directly.
