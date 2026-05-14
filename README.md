# ReTrace Defect Ledger

ReTrace is a small deterministic tracing tool for data transformations. It
helps answer one practical debugging question:

> At which step did this representation get smaller?

It measures each pipeline state with deterministic serialization plus zlib
compressed byte length. When a transform makes that measured representation
smaller, ReTrace records the shrinkage in a ledger row.

```text
C(x) = len(zlib.compress(serialize(x)))
D_step = max(0, C(before) - C(after))
ledger = C(after) + accumulated_defect
```

Operationally:

- `defect` is the nonnegative compressed-byte shrinkage for one step.
- `accumulated_defect` is the running sum of step defects.
- `ledger` is `C(after) + accumulated_defect` for that row.

ReTrace records representation shrinkage under the selected serializer and
compressor. It does not prove semantic data loss, privacy, anonymization, or
true information-theoretic loss.

## What It Looks Like

Run the demo:

```bash
python examples/basic_trace.py
```

Example output:

```text
ReTrace Defect Ledger v0.1
──────────────────────────────────────────────────────────────
Step 0  input                 C=118   D=0     L=118
Step 1  strip_name            C=116   D=2     L=118
Step 2  drop_debug_blob       C=90    D=26    L=118
Step 3  drop_temporary_notes  C=63    D=27    L=118
Step 4  export_public_record  C=37    D=26    L=118
──────────────────────────────────────────────────────────────
Total defect: 81
Ledger conserved: YES
```

## Basic Usage

```python
from retrace import print_ledger_table, trace_pipeline

record = {
    "id": 1,
    "name": "  ALEX SAMPLE  ",
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

## CLI Quickstart

Run the built-in demo:

```bash
python -m retrace demo
```

Trace a JSON file with a root-level drop:

```bash
python -m retrace trace-json input.json --drop debug_blob
```

Trace a CSV file with a column drop:

```bash
python -m retrace trace-csv input.csv --drop-column debug_blob
```

Trace and export a JSON report:

```bash
python -m retrace trace-json input.json --drop debug_blob --json-report report.json
```

Validate a saved report:

```bash
python -m retrace check report.json
```

Trace a JSON file with the default identity step:

```bash
python -m retrace trace-json input.json
```

Trace a JSON file with a small Python steps file:

```bash
python -m retrace trace-json input.json --steps steps.py
```

Drop root-level JSON object keys from the command line:

```bash
python -m retrace trace-json telemetry.json --drop headers --drop metadata
```

For v0.1.x, `--drop` only supports root-level JSON object keys. Drops run in the
same order they appear on the command line. If a key is missing, or if the
current state is not a JSON object, the drop step leaves the state unchanged.

Export the raw structured ledger rows to JSON:

```bash
python -m retrace demo --json-report report.json
python -m retrace trace-json input.json --drop debug_blob --json-report report.json
python -m retrace trace-csv input.csv --drop-column debug_blob --json-report report.json
```

Reports contain the same ledger row dictionaries used by the terminal table.
They do not contain the rendered table string, and they do not summarize,
aggregate, rename, or drop rows.

The checker treats a report as a closed ledger boundary. It exits successfully
when the report is a non-empty list of row objects, every row has the required
ledger fields, every row satisfies
`ledger == complexity_after + accumulated_defect`, and every row has the same
ledger value. Extra fields are allowed.

The steps file must define `steps` as a list or tuple:

```python
steps = [
    ("drop_debug_blob", lambda state: {
        key: value for key, value in state.items() if key != "debug_blob"
    }),
]
```

After installation, the same CLI is exposed as:

```bash
retrace demo
retrace trace-json input.json
retrace trace-csv input.csv
retrace check report.json
```

`trace_pipeline(...)` produces ledger rows with this shape:

```python
{
    "step": str,
    "complexity_before": int,
    "complexity_after": int,
    "defect": int,
    "accumulated_defect": int,
    "ledger": int,
    "signature_drift": int,
}
```

The report checker requires `step`, `complexity_before`, `complexity_after`,
`defect`, `accumulated_defect`, and `ledger`. It allows extra fields such as
`signature_drift`.

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

It does not analyze defects and does not print. It exists so JSON data can be
loaded and saved using the same deterministic JSON form used by the default
serializer.

## CSV Adapter

CSV support is representation-level only in v0.1.x. The adapter loads rows as
`list[dict[str, str]]`, treats all values as strings, and the CLI traces the
loaded row dictionaries after optional column drops. ReTrace does not infer
numeric types or semantic column meaning.

```bash
python -m retrace trace-csv users.csv
python -m retrace trace-csv users.csv --drop-column debug_blob
python -m retrace trace-csv users.csv --drop-column debug_blob --json-report report.json
```

This mode does not perform financial/accounting invariant checks, Decimal
arithmetic, stable row-ID reconciliation, scrap partitioning, or semantic
column detection.

## Intended Use

Good fits:

- locating unexpected representation shrinkage
- finding field or column drops
- spotting simple schema narrowing
- measuring declared transforms such as pruning or lossy export
- producing reproducible audit-support traces

Bad claims:

- proves anonymization
- proves privacy
- proves semantic information loss
- proves true data loss
- computes real Kolmogorov complexity

The honest claim is narrow: ReTrace can show where a deterministic
representation got smaller under a declared serializer and compressor.

## Limitations

- ReTrace does not compute true Kolmogorov complexity.
- ReTrace does not prove semantic information loss.
- ReTrace does not prove privacy or anonymization.
- zlib compressed size is only a practical complexity proxy.
- Small payloads can be noisy because compression overhead dominates.
- Canonical serialization matters; otherwise formatting changes can affect the
  measured byte length.
- Complexity gains are not treated as negative defects; they leave `defect` at
  zero for that step.

## Development

Run tests:

```bash
python -m pytest -q
```

The package has no runtime dependencies beyond Python's standard library.
