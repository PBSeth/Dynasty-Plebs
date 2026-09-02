#!/usr/bin/env python3
"""Final identity-cleaned POS ADJ PPG research build.

V4 carries forward the support-aware V3 model and adds the historical Sleeper
rename Nyheim Hines -> Nyheim Miller-Hines. The player is a material 2018
second-round rookie observation and should not be silently lost to a later name
change.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import build_pos_adj_ppg_curve_v3 as model  # noqa: E402

base = model.base
base.ALIASES["nyheimhines"] = "nyheimmillerhines"

if __name__ == "__main__":
    base.main()

    report_path = HERE / "validation_report.md"
    report = report_path.read_text(encoding="utf-8")
    report = report.replace(
        "Bandwidth is selected independently by position. The one-standard-error rule chooses the smoothest bandwidth whose error is statistically tied with the minimum-error candidate.",
        "Bandwidth is selected independently by position against the final monotone, support-aware curve. Selection minimizes observation-weighted leave-one-draft-class-out MAE; candidates within 1% favor the smoother base bandwidth. Deep slots widen automatically until effective historical support reaches 12 players.",
    )
    report = report.replace("Exact-slot kernel MAE", "Exact-slot support-aware MAE")
    report = report.replace("Mean held-out-year MAE", "Observation-weighted LOSO MAE")

    curve_path = HERE / "pos_adj_ppg_curve.json"
    curve = json.loads(curve_path.read_text(encoding="utf-8"))
    report += "\n### V4 identity + support audit\n\nNyheim Hines is explicitly bridged to Sleeper's later `Nyheim Miller-Hines` identity. Every published position/slot expectation from 1 through 72 must retain `n_eff >= 12`.\n\n| Pos | Slot 48 n_eff / bw | Slot 60 n_eff / bw | Slot 72 n_eff / bw |\n|---|---:|---:|---:|\n"
    for pos in base.POSITIONS:
        cells = []
        for slot in (48, 60, 72):
            row = curve["curve"][pos][str(slot)]
            if row["effective_n"] < model.MIN_EFFECTIVE_N - 0.05:
                raise RuntimeError(f"support floor failed after artifact build for {pos} {slot}")
            cells.append(f"{row['effective_n']:.1f} / {row['bandwidth']:.1f}")
        report += f"| {pos} | {cells[0]} | {cells[1]} | {cells[2]} |\n"
    report_path.write_text(report, encoding="utf-8")

    curve["version"] = "pos-adj-ppg-v4-research"
    curve["model_selection"] = "LOSO final monotone adaptive-kernel MAE; 1% base-bandwidth tie band; >=12 effective local observations"
    curve["minimum_effective_n"] = model.MIN_EFFECTIVE_N
    curve["max_adaptive_bandwidth"] = model.MAX_ADAPTIVE_BANDWIDTH
    curve_path.write_text(json.dumps(curve, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest_path = HERE / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = "pos-adj-ppg-research-v4"
    manifest["identity_resolution"] = "normalized name + explicit historical variants/renames + position + rookie-year context; prior NFL debut removed as non-rookie"
    manifest["notable_identity_bridge"] = "Nyheim Hines -> Sleeper Nyheim Miller-Hines"
    manifest["model_selection"] = "LOSO final monotone adaptive kernel; >=12 effective local historical observations at every published slot"
    manifest["minimum_effective_n"] = model.MIN_EFFECTIVE_N
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
