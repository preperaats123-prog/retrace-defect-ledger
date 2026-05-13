"""Terminal output helpers for ReTrace ledger rows."""

from __future__ import annotations

from collections.abc import Sequence
import json
from pathlib import Path
from typing import Any


def render_ledger_table(
    ledger: Sequence[dict[str, Any]],
    *,
    title: str = "ReTrace Defect Ledger v0.1",
) -> str:
    """Render ReTrace ledger rows as a compact terminal table."""

    if not ledger:
        return f"{title}\nNo ledger rows."

    initial_complexity = int(ledger[0]["complexity_before"])
    total_defect = int(ledger[-1]["accumulated_defect"])
    ledger_conserved = all(int(row["ledger"]) == initial_complexity for row in ledger)
    step_width = max(len("input"), *(len(str(row["step"])) for row in ledger))
    divider = "─" * max(44, step_width + 42)

    lines = [
        title,
        divider,
        _format_row(
            step_number=0,
            step_name="input",
            complexity=initial_complexity,
            defect=0,
            ledger_value=initial_complexity,
            step_width=step_width,
        ),
    ]

    for step_number, row in enumerate(ledger, start=1):
        lines.append(
            _format_row(
                step_number=step_number,
                step_name=str(row["step"]),
                complexity=int(row["complexity_after"]),
                defect=int(row["defect"]),
                ledger_value=int(row["ledger"]),
                step_width=step_width,
            )
        )

    lines.extend(
        [
            divider,
            f"Total defect: {total_defect}",
            f"Ledger conserved: {'YES' if ledger_conserved else 'NO'}",
        ]
    )
    return "\n".join(lines)


def print_ledger_table(
    ledger: Sequence[dict[str, Any]],
    *,
    title: str = "ReTrace Defect Ledger v0.1",
) -> None:
    """Print ReTrace ledger rows as a compact terminal table."""

    print(render_ledger_table(ledger, title=title))


def save_ledger_report(path: str | Path, ledger_rows: list[dict[str, Any]]) -> None:
    """Save raw structured ledger rows as a JSON report."""

    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as report_file:
        json.dump(
            ledger_rows,
            report_file,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        report_file.write("\n")


def _format_row(
    *,
    step_number: int,
    step_name: str,
    complexity: int,
    defect: int,
    ledger_value: int,
    step_width: int,
) -> str:
    return (
        f"Step {step_number:<2} "
        f"{step_name:<{step_width}}  "
        f"C={complexity:<5} "
        f"D={defect:<5} "
        f"L={ledger_value}"
    )
