# POS ADJ PPG validation report

Generated: `2026-09-02T19:15:50+00:00`

## Locked definition

`POS ADJ PPG = career-to-date Dynasty Plebs PPG - expected PPG(position, exact rookie draft slot)`

No career-age adjustment is applied. No Dynasty Plebs manager or result data is used to fit the expectation curve.

## Source / identity audit

- FFC source rows (QB/RB/WR/TE): **346**
- Resolved rows with an NFL regular-season outcome: **334**
- Historical rows removed because the player had already played before the listed ADP year: **3**
- Unresolved or zero-game rows (not fitted): **9**
- Match/outcome rate for source rows with ADP <= 96: **96.5%**
- Core fitted sample (2014-2022, >= 5 human mock selections, ADP <= 96): **315**
- Core position counts: QB 38, RB 114, WR 136, TE 27
- Exact Plebs scoring calibration: **25/25 passed**

The non-rookie filter is intentional: archived source anomalies such as a prior-year NFL player appearing on a later rookie board cannot leak into the expectation sample.

## Leave-one-draft-class-out model validation

Bandwidth is selected independently by position against the final monotone, support-aware curve. Selection minimizes observation-weighted leave-one-draft-class-out MAE; candidates within 1% favor the smoother base bandwidth. Deep slots widen automatically until effective historical support reaches 12 players.

| Pos | N | Selected bandwidth | Exact-slot support-aware MAE | Pos+round MAE | Pos-only MAE |
|---|---:|---:|---:|---:|---:|
| QB | 38 | 8.0 | 5.405 | 5.254 | 5.480 |
| RB | 114 | 5.0 | 3.028 | 3.114 | 3.602 |
| WR | 136 | 5.0 | 3.049 | 2.988 | 3.384 |
| TE | 27 | 10.0 | 1.676 | 1.665 | 1.991 |

### Bandwidth grid

**QB**

| Bandwidth | Observation-weighted LOSO MAE | SE |
|---:|---:|---:|
| 3.0 | 5.355 | 0.779 |
| 4.0 | 5.373 | 0.778 |
| 5.0 | 5.379 | 0.776 |
| 6.0 | 5.400 | 0.774 |
| 8.0 **selected** | 5.405 | 0.776 |
| 10.0 | 5.413 | 0.772 |
| 12.0 | 5.421 | 0.768 |
| 16.0 | 5.428 | 0.763 |
| 20.0 | 5.445 | 0.756 |

**RB**

| Bandwidth | Observation-weighted LOSO MAE | SE |
|---:|---:|---:|
| 3.0 | 3.003 | 0.128 |
| 4.0 | 3.017 | 0.132 |
| 5.0 **selected** | 3.028 | 0.139 |
| 6.0 | 3.039 | 0.147 |
| 8.0 | 3.060 | 0.163 |
| 10.0 | 3.095 | 0.177 |
| 12.0 | 3.143 | 0.190 |
| 16.0 | 3.260 | 0.203 |
| 20.0 | 3.349 | 0.209 |

**WR**

| Bandwidth | Observation-weighted LOSO MAE | SE |
|---:|---:|---:|
| 3.0 | 3.025 | 0.228 |
| 4.0 | 3.037 | 0.230 |
| 5.0 **selected** | 3.049 | 0.233 |
| 6.0 | 3.061 | 0.235 |
| 8.0 | 3.092 | 0.236 |
| 10.0 | 3.129 | 0.234 |
| 12.0 | 3.169 | 0.231 |
| 16.0 | 3.236 | 0.227 |
| 20.0 | 3.279 | 0.225 |

**TE**

| Bandwidth | Observation-weighted LOSO MAE | SE |
|---:|---:|---:|
| 3.0 | 1.695 | 0.214 |
| 4.0 | 1.695 | 0.214 |
| 5.0 | 1.694 | 0.210 |
| 6.0 | 1.694 | 0.197 |
| 8.0 | 1.675 | 0.176 |
| 10.0 **selected** | 1.676 | 0.175 |
| 12.0 | 1.702 | 0.184 |
| 16.0 | 1.802 | 0.200 |
| 20.0 | 1.860 | 0.216 |

## Fitted curve anchors

Expected career PPG at exact overall rookie slots; `n_eff` is the kernel's effective local sample support.

**QB**

| Slot | Expected PPG | n_eff |
|---:|---:|---:|
| 1 | 14.16 | 13.8 |
| 6 | 14.06 | 19.7 |
| 12 | 14.02 | 27.4 |
| 18 | 13.76 | 32.1 |
| 24 | 13.05 | 30.0 |
| 36 | 10.95 | 16.8 |
| 48 | 10.55 | 17.6 |
| 60 | 10.55 | 17.7 |
| 72 | 10.15 | 13.2 |

**RB**

| Slot | Expected PPG | n_eff |
|---:|---:|---:|
| 1 | 10.91 | 36.8 |
| 6 | 9.63 | 50.3 |
| 12 | 7.72 | 54.0 |
| 18 | 6.17 | 51.6 |
| 24 | 5.04 | 56.0 |
| 36 | 3.85 | 28.5 |
| 48 | 3.42 | 13.6 |
| 60 | 3.42 | 21.6 |
| 72 | 3.23 | 13.0 |

**WR**

| Slot | Expected PPG | n_eff |
|---:|---:|---:|
| 1 | 8.45 | 35.9 |
| 6 | 8.04 | 56.0 |
| 12 | 6.95 | 71.4 |
| 18 | 5.88 | 69.2 |
| 24 | 5.22 | 71.4 |
| 36 | 4.03 | 37.2 |
| 48 | 3.48 | 16.8 |
| 60 | 3.47 | 14.3 |
| 72 | 3.45 | 16.3 |

**TE**

| Slot | Expected PPG | n_eff |
|---:|---:|---:|
| 1 | 6.48 | 15.3 |
| 6 | 6.40 | 15.0 |
| 12 | 6.00 | 19.8 |
| 18 | 5.44 | 24.1 |
| 24 | 4.80 | 24.5 |
| 36 | 3.83 | 16.7 |
| 48 | 3.50 | 12.2 |
| 60 | 3.50 | 12.2 |
| 72 | 3.46 | 13.0 |

## Sensitivity

Mean absolute change in the fitted expectation curve over slots 1-48 versus the core specification.

| Test | Status | QB | RB | WR | TE |
|---|---|---:|---:|---:|---:|
| min_mock_selections_3 | ok | 0.4646 | 0.352 | 0.1272 | 0.046 |
| min_mock_selections_10 | ok | 1.2522 | 0.2012 | 0.2098 | 0.6159 |
| drop_2022_class | ok | 1.1267 | 0.1674 | 0.0758 | 0.1201 |

## Production gate

This report does **not** deploy the metric. Before production, audit the unresolved/non-rookie lists, inspect curve stability/support, and test every historical Plebs pick against the frozen table. Production should consume the committed table rather than refit in the browser.

### V4 identity + support audit

Nyheim Hines is explicitly bridged to Sleeper's later `Nyheim Miller-Hines` identity. Every published position/slot expectation from 1 through 72 must retain `n_eff >= 12`.

| Pos | Slot 48 n_eff / bw | Slot 60 n_eff / bw | Slot 72 n_eff / bw |
|---|---:|---:|---:|
| QB | 17.6 / 12.5 | 17.7 / 15.6 | 13.2 / 15.6 |
| RB | 13.6 / 6.2 | 21.6 / 9.8 | 13.0 / 9.8 |
| WR | 16.8 / 5.0 | 14.3 / 6.2 | 16.3 / 7.8 |
| TE | 12.2 / 10.0 | 12.2 / 12.5 | 13.0 / 15.6 |
