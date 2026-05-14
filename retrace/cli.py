"""Command line interface for ReTrace."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

from retrace import (
    __version__,
    check_ledger_report,
    print_ledger_table,
    save_ledger_report,
    trace_pipeline,
)
from retrace.adapters.csv_adapter import load_csv
from retrace.adapters.json_adapter import load_json


def main(argv: list[str] | None = None) -> int:
    """Run the ReTrace CLI."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "demo":
        return _run_demo(args.json_report)
    if args.command == "trace-json":
        return _run_trace_json(args.path, args.steps, args.drop, args.json_report)
    if args.command == "trace-csv":
        return _run_trace_csv(args.path, args.drop_column, args.json_report)
    if args.command == "check":
        return _run_check(args.path)

    parser.print_help()
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="retrace",
        description="Small deterministic tracing tool for data transformations.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"retrace {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")

    demo = subparsers.add_parser(
        "demo",
        help="run the built-in representation-shrinkage demo",
        description="Run the built-in demo and print ReTrace ledger rows.",
    )
    demo.add_argument(
        "--json-report",
        type=Path,
        help="write raw ledger rows to a JSON report",
    )

    trace_json = subparsers.add_parser(
        "trace-json",
        help="trace a JSON file with the identity step, drops, or a steps file",
        description=(
            "Trace a JSON file. With no drops or steps file, ReTrace records "
            "the identity step."
        ),
    )
    trace_json.add_argument("path", type=Path, help="path to a JSON file")
    trace_json.add_argument(
        "--steps",
        type=Path,
        help="optional .py file containing a list or tuple named 'steps'",
    )
    trace_json.add_argument(
        "--drop",
        action="append",
        default=[],
        metavar="KEY",
        help="drop a root-level JSON object key; repeat to drop keys in order",
    )
    trace_json.add_argument(
        "--json-report",
        type=Path,
        help="write raw ledger rows to a JSON report",
    )

    trace_csv = subparsers.add_parser(
        "trace-csv",
        help="trace a CSV file with the identity step or column drops",
        description=(
            "Trace CSV rows loaded as string dictionaries. With no column "
            "drops, ReTrace records the identity step."
        ),
    )
    trace_csv.add_argument("path", type=Path, help="path to a CSV file")
    trace_csv.add_argument(
        "--drop-column",
        action="append",
        default=[],
        metavar="NAME",
        help="drop a CSV column; repeat to drop columns in order",
    )
    trace_csv.add_argument(
        "--json-report",
        type=Path,
        help="write raw ledger rows to a JSON report",
    )

    check = subparsers.add_parser(
        "check",
        help="validate ledger identity and conserved value in a JSON report",
        description=(
            "Validate a non-empty JSON report by checking required ledger "
            "fields, ledger identity, and a conserved ledger value."
        ),
    )
    check.add_argument("path", type=Path, help="path to a ReTrace JSON report")

    return parser


def _run_demo(report_path: Path | None) -> int:
    record = {
        "id": 1,
        "name": "  ALEX SAMPLE  ",
        "email": "alex@example.com",
        "debug_blob": "x" * 2000,
        "temporary_notes": "y" * 1000,
    }
    steps = [
        ("strip_name", lambda state: {**state, "name": state["name"].strip()}),
        (
            "drop_debug_blob",
            lambda state: {
                key: value for key, value in state.items() if key != "debug_blob"
            },
        ),
        (
            "drop_temporary_notes",
            lambda state: {
                key: value
                for key, value in state.items()
                if key != "temporary_notes"
            },
        ),
        (
            "export_public_record",
            lambda state: {"id": state["id"], "name": state["name"]},
        ),
    ]

    ledger = trace_pipeline(record, steps)
    return _emit_ledger(ledger, report_path)


def _run_trace_json(
    path: Path,
    steps_path: Path | None,
    drop_keys: list[str],
    report_path: Path | None,
) -> int:
    try:
        data = load_json(path)
        steps = _build_trace_json_steps(steps_path, drop_keys)
    except FileNotFoundError as error:
        print(f"retrace: file not found: {error.filename}", file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError) as error:
        print(f"retrace: {error}", file=sys.stderr)
        return 1

    return _emit_ledger(trace_pipeline(data, steps), report_path)


def _run_trace_csv(
    path: Path,
    drop_columns: list[str],
    report_path: Path | None,
) -> int:
    try:
        rows = load_csv(path)
        steps = _build_trace_csv_steps(drop_columns)
    except FileNotFoundError as error:
        print(f"retrace: file not found: {error.filename}", file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError) as error:
        print(f"retrace: {error}", file=sys.stderr)
        return 1

    return _emit_ledger(trace_pipeline(rows, steps), report_path)


def _emit_ledger(ledger: list[dict[str, Any]], report_path: Path | None) -> int:
    try:
        print_ledger_table(ledger)
        if report_path is not None:
            save_ledger_report(report_path, ledger)
    except OSError as error:
        print(f"retrace: {error}", file=sys.stderr)
        return 1

    return 0


def _build_trace_json_steps(steps_path: Path | None, drop_keys: list[str]) -> list[Any]:
    steps = list(_load_steps(steps_path)) if steps_path else []
    steps.extend(_drop_step(key) for key in drop_keys)

    if not steps:
        steps.append(("identity", lambda state: state))

    return steps


def _build_trace_csv_steps(drop_columns: list[str]) -> list[Any]:
    steps = [_drop_column_step(column) for column in drop_columns]

    if not steps:
        steps.append(("identity", lambda rows: rows))

    return steps


def _drop_step(key: str) -> tuple[str, Any]:
    def drop_key(state: Any) -> Any:
        if not isinstance(state, dict) or key not in state:
            return state

        return {
            current_key: value
            for current_key, value in state.items()
            if current_key != key
        }

    return f"drop_{key}", drop_key


def _drop_column_step(column: str) -> tuple[str, Any]:
    def drop_column(rows: Any) -> Any:
        if not isinstance(rows, list):
            return rows

        next_rows = []
        for row in rows:
            if not isinstance(row, dict) or column not in row:
                next_rows.append(row.copy() if isinstance(row, dict) else row)
                continue

            next_rows.append(
                {
                    current_column: value
                    for current_column, value in row.items()
                    if current_column != column
                }
            )

        return next_rows

    return f"drop_column_{column}", drop_column


def _load_steps(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(path)

    spec = importlib.util.spec_from_file_location("retrace_user_steps", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"could not import steps file: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    steps = getattr(module, "steps", None)
    if not isinstance(steps, (list, tuple)):
        raise TypeError("steps file must define a list or tuple named 'steps'")

    return steps


def _run_check(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8") as report_file:
            rows = json.load(report_file)
    except FileNotFoundError:
        print("Ledger conserved: NO")
        print(f"Reason: file not found: {path}")
        return 1
    except json.JSONDecodeError as error:
        print("Ledger conserved: NO")
        print(f"Reason: invalid JSON: {error.msg}")
        return 1
    except OSError as error:
        print("Ledger conserved: NO")
        print(f"Reason: {error}")
        return 1

    conserved, reasons = check_ledger_report(rows)
    if conserved:
        print("Ledger conserved: YES")
        return 0

    print("Ledger conserved: NO")
    for reason in reasons:
        print(f"Reason: {reason}")
    return 1
