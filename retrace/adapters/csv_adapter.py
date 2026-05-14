"""Small CSV file helpers for ReTrace."""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path


def load_csv(path: str | Path) -> list[dict[str, str]]:
    """Load CSV rows as dictionaries of strings."""

    with Path(path).open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file, restval="")
        rows: list[dict[str, str]] = []
        for row in reader:
            if None in row:
                raise ValueError(f"CSV row {reader.line_num} has extra fields")
            rows.append(dict(row))
        return rows


def save_csv(path: str | Path, rows: list[dict[str, str]]) -> None:
    """Save CSV rows in deterministic UTF-8 form."""

    Path(path).write_bytes(canonical_csv_bytes(rows))


def canonical_csv_bytes(rows: list[dict[str, str]]) -> bytes:
    """Serialize CSV rows to deterministic UTF-8 bytes."""

    if not rows:
        return b""

    fieldnames = list(rows[0].keys())
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames,
        lineterminator="\n",
        extrasaction="ignore",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in fieldnames})

    return output.getvalue().encode("utf-8")
