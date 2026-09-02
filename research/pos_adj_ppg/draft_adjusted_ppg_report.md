# Dynasty Plebs Draft-Adjusted PPG final audit

## Locked public definition

**Career PPG minus the expected Career PPG for a rookie at the same position and draft slot.**

## Completed-class outcome rule

Every true rookie selection from 2019-2025 is graded. A rookie who generated no usable NFL fantasy production is a **0.0 Career PPG** outcome, including players who never appeared in an NFL regular-season game.

## Final integrity gates

- Frozen curve: `pos-adj-ppg-v4-research`
- True rookie outcomes through 2025: **390 / 390**
- Missing-production rookie picks converted to 0.0: **13**
- Completed-class rookies still omitted: **0**
- Veteran selections excluded through 2025: **7**
- Future/current-class rookies outside outcome window: **58**
- Seth true rookie outcomes through 2025: **48**
- Frank Gore Jr.: **0.0 Career PPG and included**.
- Manual audited rookie-position fallbacks: **7**
- Compensatory-pick sequencing: **passed**.
- Career-age adjustment: **none**.
- Plebs manager/results data used to train expectation: **none**.

### Zero-production outcomes restored to the denominator

| Year | Pick | Manager | Player | Pos | Career PPG | Draft-Adjusted PPG |
|---:|---:|---|---|---|---:|---:|
| 2019 | 3.10 | David Carnes | Jalen Hurd | WR | 0.0 | -4.17 |
| 2019 | 4.04 | David Carnes | Bryce Love | RB | 0.0 | -3.45 |
| 2019 | 4.06 | Matt Clawson | James Williams | RB | 0.0 | -3.42 |
| 2019 | 4.07 | Matt Metz | Rodney Anderson | RB | 0.0 | -3.42 |
| 2021 | 4.02 | Alex Agueros | Javian Hawkins | RB | 0.0 | -3.65 |
| 2021 | 4.10 | Matthew Piontek | Tamorrion Terry | WR | 0.0 | -3.53 |
| 2023 | 4.07 | Luke Miller | DeWayne McBride | RB | 0.0 | -3.42 |
| 2023 | 5.06 | Payton Docheff | Zach Kuntz | TE | 0.0 | -3.50 |
| 2023 | 5.12 | Bo Tiller | Stetson Bennett | QB | 0.0 | -10.55 |
| 2024 | 6.04 | Ryan Lipkin | Jordan Travis | QB | 0.0 | -10.55 |
| 2024 | 6.12 | Jordan Martin | Cornelius Johnson | WR | 0.0 | -3.45 |
| 2025 | 4.09 | Matt Metz | Damien Martinez | RB | 0.0 | -3.42 |
| 2025 | 5.04 | Luke Miller | Will Howard | QB | 0.0 | -10.55 |

## Graded position counts

QB 41, RB 135, WR 171, TE 43

## Manager results

| Rank | Manager | Rookie Picks | Draft-Adjusted PPG | Avg Career PPG | R1 | R2 | R3 | R4+ |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | Tim Bell | 5 | +1.81 | 6.90 | +7.85 | +2.50 | +1.96 | -1.62 |
| 2 | Travis Page | 23 | +0.98 | 7.35 | +3.57 | -0.61 | -1.58 | +1.43 |
| 3 | Bo Tiller | 26 | +0.47 | 6.42 | +3.09 | -2.83 | +1.34 | -0.76 |
| 4 | Alex Agueros | 32 | +0.32 | 6.62 | -0.35 | +1.20 | +0.02 | +0.28 |
| 5 | Seth Miller | 48 | +0.27 | 6.65 | +1.45 | +0.25 | +3.23 | -1.79 |
| 6 | Jordan Martin | 25 | +0.21 | 6.79 | +1.59 | -0.22 | +0.81 | -1.06 |
| 7 | Matt Metz | 39 | -0.32 | 5.21 | +0.83 | +1.01 | -0.13 | -1.80 |
| 8 | Luke Miller | 30 | -0.41 | 5.01 | -1.48 | -1.92 | +0.42 | -0.02 |
| 9 | Mason Good | 23 | -0.52 | 5.05 | -6.65 | +2.72 | -1.07 | -0.69 |
| 10 | Kevin Long | 5 | -0.54 | 3.90 | — | -4.87 | -2.16 | +1.45 |
| 11 | Payton Docheff | 31 | -0.92 | 5.71 | +0.78 | +0.02 | -3.55 | -0.84 |
| 12 | Matt Clawson | 40 | -1.07 | 4.64 | -0.85 | -1.54 | -1.64 | -0.64 |
| 13 | David Carnes | 27 | -1.25 | 4.64 | -1.68 | -0.61 | -2.24 | -1.05 |
| 14 | Ryan Lipkin | 15 | -1.28 | 4.55 | +3.53 | -0.50 | +0.24 | -3.74 |
| 15 | Josh Ponath | 3 | -1.59 | 9.15 | -0.07 | — | -4.61 | — |
| 16 | Clint Hudson | 8 | -1.66 | 5.51 | +1.76 | -2.89 | -1.88 | -3.14 |
| 17 | Matthew Piontek | 10 | -2.03 | 4.36 | +0.67 | -1.41 | -3.59 | -4.80 |

## Seth regression anchor

- Draft-Adjusted PPG: **+0.27** across **48** true rookie picks.
- Round 1: **+1.45**; Round 2: **+0.25**; Round 3: **+3.23**; Round 4+: **-1.79**.

## Extreme sanity check

- Highest: **Puka Nacua** 2023 6.02 = +12.97
- Lowest: **Jalen Milroe** 2025 4.04 = -11.08

## Production artifact

`draft-adjusted-ppg.js` is generated only from this final audited ledger. The production site consumes the frozen per-pick results directly.
