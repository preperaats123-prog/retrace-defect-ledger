from retrace import (
    compressed_complexity,
    compare_zlib_complexity,
    render_ledger_table,
    trace_pipeline,
)
from retrace.adapters.json_adapter import canonical_json_bytes, load_json, save_json


def test_compressed_complexity_returns_nonnegative_int():
    value = {"a": 1, "b": "hello"}
    complexity = compressed_complexity(value)

    assert isinstance(complexity, int)
    assert complexity >= 0


def test_trace_pipeline_records_loss_defect():
    initial = {
        "keep": "a" * 100,
        "drop": "b" * 1000,
    }

    steps = [
        ("drop_field", lambda state: {"keep": state["keep"]}),
    ]

    ledger = trace_pipeline(initial, steps)

    assert len(ledger) == 1
    assert ledger[0]["complexity_before"] >= ledger[0]["complexity_after"]
    assert ledger[0]["defect"] >= 0
    assert ledger[0]["accumulated_defect"] == ledger[0]["defect"]
    assert ledger[0]["ledger"] == (
        ledger[0]["complexity_after"] + ledger[0]["accumulated_defect"]
    )


def test_trace_pipeline_conserved_for_decreasing_pipeline():
    initial = {
        "a": "x" * 1000,
        "b": "y" * 1000,
        "c": "z" * 1000,
    }

    steps = [
        ("drop_c", lambda state: {"a": state["a"], "b": state["b"]}),
        ("drop_b", lambda state: {"a": state["a"]}),
    ]

    ledger = trace_pipeline(initial, steps)

    original_complexity = ledger[0]["complexity_before"]

    for row in ledger:
        assert row["ledger"] == original_complexity
        assert row["ledger"] == row["complexity_after"] + row["accumulated_defect"]


def test_trace_pipeline_no_defect_for_complexity_gain():
    initial = {"x": "a"}

    steps = [
        ("add_field", lambda state: {**state, "new": "r4Nd0mISH" * 100}),
    ]

    ledger = trace_pipeline(initial, steps)

    assert ledger[0]["complexity_after"] >= ledger[0]["complexity_before"]
    assert ledger[0]["defect"] == 0


def test_compare_zlib_complexity_smoke():
    def normalize(record):
        return {
            "name": record["name"].strip().lower(),
            "age": int(record["age"]),
        }

    before = {"name": " GUNTARS ", "age": "24", "debug": "x" * 100}
    after = {"name": "Guntars", "age": "24", "debug": "x" * 50}

    report = compare_zlib_complexity(normalize, before, after)

    assert "before" in report
    assert "after" in report
    assert "comparison" in report


def test_render_ledger_table_shows_conservation_summary():
    initial = {
        "a": "x" * 1000,
        "b": "y" * 1000,
    }
    steps = [
        ("drop_b", lambda state: {"a": state["a"]}),
    ]

    ledger = trace_pipeline(initial, steps)
    table = render_ledger_table(ledger)

    assert "ReTrace Defect Ledger v0.1" in table
    assert "Step 0" in table
    assert "drop_b" in table
    assert "Total defect:" in table
    assert "Ledger conserved: YES" in table


def test_json_adapter_loads_and_saves_canonical_json(tmp_path):
    path = tmp_path / "record.json"
    value = {"z": 1, "a": ["Guntars", "ā"]}

    save_json(path, value)

    assert load_json(path) == value
    assert path.read_bytes() == b'{"a":["Guntars","\xc4\x81"],"z":1}'


def test_canonical_json_bytes_are_stable():
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}

    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert canonical_json_bytes(left) == b'{"a":1,"b":2}'
