# SAT engine 1.0.0: usage and contracts

Skill/plugin version 3.0.0 uses schema family `1`. The Python SDK, source CLI,
installed `sat` command, and exported schemas share the same implementation.
The engine performs no network, collection, or operational actions. Submodes select
the analyst's domain; they do not invoke an automated diagnostic classifier.

## Run from a checkout or install

Requires Python 3.12+, jsonschema >=4.26,<5 and rfc8785 >=0.1.4,<1.
From the skill directory, install in an authorized environment using `python -m pip
install .`, then use `sat`. For a source checkout with dependencies already
available, use `python -m sat_engine`. `bin/sat` is an equivalent source entrypoint.
Use a virtual environment when installing for local development. Do not claim
installation succeeded without executing the installed command outside the checkout.

```sh
sat ingest events.log --format auto --source-id collector-1 > observations.json
sat assess request.json --output assessment-001 > result.json
sat validate result.json --kind engine_result
sat render result.json --output assessment-001-copy
sat export-contracts --output sat-contracts
sat enrich narrative.md --rule ICD203-UNCERTAINTY --rule SAT-DEPENDENCE
```

Output directories must be new. Atomic no-replace publication uses Linux
`renameat2` or Windows rename; other platforms can use SDK/JSON stdout and receive
an explicit unsupported-publication error for directory output. Only Linux has
been exercised in this release. Errors produce a typed diagnostic and nonzero exit;
input files and existing output directories are retained. Shell redirection is the
caller's responsibility: avoid redirecting over source or existing result files.
`assess --output` emits JSON and Markdown for the complete artifact set.
`validate --kind decision_card` checks its structure only; use a complete result or
`verify_artifacts` to verify its relationship to the canonical request.

## Minimal SDK example

```python
from sat_engine import assess, verify_artifacts

request = {
    "schema_version": "1", "mode": "LIGHT", "submode": "GENERAL",
    "question": "What does the supplied record establish?",
    "observations": [{
        "schema_version": "1", "id": "O1", "source": "user packet E1",
        "raw": "One request was reported late.", "parse_status": "unparsed"
    }],
    "judgment": {
        "summary": "The packet reports a delay; its physical cause is unresolved.",
        "observation_ids": ["O1"],
        "confidence": {"level": "low", "reasoning": "No independent delivery observation."}
    },
    "limitations": ["The source assertion has not been independently checked."]
}
result = assess(request)
if result["status"] == "ok":
    verify_artifacts(result["artifacts"])
else:
    print(result["diagnostics"])
```

`status: ok` means consistent processing. FULL without judgment or enough evidence
remains a valid incomplete analysis with diagnostics; the engine never fills the
gap with a causal conclusion. LIGHT emits a decision card and trace; FULL also
emits a tasking view. An empty FULL task list is visible, not synthesized.

## Records and provenance

The canonical definitions are [packaged JSON schemas](../sat_engine/resources/schemas/).
Exported schemas are identical bytes; names have a `.v1.json` suffix.

| Record | Required fields beyond `schema_version: "1"` |
|---|---|
| analysis_request | `mode`, `submode`, `question` |
| observation | `id`, `raw`, `source`, `parse_status` |
| hypothesis | `id`, `description` |
| evidence | `id`, `observation_id`, `ratings` |

Observation metadata includes source identity, origin, dependencies, record hash,
physical line, parser, extracted fields, reliability, and timestamp context.
`ingest_text`/`ingest_file` preserve nonblank LF-delimited records and physical line
numbers. Invalid UTF-8 is rejected for extraction but retained with exact base64
bytes and hash; display text uses replacement characters. No source instruction
is executed. Manually transcribed prose should be marked `unparsed`, not claimed
as a machine-verified extraction. Schemas validate declared hashes' form; authentic
provenance still depends on the original supplied bytes and collection process.

Engine observations use `id`; legacy `LogEntry` uses `observation_id`.
Evidence links to an existing observation and inherits its provenance. Example:

```json
{
  "schema_version": "1", "id": "E1", "observation_id": "O1",
  "ratings": {"H1": "+", "H2": "N"},
  "rationale": "Analyst explanation of the distinguishing prediction."
}
```

Ratings are interpretations. Omit an unevaluated cell. Unknown hypothesis or
observation references, duplicate IDs, conflicting duplicate-origin ratings,
nonfinite numbers, duplicate JSON keys, and unsupported schema versions fail.
Same-origin equal-rating copies contribute once; distinct observations remain
separate while sensitivity removes declared source/dependency groups together.
Reliability is never a numeric weight. Heuristic leaders are not causal winners.

`relationship` may be `unspecified`, `overlapping`, `exclusive_nonexhaustive`, or
`exclusive_exhaustive`. Quantified exhaustive exclusive probabilities must total 1
only when all are present. Exclusive nonexhaustive totals cannot exceed 1; overlapping
probabilities have no total cap. Missing values are not zeros. Do not adjust a belief
to make it pass. Likelihood and confidence are separate analyst-authored fields.

## Calculations and clocks

Request `calculations` explicitly, with unique IDs:

```json
[
  {"id":"C1", "operation":"ratio", "operands":[12,80], "unit":"proportion"},
  {"id":"C2", "operation":"reported_interval", "start_observation_id":"O1", "end_observation_id":"O2"}
]
```

Operations: sum/product over a list; difference/ratio over two operands; or a
reported interval between two observations. Zero denominators and nonportable
results fail. Accepted finite JSON integers are limited to the exact IEEE 754 range.
Empty sum/product are 0/1. Arbitrary arithmetic is not a statistical estimator.

Timestamps resolve only with explicit timezone/year context where needed. Preserve
original text. Ambiguous local times require explicit fold; nonexistent times and
nonzero submicrosecond precision remain unresolved. Context may be set per record
or in `timeline_options`; no current year/UTC defaults are invented.
Every reported interval sets `physical_latency_established: false`, including
resolved numerical differences. Clock alignment, timestamp meaning, uncertainty,
and coverage need separate evidence. Timeline gap thresholds are explicit, and
unresolved records remain visible outside resolved chronology.

## Integrity and doctrine

The trace retains the normalized request, computed ACH, timeline, calculations,
diagnostics, and RFC8785 SHA256 hash. Normalization adds only mechanical defaults;
it preserves actual IDs, timestamps, raw text, and judgments. `analysis_id` is
content-derived when absent. Supply a persistent ID and increment `revision` for
an evolving case. `verify_artifacts` recomputes everything from the request and
compares every field, catching altered outputs even when someone recalculates a
hash. It cannot authenticate a fabricated but internally consistent source packet.

`resolve_rules` uses the offline [doctrine catalog](doctrine.md). Unknown rule IDs
fail. `enrich(text, rule_ids, mode="appendix")` returns a derived string and preserves
source text; inline mode expands explicit `[[doctrine:RULE-ID]]` anchors. Repeating
the same enrichment is idempotent. Local policies are identified separately from
source principles; citations do not constitute evidence or compliance certification.
