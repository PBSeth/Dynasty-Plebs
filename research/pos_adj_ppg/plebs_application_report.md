# Dynasty Plebs Draft-Adjusted PPG application audit

Curve: `pos-adj-ppg-v4-research`

## Definition

**Draft-Adjusted PPG = Career PPG − expected Career PPG for a rookie at the same position and actual sequential draft slot.**

The expectation table is frozen before this script reads any Dynasty Plebs manager/result data. Managers only enter after the pick-level residual exists, for aggregation and display.

## Integrity gates

- Draft years present: **2019–2026**
- Every recovered draft round has a parallel owner row; rounds are allowed to exceed 12 picks when compensatory selections exist.
- Compensatory selections detected: **1** (each shifts every later overall draft slot in that year).
- Historical pick anchors passed: **6/6**.
- Known veteran selections excluded: **9**.
- Eligible scored rookie picks: **377**.
- Unscored rookie picks: **71** (includes future/zero-game players; they do not affect manager grades).
- 2026 rookie outcomes in through-2025 results: **0**.
- Pick-level residual arithmetic and manager mean re-aggregation: **passed**.

## Scored sample

Position counts: QB 38, RB 129, WR 165, TE 45

Display-round counts: R1 84, R2 84, R3 83, R4+ 126

## Manager results

| Rank | Manager | Picks | Draft-Adjusted PPG | Avg Career PPG | R1 | R2 | R3 | R4+ | Best | Worst |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| 1 | Tim Bell | 5 | +1.81 | 6.90 | +7.85 | +2.50 | +1.96 | -1.62 | Devon Achane 1.09 (+7.85) | Rakim Jarrett 6.09 (-2.23) |
| 2 | Travis Page | 23 | +1.00 | 7.35 | +3.57 | -0.51 | -1.58 | +1.43 | Puka Nacua 6.02 (+12.97) | Hakeem Butler 2.08 (-5.23) |
| 3 | Bo Tiller | 25 | +0.91 | 6.67 | +3.09 | -2.83 | +1.34 | +0.22 | Jaxson Dart 3.07 (+6.81) | Evan Hull 3.10 (-3.15) |
| 4 | Alex Agueros | 31 | +0.45 | 6.83 | -0.35 | +1.20 | +0.02 | +0.77 | Justin Herbert 4.06 (+10.61) | Ben Sinnott 2.11 (-3.87) |
| 5 | Jordan Martin | 24 | +0.36 | 7.07 | +1.59 | -0.22 | +0.81 | -0.66 | Ja'Marr Chase 1.03 (+7.90) | JJ Arcega-Whiteside 2.05 (-4.74) |
| 6 | Seth Miller | 48 | +0.27 | 6.65 | +1.45 | +0.25 | +3.23 | -1.79 | Bo Nix 3.12 (+9.15) | Jake Haener 6.12 (-8.50) |
| 7 | Luke Miller | 28 | +0.06 | 5.37 | -1.48 | -1.92 | +0.42 | +1.14 | Rhamondre Stevenson 3.01 (+6.11) | Jonathon Brooks 1.06 (-7.63) |
| 8 | Matt Metz | 37 | -0.10 | 5.50 | +1.04 | +1.01 | -0.13 | -1.55 | Amon-Ra St. Brown 2.04 (+8.22) | D'Wayne Eskridge 2.10 (-4.36) |
| 9 | Mason Good | 23 | -0.52 | 5.05 | -6.65 | +2.72 | -1.07 | -0.69 | Joe Burrow 2.10 (+8.92) | Clayton Tune 6.04 (-10.45) |
| 10 | Kevin Long | 5 | -0.54 | 3.90 | — | -4.87 | -2.16 | +1.45 | Darnell Mooney 4.04 (+3.60) | Andy Isabella 2.01 (-4.87) |
| 11 | Ryan Lipkin | 14 | -0.62 | 4.88 | +3.53 | -0.50 | +0.24 | -2.61 | Harold Fannin 3.12 (+5.57) | Jalen Milroe 4.04 (-11.08) |
| 12 | Payton Docheff | 30 | -0.83 | 5.90 | +0.78 | +0.02 | -3.55 | -0.55 | Rashee Rice 2.04 (+6.31) | Hendon Hooker 3.08 (-10.80) |
| 13 | Matt Clawson | 39 | -1.01 | 4.76 | -0.85 | -1.54 | -1.64 | -0.46 | Kyren Williams 4.07 (+10.49) | Kenny Pickett 2.10 (-5.19) |
| 14 | David Carnes | 25 | -1.05 | 5.01 | -1.68 | -0.61 | -1.76 | -0.25 | Brandon Aiyuk 2.04 (+4.66) | Kaleb Johnson 1.08 (-8.18) |
| 15 | Josh Ponath | 3 | -1.59 | 9.15 | -0.07 | — | -4.61 | — | Josh Jacobs 1.01 (+3.89) | Dwayne Haskins 3.01 (-4.61) |
| 16 | Clint Hudson | 8 | -1.66 | 5.51 | +1.76 | -2.89 | -1.88 | -3.14 | Brock Bowers 1.05 (+5.65) | Jalen Royals 2.09 (-5.34) |
| 17 | Matthew Piontek | 9 | -1.84 | 4.85 | +0.67 | -1.41 | -3.47 | -5.44 | DK Metcalf 1.06 (+3.43) | Kellen Mond 4.12 (-10.35) |

## Extreme pick sanity check

- Highest residual: **Puka Nacua**, Travis Page 2023 6.02: Career 16.45 − Expected 3.47 = **+12.97**.
- Lowest residual: **Jalen Milroe**, Ryan Lipkin 2025 4.04: Career -0.53 − Expected 10.55 = **-11.08**.

## Production rule

The website should consume the frozen curve and calculate the same pick residuals. It must not construct peer groups from current or historical Plebs managers. Round 4+ is a display bucket only; each pick retains its actual sequential overall-slot expectation, including compensatory-pick shifts.
