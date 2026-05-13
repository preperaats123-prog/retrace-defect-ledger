# ReTrace Defect Ledger

ReTrace is a deterministic compression-complexity flight recorder for data
transformations. It helps answer one practical debugging question:

> At which step did this representation collapse?

It estimates each pipeline state with deterministic serialization plus zlib
compressed byte length. When a transform makes the representation smaller,
ReTrace records that shrinkage as a defect balance instead of letting it vanish
silently.

```text
C(x) = len(zlib.compress(serialize(x)))
D_step = max(0, C(before) - C(after))
ledger = C(after) + accumulated_defect
```

ReTrace records apparent structural collapse. It does not prove semantic data
loss, privacy, anonymization, or true information-theoretic loss.

## What It Looks Like

Run the demo:

```bash
python examples/basic_trace.py
```

Example output:

```text
ReTrace Defect Ledger v0.1
──────────────────────────────────────────────────────────────
Step 0  input                 C=124   D=0     L=124
Step 1  strip_name            C=121   D=3     L=124
Step 2  drop_debug_blob       C=96    D=25    L=124
Step 3  drop_temporary_notes  C=69    D=27    L=124
Step 4  export_public_record  C=40    D=29    L=124
──────────────────────────────────────────────────────────────
Total defect: 84
Ledger conserved: YES
```

## Basic Usage

```python
from retrace import print_ledger_table, trace_pipeline

record = {
    "id": 1,
    "name": "  GUNTARS NOSALS  ",
    "debug_blob": "x" * 2000,
}

steps = [
    ("strip_name", lambda state: {**state, "name": state["name"].strip()}),
    ("drop_debug_blob", lambda state: {
        key: value for key, value in state.items() if key != "debug_blob"
    }),
]

ledger = trace_pipeline(record, steps)
print_ledger_table(ledger)
```

Every core feature produces or consumes ledger rows with this shape:

```python
{
    "step": str,
    "complexity_before": int,
    "complexity_after": int,
    "defect": int,
    "accumulated_defect": int,
    "ledger": int,
}
```

## JSON Adapter

The JSON adapter intentionally does only boring file plumbing:

```python
from retrace.adapters.json_adapter import (
    canonical_json_bytes,
    load_json,
    save_json,
)

data = load_json("input.json")
bytes_for_measurement = canonical_json_bytes(data)
save_json("canonical.json", data)
```

It does not analyze defects and does not print. It exists so real JSON data can
feed `trace_pipeline(...)` through stable, canonical bytes.

## Intended Use

Good fits:

- locating unexpected truncation
- finding field drops and row filtering
- spotting schema narrowing or type coercion
- measuring rounding, deduplication, feature pruning, and lossy export
- producing reproducible audit-support traces

Bad claims:

- proves anonymization
- proves privacy
- proves true data loss
- computes real Kolmogorov complexity

The honest claim is narrower and stronger: ReTrace can show where a
deterministic representation got smaller under a declared serializer and
compressor.

## Limitations

- zlib compressed size is only a practical complexity proxy.
- Small payloads can be noisy because compression overhead dominates.
- Canonical serialization matters; otherwise formatting drift can look like
  structural drift.
- Loss-only mode treats complexity gains as external input, not negative
  defects.

## Development

Run tests:

```bash
python -m pytest -q
```

The package has no runtime dependencies beyond Python's standard library.
