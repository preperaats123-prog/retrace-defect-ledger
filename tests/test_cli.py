import json
from pathlib import Path
import subprocess
import sys


CSV_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "csv"

REQUIRED_LEDGER_FIELDS = {
    "step",
    "complexity_before",
    "complexity_after",
    "defect",
    "accumulated_defect",
    "ledger",
}


def test_python_module_demo_returns_table():
    result = subprocess.run(
        [sys.executable, "-m", "retrace", "demo"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "ReTrace Defect Ledger" in result.stdout
    assert "Ledger conserved: YES" in result.stdout


def test_trace_json_works_on_temporary_json_file(tmp_path):
    path = tmp_path / "input.json"
    path.write_text(json.dumps({"name": "Alex", "debug": "x" * 100}), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "retrace", "trace-json", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "identity" in result.stdout
    assert "ReTrace Defect Ledger" in result.stdout


def test_trace_json_missing_file_fails_cleanly(tmp_path):
    missing_path = tmp_path / "missing.json"

    result = subprocess.run(
        [sys.executable, "-m", "retrace", "trace-json", str(missing_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "file not found" in result.stderr


def test_trace_json_steps_file_can_transform_data(tmp_path):
    data_path = tmp_path / "input.json"
    steps_path = tmp_path / "steps.py"
    data_path.write_text(
        json.dumps({"keep": "a" * 100, "drop": "b" * 1000}),
        encoding="utf-8",
    )
    steps_path.write_text(
        "steps = [\n"
        "    ('drop_field', lambda state: {'keep': state['keep']}),\n"
        "]\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "retrace",
            "trace-json",
            str(data_path),
            "--steps",
            str(steps_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "drop_field" in result.stdout
    assert "Ledger conserved: YES" in result.stdout


def test_trace_json_one_drop(tmp_path):
    path = tmp_path / "input.json"
    path.write_text(
        json.dumps({"keep": "a" * 100, "debug": "x" * 1000}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "-m", "retrace", "trace-json", str(path), "--drop", "debug"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "drop_debug" in result.stdout
    assert "Ledger conserved: YES" in result.stdout


def test_trace_json_multiple_drops_preserve_command_line_order(tmp_path):
    path = tmp_path / "input.json"
    path.write_text(
        json.dumps({"headers": "h" * 1000, "metadata": "m" * 1000, "body": "b"}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "retrace",
            "trace-json",
            str(path),
            "--drop",
            "headers",
            "--drop",
            "metadata",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.index("drop_headers") < result.stdout.index("drop_metadata")


def test_trace_json_missing_drop_key_leaves_state_unchanged(tmp_path):
    path = tmp_path / "input.json"
    path.write_text(json.dumps({"keep": "a" * 100}), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "retrace", "trace-json", str(path), "--drop", "missing"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "drop_missing" in result.stdout
    assert "D=0" in result.stdout
    assert "Ledger conserved: YES" in result.stdout


def test_trace_json_drop_on_non_dict_input_leaves_state_unchanged(tmp_path):
    path = tmp_path / "input.json"
    path.write_text(json.dumps(["a", "b", "c"]), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "retrace", "trace-json", str(path), "--drop", "a"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "drop_a" in result.stdout
    assert "D=0" in result.stdout
    assert "Ledger conserved: YES" in result.stdout


def test_demo_json_report_creates_raw_ledger_file(tmp_path):
    report_path = tmp_path / "reports" / "demo-report.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "retrace",
            "demo",
            "--json-report",
            str(report_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "ReTrace Defect Ledger" in result.stdout
    _assert_valid_ledger_report(report_path)


def test_trace_json_report_creates_raw_ledger_file(tmp_path):
    data_path = tmp_path / "input.json"
    report_path = tmp_path / "nested" / "trace-report.json"
    data_path.write_text(
        json.dumps({"keep": "a" * 100, "debug_blob": "x" * 1000}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "retrace",
            "trace-json",
            str(data_path),
            "--drop",
            "debug_blob",
            "--json-report",
            str(report_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "ReTrace Defect Ledger" in result.stdout
    rows = _assert_valid_ledger_report(report_path)
    assert rows[0]["step"] == "drop_debug_blob"


def test_trace_csv_default_command(tmp_path):
    path = tmp_path / "users.csv"
    path.write_text("id,name,debug\n1,Ada,trace\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "retrace", "trace-csv", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "identity" in result.stdout
    assert "ReTrace Defect Ledger" in result.stdout


def test_trace_csv_one_drop_column(tmp_path):
    path = tmp_path / "users.csv"
    path.write_text("id,name,debug\n1,Ada,trace\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "retrace",
            "trace-csv",
            str(path),
            "--drop-column",
            "debug",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "drop_column_debug" in result.stdout
    assert "Ledger conserved: YES" in result.stdout


def test_trace_csv_multiple_drop_columns_preserve_order(tmp_path):
    path = tmp_path / "users.csv"
    path.write_text("id,name,debug,notes\n1,Ada,trace,temporary\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "retrace",
            "trace-csv",
            str(path),
            "--drop-column",
            "debug",
            "--drop-column",
            "notes",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.index("drop_column_debug") < result.stdout.index(
        "drop_column_notes"
    )


def test_trace_csv_missing_column_is_noop(tmp_path):
    path = tmp_path / "users.csv"
    path.write_text("id,name\n1,Ada\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "retrace",
            "trace-csv",
            str(path),
            "--drop-column",
            "debug",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "drop_column_debug" in result.stdout
    assert "D=0" in result.stdout


def test_trace_csv_json_report_and_check(tmp_path):
    csv_path = tmp_path / "users.csv"
    report_path = tmp_path / "reports" / "csv-report.json"
    csv_path.write_text("id,name,debug\n1,Ada,trace\n", encoding="utf-8")

    trace_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "retrace",
            "trace-csv",
            str(csv_path),
            "--drop-column",
            "debug",
            "--json-report",
            str(report_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    check_result = subprocess.run(
        [sys.executable, "-m", "retrace", "check", str(report_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert trace_result.returncode == 0
    assert check_result.returncode == 0
    rows = _assert_valid_ledger_report(report_path)
    assert rows[0]["step"] == "drop_column_debug"


def test_trace_csv_works_on_simple_fixture():
    result = subprocess.run(
        [sys.executable, "-m", "retrace", "trace-csv", str(CSV_FIXTURE_DIR / "simple.csv")],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "identity" in result.stdout
    assert "ReTrace Defect Ledger" in result.stdout


def test_trace_csv_drop_column_works_on_simple_fixture():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "retrace",
            "trace-csv",
            str(CSV_FIXTURE_DIR / "simple.csv"),
            "--drop-column",
            "debug",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "drop_column_debug" in result.stdout


def test_trace_csv_fixture_drop_order():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "retrace",
            "trace-csv",
            str(CSV_FIXTURE_DIR / "simple.csv"),
            "--drop-column",
            "notes",
            "--drop-column",
            "debug",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.index("drop_column_notes") < result.stdout.index(
        "drop_column_debug"
    )


def test_trace_csv_works_on_quoted_fixture():
    result = subprocess.run(
        [sys.executable, "-m", "retrace", "trace-csv", str(CSV_FIXTURE_DIR / "quoted.csv")],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "ReTrace Defect Ledger" in result.stdout


def test_trace_csv_works_on_numeric_strings_fixture():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "retrace",
            "trace-csv",
            str(CSV_FIXTURE_DIR / "numeric_strings.csv"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "ReTrace Defect Ledger" in result.stdout


def test_trace_csv_fixture_json_report_and_check(tmp_path):
    report_path = tmp_path / "reports" / "fixture-report.json"
    trace_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "retrace",
            "trace-csv",
            str(CSV_FIXTURE_DIR / "simple.csv"),
            "--drop-column",
            "debug",
            "--json-report",
            str(report_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    check_result = subprocess.run(
        [sys.executable, "-m", "retrace", "check", str(report_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert trace_result.returncode == 0
    assert check_result.returncode == 0
    assert "Ledger conserved: YES" in check_result.stdout
    _assert_valid_ledger_report(report_path)


def test_trace_csv_missing_file_fails_cleanly(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "retrace", "trace-csv", str(tmp_path / "missing.csv")],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "file not found" in result.stderr


def test_version_flag_returns_version():
    result = subprocess.run(
        [sys.executable, "-m", "retrace", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "retrace 0.1.1" in result.stdout


def test_check_valid_exported_report_passes(tmp_path):
    report_path = tmp_path / "report.json"
    export_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "retrace",
            "demo",
            "--json-report",
            str(report_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    check_result = subprocess.run(
        [sys.executable, "-m", "retrace", "check", str(report_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert export_result.returncode == 0
    assert check_result.returncode == 0
    assert "Ledger conserved: YES" in check_result.stdout


def test_check_missing_file_fails_cleanly(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "retrace", "check", str(tmp_path / "missing.json")],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Ledger conserved: NO" in result.stdout
    assert "file not found" in result.stdout


def test_check_invalid_json_fails_cleanly(tmp_path):
    report_path = tmp_path / "bad.json"
    report_path.write_text("{not json", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "retrace", "check", str(report_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Ledger conserved: NO" in result.stdout
    assert "invalid JSON" in result.stdout


def test_check_json_object_instead_of_list_fails(tmp_path):
    report_path = tmp_path / "object.json"
    report_path.write_text(json.dumps({"rows": []}), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "retrace", "check", str(report_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "malformed report" in result.stdout


def test_check_empty_list_fails(tmp_path):
    report_path = tmp_path / "empty.json"
    report_path.write_text("[]", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "retrace", "check", str(report_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "empty ledger report" in result.stdout


def test_check_missing_required_field_fails(tmp_path):
    report_path = tmp_path / "missing-field.json"
    report_path.write_text(
        json.dumps(
            [
                {
                    "step": "drop_a",
                    "complexity_before": 20,
                    "complexity_after": 15,
                    "defect": 5,
                    "ledger": 20,
                }
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "-m", "retrace", "check", str(report_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "missing required field" in result.stdout


def test_check_row_identity_violation_fails(tmp_path):
    report_path = tmp_path / "identity-violation.json"
    report_path.write_text(
        json.dumps(
            [
                {
                    "step": "drop_a",
                    "complexity_before": 20,
                    "complexity_after": 15,
                    "defect": 5,
                    "accumulated_defect": 4,
                    "ledger": 20,
                }
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "-m", "retrace", "check", str(report_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "identity violated" in result.stdout


def test_check_ledger_drift_fails(tmp_path):
    report_path = tmp_path / "ledger-drift.json"
    report_path.write_text(
        json.dumps(
            [
                {
                    "step": "drop_a",
                    "complexity_before": 20,
                    "complexity_after": 15,
                    "defect": 5,
                    "accumulated_defect": 5,
                    "ledger": 20,
                },
                {
                    "step": "drop_b",
                    "complexity_before": 15,
                    "complexity_after": 11,
                    "defect": 4,
                    "accumulated_defect": 10,
                    "ledger": 21,
                },
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "-m", "retrace", "check", str(report_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "ledger drift detected" in result.stdout


def _assert_valid_ledger_report(report_path):
    rows = json.loads(report_path.read_text(encoding="utf-8"))

    assert isinstance(rows, list)
    assert rows
    for row in rows:
        assert REQUIRED_LEDGER_FIELDS <= set(row)
        assert "ReTrace Defect Ledger" not in row.values()
        assert row["ledger"] == row["complexity_after"] + row["accumulated_defect"]

    return rows
