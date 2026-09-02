# POS ADJ PPG validation report

Generated: `2026-09-02T18:37:42+00:00`

## Locked definition

`POS ADJ PPG = career-to-date Dynasty Plebs PPG - expected PPG(position, exact rookie draft slot)`

No career-age adjustment is applied. No Dynasty Plebs manager or result data is used to fit the expectation curve.

## Source / identity audit

- FFC source rows (QB/RB/WR/TE): **346**
- Resolved rows with an NFL regular-season outcome: **332**
- Historical rows removed because the player had already played before the listed ADP year: **3**
- Unresolved or zero-game rows (not fitted): **11**
- Match/outcome rate for source rows with ADP <= 96: **96.0%**
- Core fitted sample (2014-2022, >= 5 human mock selections, ADP <= 96): **313**
- Core position counts: QB 38, RB 113, WR 135, TE 27
- Exact Plebs scoring calibration: **25/25 passed**

The non-rookie filter is intentional: archived source anomalies such as a prior-year NFL player appearing on a later rookie board cannot leak into the expectation sample.

## Leave-one-draft-class-out model validation

Bandwidth is selected independently by position against the final monotone curve. Selection minimizes observation-weighted leave-one-draft-class-out MAE; when candidates are within 1% of the minimum, the smoother bandwidth wins.

| Pos | N | Selected bandwidth | Exact-slot monotone MAE | Pos+round MAE | Pos-only MAE |
|---|---:|---:|---:|---:|---:|
| QB | 38 | 16.0 | 5.428 | 5.254 | 5.480 |
| RB | 113 | 6.0 | 3.049 | 3.124 | 3.612 |
| WR | 135 | 5.0 | 3.053 | 3.003 | 3.379 |
| TE | 27 | 10.0 | 1.670 | 1.665 | 1.991 |

### Bandwidth grid

**QB**

| Bandwidth | Observation-weighted LOSO MAE | SE |
|---:|---:|---:|
| 3.0 | 5.436 | 0.759 |
| 4.0 | 5.397 | 0.766 |
| 5.0 | 5.385 | 0.769 |
| 6.0 | 5.397 | 0.771 |
| 8.0 | 5.403 | 0.776 |
| 10.0 | 5.413 | 0.772 |
| 12.0 | 5.421 | 0.768 |
| 16.0 **selected** | 5.428 | 0.763 |
| 20.0 | 5.445 | 0.756 |

**RB**

| Bandwidth | Observation-weighted LOSO MAE | SE |
|---:|---:|---:|
| 3.0 | 3.024 | 0.132 |
| 4.0 | 3.033 | 0.135 |
| 5.0 | 3.039 | 0.140 |
| 6.0 **selected** | 3.049 | 0.147 |
| 8.0 | 3.069 | 0.162 |
| 10.0 | 3.102 | 0.175 |
| 12.0 | 3.150 | 0.188 |
| 16.0 | 3.265 | 0.201 |
| 20.0 | 3.355 | 0.207 |

**WR**

| Bandwidth | Observation-weighted LOSO MAE | SE |
|---:|---:|---:|
| 3.0 | 3.032 | 0.229 |
| 4.0 | 3.042 | 0.231 |
| 5.0 **selected** | 3.053 | 0.234 |
| 6.0 | 3.066 | 0.236 |
| 8.0 | 3.097 | 0.236 |
| 10.0 | 3.133 | 0.234 |
| 12.0 | 3.171 | 0.231 |
| 16.0 | 3.236 | 0.227 |
| 20.0 | 3.277 | 0.224 |

**TE**

| Bandwidth | Observation-weighted LOSO MAE | SE |
|---:|---:|---:|
| 3.0 | 1.810 | 0.242 |
| 4.0 | 1.750 | 0.231 |
| 5.0 | 1.702 | 0.216 |
| 6.0 | 1.678 | 0.198 |
| 8.0 | 1.664 | 0.175 |
| 10.0 **selected** | 1.670 | 0.174 |
| 12.0 | 1.702 | 0.184 |
| 16.0 | 1.802 | 0.200 |
| 20.0 | 1.860 | 0.216 |

## Fitted curve anchors

Expected career PPG at exact overall rookie slots; `n_eff` is the kernel's effective local sample support.

**QB**

| Slot | Expected PPG | n_eff |
|---:|---:|---:|
| 1 | 13.84 | 30.2 |
| 6 | 13.71 | 33.4 |
| 12 | 13.53 | 36.2 |
| 18 | 13.31 | 37.3 |
| 24 | 13.06 | 36.6 |
| 36 | 12.45 | 31.2 |
| 48 | 11.75 | 24.4 |
| 60 | 11.02 | 18.4 |
| 72 | 10.28 | 13.8 |

**RB**

| Slot | Expected PPG | n_eff |
|---:|---:|---:|
| 1 | 10.60 | 41.5 |
| 6 | 9.52 | 55.0 |
| 12 | 7.86 | 63.4 |
| 18 | 6.26 | 63.2 |
| 24 | 5.11 | 62.4 |
| 36 | 4.03 | 34.2 |
| 48 | 3.14 | 12.0 |
| 60 | 2.39 | 3.7 |
| 72 | 1.94 | 1.8 |

**WR**

| Slot | Expected PPG | n_eff |
|---:|---:|---:|
| 1 | 8.43 | 35.3 |
| 6 | 7.99 | 55.0 |
| 12 | 6.89 | 70.4 |
| 18 | 5.86 | 68.6 |
| 24 | 5.21 | 71.3 |
| 36 | 4.03 | 37.2 |
| 48 | 3.45 | 16.8 |
| 60 | 3.03 | 6.2 |
| 72 | 2.60 | 1.0 |

**TE**

| Slot | Expected PPG | n_eff |
|---:|---:|---:|
| 1 | 6.62 | 11.5 |
| 6 | 6.40 | 15.0 |
| 12 | 6.00 | 19.8 |
| 18 | 5.44 | 24.1 |
| 24 | 4.80 | 24.5 |
| 36 | 3.83 | 16.7 |
| 48 | 3.38 | 12.2 |
| 60 | 3.15 | 10.1 |
| 72 | 3.00 | 8.8 |

## Sensitivity

Mean absolute change in the fitted expectation curve over slots 1-48 versus the core specification.

| Test | Status | QB | RB | WR | TE |
|---|---|---:|---:|---:|---:|
| min_mock_selections_3 | ok | 0.7413 | 0.2597 | 0.1271 | 0.0409 |
| min_mock_selections_10 | ok | 0.8605 | 0.4486 | 0.2099 | 0.338 |
| drop_2022_class | ok | 0.7625 | 0.1595 | 0.0779 | 0.063 |

## Production gate

This report does **not** deploy the metric. Before production, audit the unresolved/non-rookie lists, inspect curve stability/support, and test every historical Plebs pick against the frozen table. Production should consume the committed table rather than refit in the browser.

### V2 refinement

Identity resolution uses position and rookie-year context for same-name players. Final-model validation includes the monotonic constraint actually shipped in the frozen expectation table.
