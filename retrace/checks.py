"""Validation helpers for saved ReTrace ledger reports."""

from __future__ import annotations

from typing import Any


REQUIRED_LEDGER_FIELDS = {
    "step",
    "complexity_before",
    "complexity_after",
    "defect",
    "accumulated_defect",
    "ledger",
}


def summarize_defects(rows: list[dict]) -> dict[str, int]:
    """Return defect totals grouped by ledger step name."""

    totals: dict[str, int] = {}
    for row in rows:
        step = row["step"]
        totals[step] = totals.get(step, 0) + row["defect"]
    return totals


def check_defect_conservation(rows: list[dict]) -> list[str]:
    """Return violations when row defects do not match final accumulation."""

    reasons: list[str] = []

    if not isinstance(rows, list):
        return ["malformed report: expected a list of ledger rows"]
    if not rows:
        return ["malformed report: empty ledger report"]

    required_fields = {"step", "defect", "accumulated_defect"}
    defect_total = 0
    can_check_total = True

    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            reasons.append(f"row {index} malformed report: expected object")
            can_check_total = False
            continue

        missing_fields = required_fields - set(row)
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            reasons.append(f"row {index} missing required field: {missing}")
            can_check_total = False
            continue

        defect = row["defect"]
        if not isinstance(defect, (int, float)) or isinstance(defect, bool):
            reasons.append(
                f"row {index} identity violated: values are not numeric"
            )
            can_check_total = False
            continue

        defect_total += defect

    if can_check_total and defect_total != rows[-1]["accumulated_defect"]:
        reasons.append(
            "ledger drift detected: summed defects != final accumulated_defect"
        )

    return reasons


def check_accum_monotone(rows: list[dict]) -> list[str]:
    """Return violations when accumulated defects decrease across rows."""

    reasons: list[str] = []

    if not isinstance(rows, list):
        return ["malformed report: expected a list of ledger rows"]
    if not rows:
        return ["malformed report: empty ledger report"]

    previous_accumulated = None
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            reasons.append(f"row {index} malformed report: expected object")
            previous_accumulated = None
            continue

        if "accumulated_defect" not in row:
            reasons.append(
                f"row {index} missing required field: accumulated_defect"
            )
            previous_accumulated = None
            continue

        accumulated_defect = row["accumulated_defect"]
        if not isinstance(accumulated_defect, (int, float)) or isinstance(
            accumulated_defect, bool
        ):
            reasons.append(
                f"row {index} identity violated: values are not numeric"
            )
            previous_accumulated = None
            continue

        if (
            previous_accumulated is not None
            and accumulated_defect < previous_accumulated
        ):
            reasons.append(
                f"row {index} ledger drift detected: "
                "accumulated_defect decreased"
            )

        previous_accumulated = accumulated_defect

    return reasons


def check_defect_tally(rows: list[dict]) -> list[str]:
    """Return violations when running defects do not match accumulation."""

    reasons: list[str] = []

    if not isinstance(rows, list):
        return ["malformed report: expected a list of ledger rows"]
    if not rows:
        return ["malformed report: empty ledger report"]

    running_defect = 0
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            reasons.append(f"row {index} malformed report: expected object")
            continue

        missing_fields = {"defect", "accumulated_defect"} - set(row)
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            reasons.append(f"row {index} missing required field: {missing}")
            continue

        defect = row["defect"]
        accumulated_defect = row["accumulated_defect"]
        if (
            not isinstance(defect, (int, float))
            or isinstance(defect, bool)
            or not isinstance(accumulated_defect, (int, float))
            or isinstance(accumulated_defect, bool)
        ):
            reasons.append(
                f"row {index} identity violated: values are not numeric"
            )
            continue

        running_defect += defect
        if running_defect != accumulated_defect:
            reasons.append(
                f"row {index} ledger drift detected: "
                "running defect total != accumulated_defect"
            )

    return reasons


def check_row_sequence(rows: list[dict]) -> list[str]:
    """Return violations when ledger row order is not readable."""

    reasons: list[str] = []

    if not isinstance(rows, list):
        return ["malformed report: expected a list of ledger rows"]
    if not rows:
        return ["malformed report: empty ledger report"]

    previous_step = None
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            reasons.append(f"row {index} malformed report: expected object")
            previous_step = None
            continue

        if "step" not in row:
            reasons.append(f"row {index} missing required field: step")
            previous_step = None
            continue

        step = row["step"]
        if step in ("", None):
            reasons.append(f"row {index} malformed report: empty step name")
            previous_step = None
            continue

        if previous_step is not None and step == previous_step:
            reasons.append(
                f"row {index} ledger drift detected: "
                "duplicate consecutive step name"
            )

        previous_step = step

    return reasons


def check_ledger_report(rows: Any) -> tuple[bool, list[str]]:
    """Check whether saved ledger rows preserve ReTrace conservation."""

    reasons: list[str] = []

    if not isinstance(rows, list):
        return False, ["malformed report: expected a list of ledger rows"]
    if not rows:
        return False, ["malformed report: empty ledger report"]

    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            reasons.append(f"row {index} malformed report: expected object")
    if reasons:
        return False, reasons

    for index, row in enumerate(rows, start=1):
        missing_fields = REQUIRED_LEDGER_FIELDS - set(row)
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            reasons.append(f"row {index} missing required field: {missing}")
    if reasons:
        return False, reasons

    reasons.extend(check_row_sequence(rows))
    if reasons:
        return False, reasons

    baseline_ledger: Any | None = None
    for index, row in enumerate(rows, start=1):
        ledger = row["ledger"]
        if baseline_ledger is None:
            baseline_ledger = ledger

        try:
            row_identity = row["complexity_after"] + row["accumulated_defect"]
        except TypeError:
            reasons.append(
                f"row {index} identity violated: values are not numeric"
            )
            continue

        if ledger != row_identity:
            reasons.append(
                f"row {index} identity violated: "
                "ledger != complexity_after + accumulated_defect"
            )

        if ledger != baseline_ledger:
            reasons.append(f"row {index} ledger drift detected")
    if reasons:
        return False, reasons

    reasons.extend(check_defect_conservation(rows))
    if reasons:
        return False, reasons

    reasons.extend(check_accum_monotone(rows))
    if reasons:
        return False, reasons

    reasons.extend(check_defect_tally(rows))

    return not reasons, reasons
