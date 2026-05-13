from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from retrace import print_ledger_table, trace_pipeline


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
            key: value for key, value in state.items() if key != "temporary_notes"
        },
    ),
    ("export_public_record", lambda state: {"id": state["id"], "name": state["name"]}),
]

ledger = trace_pipeline(record, steps)

print_ledger_table(ledger)
