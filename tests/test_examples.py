import subprocess
import sys


def test_trace_data_spec_example_runs():
    result = subprocess.run(
        [sys.executable, "examples/trace_data_spec.py"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "ReTrace Text Note Trace" in result.stdout
    assert "parse_sections" in result.stdout
    assert "keep_core_contract" in result.stdout
    assert "keep_formula_lines" in result.stdout
    assert "Ledger conserved: YES" in result.stdout
