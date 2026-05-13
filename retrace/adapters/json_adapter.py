"""Small JSON file helpers for ReTrace."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: str | Path) -> Any:
    """Load one JSON value from a UTF-8 file."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path: str | Path, value: Any) -> None:
    """Save one JSON value in canonical UTF-8 form."""

    Path(path).write_bytes(canonical_json_bytes(value))


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize a JSON-compatible value to deterministic UTF-8 bytes."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
