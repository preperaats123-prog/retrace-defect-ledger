from pathlib import Path

import pytest

from retrace.adapters.csv_adapter import canonical_csv_bytes, load_csv, save_csv


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "csv"


def test_load_csv_reads_rows_as_strings(tmp_path):
    path = tmp_path / "users.csv"
    path.write_text("id,name,debug\n1,Ada,trace\n2,Linus,verbose\n", encoding="utf-8")

    rows = load_csv(path)

    assert rows == [
        {"id": "1", "name": "Ada", "debug": "trace"},
        {"id": "2", "name": "Linus", "debug": "verbose"},
    ]
    assert list(rows[0].keys()) == ["id", "name", "debug"]


def test_save_csv_writes_rows(tmp_path):
    path = tmp_path / "users.csv"
    rows = [
        {"id": "1", "name": "Ada", "debug": "trace"},
        {"id": "2", "name": "Linus", "debug": "verbose"},
    ]

    save_csv(path, rows)

    assert path.read_text(encoding="utf-8") == (
        "id,name,debug\n"
        "1,Ada,trace\n"
        "2,Linus,verbose\n"
    )


def test_canonical_csv_bytes_are_stable():
    rows = [
        {"id": "1", "name": "Ada", "debug": "trace"},
        {"debug": "verbose", "name": "Linus", "id": "2"},
    ]

    assert canonical_csv_bytes(rows) == (
        b"id,name,debug\n"
        b"1,Ada,trace\n"
        b"2,Linus,verbose\n"
    )


def test_canonical_csv_bytes_for_empty_rows():
    assert canonical_csv_bytes([]) == b""


def test_load_csv_simple_fixture():
    rows = load_csv(FIXTURE_DIR / "simple.csv")

    assert rows[0] == {
        "id": "1",
        "name": "Ada",
        "debug": "trace",
        "notes": "alpha",
    }
    assert list(rows[0].keys()) == ["id", "name", "debug", "notes"]


def test_load_csv_preserves_values_as_strings():
    rows = load_csv(FIXTURE_DIR / "numeric_strings.csv")

    assert rows[0]["id"] == "00123"
    assert rows[0]["amount"] == "1.2300"
    assert rows[0]["rate"] == "1e-5"
    assert rows[0]["count"] == "0"
    assert rows[0]["delta"] == "-42"


def test_load_csv_handles_quoted_commas():
    rows = load_csv(FIXTURE_DIR / "quoted.csv")

    assert rows[0]["comment"] == "hello, world"
    assert rows[1]["comment"] == 'said "hello"'
    assert rows[2]["comment"] == "line one\nline two"


def test_load_csv_handles_empty_fields():
    rows = load_csv(FIXTURE_DIR / "missing_values.csv")

    assert rows[0]["debug"] == ""
    assert rows[1]["name"] == ""
    assert rows[1]["notes"] == ""
    assert rows[2]["debug"] == ""
    assert rows[2]["notes"] == ""


def test_load_csv_treats_short_rows_as_empty_strings(tmp_path):
    path = tmp_path / "short.csv"
    path.write_text("id,name,debug\n1,Ada\n", encoding="utf-8")

    assert load_csv(path) == [{"id": "1", "name": "Ada", "debug": ""}]


def test_load_csv_rejects_extra_fields(tmp_path):
    path = tmp_path / "extra.csv"
    path.write_text("id,name\n1,Ada,extra\n", encoding="utf-8")

    with pytest.raises(ValueError, match="extra fields"):
        load_csv(path)


def test_canonical_csv_bytes_is_stable_for_loaded_fixture():
    rows = load_csv(FIXTURE_DIR / "simple.csv")

    assert canonical_csv_bytes(rows) == canonical_csv_bytes(
        load_csv(FIXTURE_DIR / "simple.csv")
    )


def test_save_then_load_roundtrip_preserves_rows_for_simple_fixture(tmp_path):
    rows = load_csv(FIXTURE_DIR / "simple.csv")
    path = tmp_path / "roundtrip.csv"

    save_csv(path, rows)

    assert load_csv(path) == rows
