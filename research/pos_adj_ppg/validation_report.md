# POS ADJ PPG validation report

Generated: `2026-09-02T18:34:35+00:00`

## Locked definition

`POS ADJ PPG = career-to-date Dynasty Plebs PPG - expected PPG(position, exact rookie draft slot)`

No career-age adjustment is applied. No Dynasty Plebs manager or result data is used to fit the expectation curve.

## Source / identity audit

- FFC source rows (QB/RB/WR/TE): **346**
- Resolved rows with an NFL regular-season outcome: **329**
- Historical rows removed because the player had already played before the listed ADP year: **3**
- Unresolved or zero-game rows (not fitted): **14**
- Match/outcome rate for source rows with ADP <= 96: **95.1%**
- Core fitted sample (2014-2022, >= 5 human mock selections, ADP <= 96): **310**
- Core position counts: QB 38, RB 112, WR 133, TE 27
- Exact Plebs scoring calibration: **25/25 passed**

The non-rookie filter is intentional: archived source anomalies such as a prior-year NFL player appearing on a later rookie board cannot leak into the expectation sample.

## Leave-one-draft-class-out model validation

Bandwidth is selected independently by position. The one-standard-error rule chooses the smoothest bandwidth whose error is statistically tied with the minimum-error candidate.

| Pos | N | Selected bandwidth | Exact-slot kernel MAE | Pos+round MAE | Pos-only MAE |
|---|---:|---:|---:|---:|---:|
| QB | 38 | 20.0 | 5.445 | 5.254 | 5.480 |
| RB | 112 | 12.0 | 3.161 | 3.117 | 3.642 |
| WR | 133 | 16.0 | 3.225 | 2.975 | 3.373 |
| TE | 27 | 20.0 | 1.860 | 1.665 | 1.991 |

### Bandwidth grid

**QB**

| Bandwidth | Mean held-out-year MAE | SE |
|---:|---:|---:|
| 3.0 | 5.302 | 0.744 |
| 4.0 | 5.244 | 0.769 |
| 5.0 | 5.225 | 0.770 |
| 6.0 | 5.207 | 0.774 |
| 8.0 | 5.185 | 0.781 |
| 10.0 | 5.194 | 0.774 |
| 12.0 | 5.207 | 0.769 |
| 16.0 | 5.227 | 0.763 |
| 20.0 **selected** | 5.250 | 0.756 |

**RB**

| Bandwidth | Mean held-out-year MAE | SE |
|---:|---:|---:|
| 3.0 | 3.030 | 0.133 |
| 4.0 | 3.041 | 0.135 |
| 5.0 | 3.050 | 0.139 |
| 6.0 | 3.057 | 0.146 |
| 8.0 | 3.078 | 0.160 |
| 10.0 | 3.113 | 0.174 |
| 12.0 **selected** | 3.163 | 0.186 |
| 16.0 | 3.283 | 0.199 |
| 20.0 | 3.377 | 0.204 |

**WR**

| Bandwidth | Mean held-out-year MAE | SE |
|---:|---:|---:|
| 3.0 | 2.954 | 0.225 |
| 4.0 | 2.965 | 0.226 |
| 5.0 | 2.974 | 0.229 |
| 6.0 | 2.983 | 0.231 |
| 8.0 | 3.008 | 0.232 |
| 10.0 | 3.045 | 0.231 |
| 12.0 | 3.085 | 0.228 |
| 16.0 **selected** | 3.153 | 0.223 |
| 20.0 | 3.196 | 0.221 |

**TE**

| Bandwidth | Mean held-out-year MAE | SE |
|---:|---:|---:|
| 3.0 | 1.967 | 0.238 |
| 4.0 | 1.878 | 0.230 |
| 5.0 | 1.814 | 0.216 |
| 6.0 | 1.772 | 0.198 |
| 8.0 | 1.721 | 0.175 |
| 10.0 | 1.696 | 0.174 |
| 12.0 | 1.705 | 0.184 |
| 16.0 | 1.765 | 0.200 |
| 20.0 **selected** | 1.801 | 0.216 |

## Fitted curve anchors

Expected career PPG at exact overall rookie slots; `n_eff` is the kernel's effective local sample support.

**QB**

| Slot | Expected PPG | n_eff |
|---:|---:|---:|
| 1 | 13.65 | 34.0 |
| 6 | 13.55 | 35.7 |
| 12 | 13.40 | 37.2 |
| 18 | 13.25 | 37.7 |
| 24 | 13.07 | 37.4 |
| 36 | 12.68 | 34.4 |
| 48 | 12.24 | 29.8 |
| 60 | 11.77 | 25.0 |
| 72 | 11.29 | 20.7 |

**RB**

| Slot | Expected PPG | n_eff |
|---:|---:|---:|
| 1 | 9.18 | 69.8 |
| 6 | 8.52 | 83.5 |
| 12 | 7.61 | 99.0 |
| 18 | 6.69 | 103.4 |
| 24 | 5.88 | 93.0 |
| 36 | 4.82 | 62.9 |
| 48 | 4.28 | 44.0 |
| 60 | 3.94 | 32.1 |
| 72 | 3.66 | 23.3 |

**WR**

| Slot | Expected PPG | n_eff |
|---:|---:|---:|
| 1 | 6.99 | 103.7 |
| 6 | 6.74 | 115.0 |
| 12 | 6.43 | 125.8 |
| 18 | 6.11 | 130.2 |
| 24 | 5.80 | 126.3 |
| 36 | 5.25 | 102.1 |
| 48 | 4.83 | 77.4 |
| 60 | 4.54 | 60.9 |
| 72 | 4.33 | 50.5 |

**TE**

| Slot | Expected PPG | n_eff |
|---:|---:|---:|
| 1 | 5.70 | 23.3 |
| 6 | 5.55 | 24.8 |
| 12 | 5.36 | 26.1 |
| 18 | 5.17 | 26.8 |
| 24 | 4.98 | 26.7 |
| 36 | 4.62 | 24.7 |
| 48 | 4.30 | 21.7 |
| 60 | 4.03 | 18.9 |
| 72 | 3.81 | 16.5 |

## Sensitivity

Mean absolute change in the fitted expectation curve over slots 1-48 versus the core specification.

| Test | Status | QB | RB | WR | TE |
|---|---|---:|---:|---:|---:|
| min_mock_selections_3 | ok | 0.2655 | 0.142 | 0.0107 | 0.0667 |
| min_mock_selections_10 | ok | 0.7892 | 0.6687 | 0.2615 | 0.4577 |
| drop_2022_class | ok | 0.9273 | 0.0493 | 0.1498 | 0.0072 |

## Production gate

This report does **not** deploy the metric. Before production, audit the unresolved/non-rookie lists, inspect curve stability/support, and test every historical Plebs pick against the frozen table. Production should consume the committed table rather than refit in the browser.
