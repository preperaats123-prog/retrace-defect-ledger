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
from retrace.adapters.json_adapter import load_json


def main(argv: list[str] | None = None) -> int:
    """Run the ReTrace CLI."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "demo":
        return _run_demo(args.json_report)
    if args.command == "trace-json":
        return _run_trace_json(args.path, args.steps, args.drop, args.json_report)
    if args.command == "check":
        return _run_check(args.path)

    parser.print_help()
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="retrace",
        description="Deterministic compression-complexity flight recorder.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"retrace {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")

    demo = subparsers.add_parser(
        "demo",
        help="run the built-in demo pipeline",
    )
    demo.add_argument(
        "--json-report",
        type=Path,
        help="write raw ledger rows to a JSON report file",
    )

    trace_json = subparsers.add_parser(
        "trace-json",
        help="trace a JSON file with an identity pipeline or a steps file",
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
        help="write raw ledger rows to a JSON report file",
    )

    check = subparsers.add_parser(
        "check",
        help="validate a saved ReTrace JSON report",
    )
    check.add_argument("path", type=Path, help="path to a JSON report file")

    return parser


def _run_demo(report_path: Path | None) -> int:
    record = {
        "id": 1,
        "name": "  GUNTARS NOSALS  ",
        "email": "guntars@example.com",
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
