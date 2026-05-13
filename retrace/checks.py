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


def check_ledger_report(rows: Any) -> tuple[bool, list[str]]:
    """Check whether saved ledger rows preserve ReTrace conservation."""

    reasons: list[str] = []

    if not isinstance(rows, list):
        return False, ["malformed report: expected a list of ledger rows"]
    if not rows:
        return False, ["malformed report: empty ledger report"]

    baseline_ledger: Any | None = None
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            reasons.append(f"row {index} malformed report: expected object")
            continue

        missing_fields = REQUIRED_LEDGER_FIELDS - set(row)
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            reasons.append(f"row {index} missing required field: {missing}")
            continue

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

    return not reasons, reasons
