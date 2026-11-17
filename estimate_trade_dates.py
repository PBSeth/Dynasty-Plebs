"""Estimate missing workbook dates from its oldest-to-newest row order."""

import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).parent
CENTRAL = ZoneInfo("America/Chicago")


def ordered_anchors(records):
    """Keep the longest date-consistent chain; prefer earlier dates on ties.

    ESPN execution dates are preserved even when a delayed processing date
    cannot serve as an anchor for the workbook's chronological row order.
    """
    candidates = [t for t in records if t.get("acceptedAt") and not t.get("dateEstimate")]
    paths = []
    key = lambda path: (len(path), -sum(date.fromisoformat(t["date"]).toordinal() for t in path))
    for i, trade in enumerate(candidates):
        compatible = [paths[j] for j in range(i) if candidates[j]["date"] <= trade["date"]]
        paths.append(max(compatible, key=key, default=[]) + [trade])
    return max(paths, key=key, default=[])


def estimate_history(history):
    records = sorted((t for t in history["trades"] if t.get("row")), key=lambda t: t["row"])
    anchors = ordered_anchors(records)
    if not anchors:
        raise ValueError("At least one observed workbook date is required")
    anchor_ids = {t["id"] for t in anchors}
    excluded = [t for t in records if t.get("acceptedAt") and not t.get("dateEstimate") and t["id"] not in anchor_ids]
    windows = {}
    # A traded unspent pick predates the first documented roster appearance
    # of its selected player. Tighten windows without inserting player value.
    for trade in records:
        if trade.get("acceptedAt") and not trade.get("dateEstimate"):
            continue
        left = next((a for a in reversed(anchors) if a["row"] < trade["row"]), None)
        right = next((a for a in anchors if a["row"] > trade["row"]), None)
        lower = left["date"] if left else None
        upper = right["date"] if right else None
        selection_dates = [datetime.fromtimestamp(a["afterDraft"] / 1000, CENTRAL).date().isoformat()
                           for s in trade["sides"] for a in s["assets"]
                           if a["kind"] == "pick" and a.get("afterDraft")]
        selection_dates = [d for d in selection_dates if (not lower or d >= lower) and (not upper or d < upper)]
        if selection_dates:
            upper = min(selection_dates)
        windows[trade["row"]] = {"left": left, "right": right, "lower": lower, "upper": upper, "selectionBounds": selection_dates}
    # Later rows also bound earlier undated rows in the same anchor interval.
    for row in sorted(windows, reverse=True):
        window = windows[row]
        following = next((windows[r] for r in sorted(windows) if r > row), None)
        if following and window["right"] is following["right"] and following["upper"]:
            if not window["upper"] or following["upper"] < window["upper"]:
                window["upper"] = following["upper"]
                window["selectionBounds"] += following["selectionBounds"]
    for trade in records:
        if trade.get("acceptedAt") and not trade.get("dateEstimate"):
            continue
        window = windows[trade["row"]]
        left, right = window["left"], window["right"]
        lower = date.fromisoformat(window["lower"]) if window["lower"] else None
        upper = date.fromisoformat(window["upper"]) if window["upper"] else None
        if left and right:
            fraction = (trade["row"] - left["row"]) / (right["row"] - left["row"])
            estimate = lower + timedelta(days=int((upper - lower).days * fraction + 0.5))
            method = "Linear interpolation by workbook row between surrounding date-consistent ESPN executions."
        elif right:
            estimate = upper - timedelta(days=right["row"] - trade["row"])
            method = "One-sided estimate: one day per workbook row before the first observed execution; no earlier date bound is known."
        else:
            estimate = lower + timedelta(days=trade["row"] - left["row"])
            method = "One-sided estimate: one day per workbook row after the last observed execution; no later date bound is known."
        span = (upper - lower).days if lower and upper else None
        nearby = [t["row"] for t in excluded if (not left or left["row"] < t["row"]) and (not right or t["row"] < right["row"])]
        trade["dateEstimate"] = {
            "earliest": lower.isoformat() if lower else None,
            "latest": upper.isoformat() if upper else None,
            "anchorRows": [a["row"] for a in (left, right) if a],
            "windowDays": span,
            "precision": "one-sided" if span is None else "within a week" if span <= 7 else "within a month" if span <= 31 else "broad window",
            "method": method,
            "pickSelectionUpperBounds": sorted(set(window["selectionBounds"])),
            "excludedProcessingDateRows": nearby,
        }
        trade["date"] = estimate.isoformat()
        # This is a modeled timestamp, not an ESPN acceptedAt execution.
        trade["estimatedAt"] = int(datetime.combine(estimate, time(12), CENTRAL).timestamp() * 1000)
        trade.pop("acceptedAt", None)
        trade["season"] = estimate.year
        trade["dateSource"] = "Estimated from workbook order, using " + " and ".join(f"row {a['row']} ({a['date']})" for a in (left, right) if a)
        trade["issues"] = [s for s in trade.get("issues", []) if not s.startswith("Exact execution date is not present")]
    coverage = history["coverage"]
    coverage["workbookRowsEstimated"] = sum(bool(t.get("dateEstimate")) for t in records)
    coverage["undatedWorkbookRows"] = sum(not t.get("date") for t in records)
    coverage["estimateAnchorRows"] = [a["row"] for a in anchors]
    coverage["outOfSequenceExecutionRows"] = [t["row"] for t in excluded]
    coverage["limitations"] = [s for s in coverage["limitations"] if not s.startswith("ESPN does not record the spreadsheet-only")]
    note = "Missing workbook dates are estimates from row order. Their surrounding date windows are not confidence intervals. Observed out-of-sequence ESPN execution dates are retained but omitted as estimation anchors."
    if note not in coverage["limitations"]:
        coverage["limitations"].append(note)
    return history


if __name__ == "__main__":
    path = ROOT / "trade-history.json"
    history = estimate_history(json.loads(path.read_text()))
    path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n")
    print(f"{history['coverage']['workbookRowsEstimated']} estimated workbook dates; {history['coverage']['undatedWorkbookRows']} missing")
