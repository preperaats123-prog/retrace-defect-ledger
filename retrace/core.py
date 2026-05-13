"""Compression-complexity flight recorder for deterministic pipelines.

ReTrace uses deterministic serialization and zlib compressed byte length as a
practical structural-complexity estimate:

    C(x) = len(zlib.compress(serialize(x)))
    D_n = max(0, C(x_n) - C(x_{n+1}))
    L_n = C(x_n) + accumulated_defect

It records apparent representation shrinkage. It does not prove semantic data
loss, privacy, anonymization, or true information-theoretic loss.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any
import zlib


@dataclass(frozen=True)
class ComplexitySnapshot:
    """A deterministic byte snapshot and its zlib complexity estimate."""

    raw_bytes: int
    compressed_bytes: int
    compression_ratio: float
    hamming_weight: int
    sha256: str


@dataclass(frozen=True)
class LedgerStep:
    """One ledger row for a deterministic transform."""

    step: str
    complexity_before: int
    complexity_after: int
    defect: int
    accumulated_defect: int
    ledger: int
    signature_drift: int


def trace_pipeline(
    initial_state: Any,
    steps: Sequence[Callable[[Any], Any] | tuple[str, Callable[[Any], Any]]],
    *,
    serializer: Callable[[Any], bytes] | None = None,
    compression_level: int = 9,
    include_states: bool = False,
) -> list[dict[str, Any]]:
    """Run a deterministic pipeline and return ReTrace ledger rows."""

    _validate_compression_level(compression_level)
    encode = serializer or stable_bytes

    state = initial_state
    state_bytes = encode(state)
    previous_snapshot = _snapshot(state_bytes, compression_level)
    accumulated_defect = 0
    ledger: list[dict[str, Any]] = []

    for index, step_definition in enumerate(steps, start=1):
        step_name, step_function = _normalize_step(step_definition, index)
        next_state = step_function(state)
        next_state_bytes = encode(next_state)
        next_snapshot = _snapshot(next_state_bytes, compression_level)

        defect = max(
            0,
            previous_snapshot.compressed_bytes - next_snapshot.compressed_bytes,
        )
        accumulated_defect += defect

        row: dict[str, Any] = asdict(
            LedgerStep(
                step=step_name,
                complexity_before=previous_snapshot.compressed_bytes,
                complexity_after=next_snapshot.compressed_bytes,
                defect=defect,
                accumulated_defect=accumulated_defect,
                ledger=next_snapshot.compressed_bytes + accumulated_defect,
                signature_drift=_hamming_distance(
                    zlib.compress(state_bytes, compression_level),
                    zlib.compress(next_state_bytes, compression_level),
                ),
            )
        )
        if include_states:
            row["state"] = next_state

        ledger.append(row)
        state = next_state
        state_bytes = next_state_bytes
        previous_snapshot = next_snapshot

    if include_states and ledger:
        ledger[-1]["final_state"] = state

    return ledger


def compare_zlib_complexity(
    function: Callable[[Any], Any],
    before_dataset: Any,
    after_dataset: Any,
    *,
    serializer: Callable[[Any], bytes] | None = None,
    compression_level: int = 9,
    include_outputs: bool = False,
) -> dict[str, Any]:
    """Run one function on two datasets and compare compressed complexity."""

    _validate_compression_level(compression_level)
    encode = serializer or stable_bytes

    before_output = function(before_dataset)
    after_output = function(after_dataset)

    before_input_bytes = encode(before_dataset)
    after_input_bytes = encode(after_dataset)
    before_output_bytes = encode(before_output)
    after_output_bytes = encode(after_output)

    before_input = _snapshot(before_input_bytes, compression_level)
    after_input = _snapshot(after_input_bytes, compression_level)
    before_result = _snapshot(before_output_bytes, compression_level)
    after_result = _snapshot(after_output_bytes, compression_level)

    before_defect = max(
        0,
        before_input.compressed_bytes - before_result.compressed_bytes,
    )
    after_defect = max(
        0,
        after_input.compressed_bytes - after_result.compressed_bytes,
    )

    report: dict[str, Any] = {
        "function": getattr(function, "__name__", function.__class__.__name__),
        "compression_level": compression_level,
        "before": {
            "input": asdict(before_input),
            "output": asdict(before_result),
            "complexity_delta": before_result.compressed_bytes
            - before_input.compressed_bytes,
            "defect": before_defect,
            "ledger": before_result.compressed_bytes + before_defect,
            "signature_drift": _hamming_distance(
                zlib.compress(before_input_bytes, compression_level),
                zlib.compress(before_output_bytes, compression_level),
            ),
        },
        "after": {
            "input": asdict(after_input),
            "output": asdict(after_result),
            "complexity_delta": after_result.compressed_bytes
            - after_input.compressed_bytes,
            "defect": after_defect,
            "ledger": after_result.compressed_bytes + after_defect,
            "signature_drift": _hamming_distance(
                zlib.compress(after_input_bytes, compression_level),
                zlib.compress(after_output_bytes, compression_level),
            ),
        },
        "comparison": {
            "input_complexity_delta": after_input.compressed_bytes
            - before_input.compressed_bytes,
            "output_complexity_delta": after_result.compressed_bytes
            - before_result.compressed_bytes,
            "transform_delta_drift": (
                after_result.compressed_bytes - after_input.compressed_bytes
            )
            - (before_result.compressed_bytes - before_input.compressed_bytes),
            "defect_growth": after_defect - before_defect,
            "cross_output_signature_drift": _hamming_distance(
                zlib.compress(before_output_bytes, compression_level),
                zlib.compress(after_output_bytes, compression_level),
            ),
            "ledger_delta": (after_result.compressed_bytes + after_defect)
            - (before_result.compressed_bytes + before_defect),
        },
    }

    if include_outputs:
        report["before"]["return_value"] = before_output
        report["after"]["return_value"] = after_output

    return report


def compressed_complexity(
    value: Any,
    *,
    serializer: Callable[[Any], bytes] | None = None,
    compression_level: int = 9,
) -> int:
    """Return ``C(x)`` as deterministic zlib compressed byte length."""

    _validate_compression_level(compression_level)
    encode = serializer or stable_bytes
    return _snapshot(encode(value), compression_level).compressed_bytes


def stable_bytes(value: Any) -> bytes:
    """Serialize common Python values to deterministic UTF-8 bytes."""

    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, str):
        return value.encode("utf-8")

    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        return repr(value).encode("utf-8")


def _snapshot(data: bytes, compression_level: int) -> ComplexitySnapshot:
    compressed = zlib.compress(data, compression_level)
    raw_size = len(data)
    return ComplexitySnapshot(
        raw_bytes=raw_size,
        compressed_bytes=len(compressed),
        compression_ratio=len(compressed) / raw_size if raw_size else 0.0,
        hamming_weight=_hamming_weight(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )


def _validate_compression_level(compression_level: int) -> None:
    if not 0 <= compression_level <= 9:
        raise ValueError("compression_level must be between 0 and 9")


def _normalize_step(
    step_definition: Callable[[Any], Any] | tuple[str, Callable[[Any], Any]],
    index: int,
) -> tuple[str, Callable[[Any], Any]]:
    if isinstance(step_definition, tuple):
        step_name, step_function = step_definition
    else:
        step_function = step_definition
        step_name = getattr(step_function, "__name__", f"step_{index}")

    if not callable(step_function):
        raise TypeError(f"pipeline step {index} is not callable")

    return step_name, step_function


def _hamming_weight(data: bytes) -> int:
    return sum(byte.bit_count() for byte in data)


def _hamming_distance(left: bytes, right: bytes) -> int:
    shared = sum(
        (left_byte ^ right_byte).bit_count()
        for left_byte, right_byte in zip(left, right, strict=False)
    )
    extra = left[len(right) :] if len(left) > len(right) else right[len(left) :]
    return shared + _hamming_weight(extra)
