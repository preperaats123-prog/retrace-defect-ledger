"""Trace a local text note as a concrete ReTrace artifact.

This example treats text as ordinary input data and records when declared
transforms make the measured representation smaller.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from retrace import print_ledger_table, trace_pipeline


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data"
FALLBACK_SPEC = """Each raw row corresponds to a finite-dimensional invariant vector.
--
Warnings

Silent drops must be visible.
--
Formulas

ledger = C(after) + accumulated_defect
--
Info

Use this as a small built-in fallback when the local data note is absent.
"""


def load_spec_state(path: Path = DATA_PATH) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8") if path.exists() else FALLBACK_SPEC
    return {
        "source": path.name,
        "text": text,
        "line_count": len(text.splitlines()),
    }


def parse_sections(state: dict[str, Any]) -> dict[str, Any]:
    text = state["text"]
    sections = {
        "core": text,
    }

    if "\n--\nWarnings\n\n" in text:
        core, remainder = text.split("\n--\nWarnings\n\n", maxsplit=1)
        sections = {
            "core": core.strip(),
            "warnings": remainder.strip(),
        }

    if "\n--\nFormulas\n\n" in sections.get("warnings", ""):
        warnings, remainder = sections["warnings"].split(
            "\n--\nFormulas\n\n",
            maxsplit=1,
        )
        sections["warnings"] = warnings.strip()
        sections["formulas"] = remainder.strip()

    if "\n--\nInfo\n\n" in sections.get("formulas", ""):
        formulas, info = sections["formulas"].split("\n--\nInfo\n\n", maxsplit=1)
        sections["formulas"] = formulas.strip()
        sections["info"] = info.strip()

    return {
        "source": state["source"],
        "sections": sections,
        "section_count": len(sections),
    }


def keep_core_contract(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": state["source"],
        "core": state["sections"].get("core", ""),
    }


def keep_formula_lines(state: dict[str, Any]) -> dict[str, Any]:
    lines = state["core"].splitlines()
    formula_lines = [
        line
        for line in lines
        if any(token in line for token in ("=", "\\sum", "\\boxed", "ledger"))
    ]
    return {
        "source": state["source"],
        "formula_lines": formula_lines,
    }


def main() -> None:
    steps = [
        ("parse_sections", parse_sections),
        ("keep_core_contract", keep_core_contract),
        ("keep_formula_lines", keep_formula_lines),
    ]
    ledger = trace_pipeline(load_spec_state(), steps)
    print_ledger_table(ledger, title="ReTrace Text Note Trace")


if __name__ == "__main__":
    main()
