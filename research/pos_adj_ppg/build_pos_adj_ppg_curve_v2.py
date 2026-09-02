#!/usr/bin/env python3
"""Refined POS ADJ PPG build.

V2 keeps the V1 source/scoring pipeline but improves two audit-critical pieces:
1) same-name historical identity resolution uses rookie year + position context;
2) bandwidth selection validates the *final monotone curve*, not the raw kernel.
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import build_pos_adj_ppg_curve as base  # noqa: E402

base.ALIASES.update(
    {
        "willfuller": "willfullerv",
        "leonteecaroo": "leontecarroo",
        "ronaldjones": "ronaldjonesii",
    }
)


def resolve_pid(name: str, pos: str, identity: dict, draft_year: int | None = None) -> str | None:
    n = base.norm_name(name)
    variants = {n, base.strip_suffix(n)}
    if n in base.ALIASES:
        variants.add(base.ALIASES[n])
        variants.add(base.strip_suffix(base.ALIASES[n]))
    for k, v in base.ALIASES.items():
        if v == n:
            variants.add(k)
            variants.add(base.strip_suffix(k))

    exact_candidates: set[str] = set()
    base_candidates: set[str] = set()
    for v in variants:
        exact_candidates.update(identity["exact"].get(v, set()))
        base_candidates.update(identity["base"].get(base.strip_suffix(v), set()))
    candidates = exact_candidates or base_candidates
    if not candidates:
        return None

    positional = {pid for pid in candidates if pos in identity["positions"].get(pid, set())}
    if positional:
        candidates = positional
    if len(candidates) == 1:
        return next(iter(candidates))

    if draft_year is not None:
        def score(pid: str) -> tuple[int, int, int, str]:
            first = identity["first_game_season"].get(pid)
            missing = 1 if first is None else 0
            distance = 999 if first is None else abs(first - draft_year)
            # If equally close, prefer a debut in/after the listed rookie year;
            # a prior-year debut remains selectable when it is the only plausible
            # identity so the explicit non-rookie audit can remove it later.
            prior = 1 if first is not None and first < draft_year else 0
            return (missing, distance, prior, pid)

        ranked = sorted(candidates, key=score)
        if len(ranked) == 1 or score(ranked[0])[:3] < score(ranked[1])[:3]:
            return ranked[0]
    return None


def resolve_adp_rows(adp_rows: list[dict], by_year_pid: dict[int, dict[str, dict]], identity: dict):
    resolved, unresolved, nonrookies = [], [], []
    for row in adp_rows:
        pid = resolve_pid(row["name"], row["position"], identity, row["year"])
        if not pid:
            unresolved.append(row)
            continue
        first = identity["first_game_season"].get(pid)
        if first is not None and first < row["year"]:
            nonrookies.append({**row, "sleeper_first_game_season": first})
            continue
        ppg, points, games = base.career_outcome(pid, row["year"], by_year_pid)
        if ppg is None:
            unresolved.append({**row, "reason": "no_regular_season_game_or_identity_outcome"})
            continue
        resolved.append(
            {
                **row,
                "sleeper_player_id": pid,
                "sleeper_first_game_season": first,
                "career_games": games,
                "career_points": round(points, 4),
                "career_ppg": round(ppg, 6),
            }
        )
    return resolved, unresolved, nonrookies


def fit_position_values(data: list[dict], bandwidth: float, max_slot: int = 96):
    raw, supports = [], []
    for slot in range(1, max_slot + 1):
        pred, neff = base.kernel_predict(data, float(slot), bandwidth)
        raw.append(pred)
        supports.append(neff)
    monotone = base.pava_decreasing(raw, supports)
    return monotone, raw, supports


def predict_from_grid(values: list[float], x: float) -> float:
    x = max(1.0, min(float(len(values)), x))
    lo = int(math.floor(x))
    hi = int(math.ceil(x))
    if lo == hi:
        return values[lo - 1]
    frac = x - lo
    return values[lo - 1] * (1.0 - frac) + values[hi - 1] * frac


def select_bandwidth(rows: list[dict], position: str):
    data = [r for r in rows if r["position"] == position]
    years = sorted({r["year"] for r in data})
    if len(years) < 5:
        raise RuntimeError(f"not enough draft classes to cross-validate {position}: {years}")
    results = []
    for bw in base.BANDWIDTHS:
        all_errors, year_maes = [], []
        for holdout in years:
            train = [r for r in data if r["year"] != holdout]
            test = [r for r in data if r["year"] == holdout]
            if not train or not test:
                continue
            values, _, _ = fit_position_values(train, bw, int(base.MAX_TRAINING_ADP))
            errors = [abs(r["career_ppg"] - predict_from_grid(values, r["adp"])) for r in test]
            all_errors.extend(errors)
            year_maes.append(statistics.mean(errors))
        obs_mae = statistics.mean(all_errors)
        year_se = statistics.stdev(year_maes) / math.sqrt(len(year_maes)) if len(year_maes) > 1 else 0.0
        results.append(
            {
                "bandwidth": bw,
                # V1's report renderer consumes this key; V2 intentionally puts
                # observation-weighted LOSO MAE here and relabels the report.
                "mean_year_mae": obs_mae,
                "se": year_se,
                "years": len(year_maes),
                "n": len(all_errors),
                "year_balanced_mae": statistics.mean(year_maes),
            }
        )
    best = min(results, key=lambda r: r["mean_year_mae"])
    # Monotonicity already supplies strong regularization. Use a tight 1% tie
    # band rather than the much broader one-SE rule, then prefer the smoother fit.
    threshold = best["mean_year_mae"] * 1.01
    eligible = [r for r in results if r["mean_year_mae"] <= threshold + 1e-12]
    selected = max(eligible, key=lambda r: r["bandwidth"])["bandwidth"]
    return float(selected), results


def fit_curve(rows: list[dict], selected_bw: dict[str, float]):
    out = {}
    for pos in base.POSITIONS:
        data = [r for r in rows if r["position"] == pos]
        values, raw, supports = fit_position_values(data, selected_bw[pos], base.MAX_CURVE_SLOT)
        if any(values[i] < values[i + 1] - 1e-9 for i in range(len(values) - 1)):
            raise RuntimeError(f"monotonicity failed for {pos}")
        out[pos] = {
            str(slot): {
                "expected_ppg": round(values[slot - 1], 4),
                "raw_smoothed_ppg": round(raw[slot - 1], 4),
                "effective_n": round(supports[slot - 1], 2),
            }
            for slot in range(1, base.MAX_CURVE_SLOT + 1)
        }
    return out


def cv_compare(rows: list[dict], selected_bw: dict[str, float]):
    metrics = {}
    for pos in base.POSITIONS:
        data = [r for r in rows if r["position"] == pos]
        years = sorted({r["year"] for r in data})
        exact_errors, round_errors, pos_errors = [], [], []
        for holdout in years:
            train = [r for r in data if r["year"] != holdout]
            test = [r for r in data if r["year"] == holdout]
            if not train or not test:
                continue
            values, _, _ = fit_position_values(train, selected_bw[pos], int(base.MAX_TRAINING_ADP))
            pos_mean = statistics.mean(r["career_ppg"] for r in train)
            by_round = defaultdict(list)
            for r in train:
                by_round[base.round_bucket(r["adp"])].append(r["career_ppg"])
            for r in test:
                epred = predict_from_grid(values, r["adp"])
                bucket_vals = by_round.get(base.round_bucket(r["adp"])) or [pos_mean]
                rpred = statistics.mean(bucket_vals)
                y = r["career_ppg"]
                exact_errors.append(abs(y - epred))
                round_errors.append(abs(y - rpred))
                pos_errors.append(abs(y - pos_mean))
        metrics[pos] = {
            "n": len(exact_errors),
            "kernel_slot_mae": round(statistics.mean(exact_errors), 4),
            "position_round_mae": round(statistics.mean(round_errors), 4),
            "position_only_mae": round(statistics.mean(pos_errors), 4),
        }
    return metrics


base.resolve_pid = resolve_pid
base.resolve_adp_rows = resolve_adp_rows
base.select_bandwidth = select_bandwidth
base.fit_curve = fit_curve
base.cv_compare = cv_compare


if __name__ == "__main__":
    base.main()

    report_path = HERE / "validation_report.md"
    report = report_path.read_text(encoding="utf-8")
    report = report.replace(
        "Bandwidth is selected independently by position. The one-standard-error rule chooses the smoothest bandwidth whose error is statistically tied with the minimum-error candidate.",
        "Bandwidth is selected independently by position against the final monotone curve. Selection minimizes observation-weighted leave-one-draft-class-out MAE; when candidates are within 1% of the minimum, the smoother bandwidth wins.",
    )
    report = report.replace("Exact-slot kernel MAE", "Exact-slot monotone MAE")
    report = report.replace("Mean held-out-year MAE", "Observation-weighted LOSO MAE")
    report += "\n### V2 refinement\n\nIdentity resolution uses position and rookie-year context for same-name players. Final-model validation includes the monotonic constraint actually shipped in the frozen expectation table.\n"
    report_path.write_text(report, encoding="utf-8")

    curve_path = HERE / "pos_adj_ppg_curve.json"
    curve = json.loads(curve_path.read_text(encoding="utf-8"))
    curve["version"] = "pos-adj-ppg-v2-research"
    curve["model_selection"] = "LOSO final-monotone MAE; smoother bandwidth wins only inside 1% tie band"
    curve_path.write_text(json.dumps(curve, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest_path = HERE / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = "pos-adj-ppg-research-v2"
    manifest["identity_resolution"] = "normalized name + position + rookie-year context; prior NFL debut explicitly removed as non-rookie"
    manifest["model_selection"] = "LOSO final-monotone MAE; 1% smoothness tie band"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
