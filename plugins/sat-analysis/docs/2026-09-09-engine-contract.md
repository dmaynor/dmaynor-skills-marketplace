# SAT engine implementation contract

This contract governs the authorized engine redesign on `feat/sat-engine-redesign`.
The May design supplies architecture and scope, not its disproven scoring rules.
Preserve the corrected helper invariants in `references/data_contract.md`; the
old document's exclusion of an SDK describes the earlier release only.

## Scope and versions

- Engine `1.0.0`; schema family `1`; skill/plugin `3.0.0` (the separately installed
  helper-only skill already used 2.0.0). Do not present version numbers as accuracy evidence.
- Importable Python 3.12+ `sat_engine`, unified CLI, nine original domain schemas,
  analysis-request and engine-result schemas, doctrine data, three projections,
  LIGHT plus five FULL domains, compatibility wrappers and portable fixtures.
- No mobile UI, server, database, background automation, or model/network calls
  inside the engine. Analyst/model inputs remain explicit inputs.
- Accuracy comparisons and architecture acceptance are separate outcomes.

## Resource and module ownership

Canonical JSON contracts live in `sat_engine/resources/schemas/*.v1.json` and the
catalog in `sat_engine/resources/doctrine/catalog.v1.json`. Package these resources
in the wheel. `sat export-contracts` exports byte-identical portable `schemas/`
and `doctrine/` directories; there is no second handwritten source of truth.

Modules: `models`, `validators`, `parsers`, `timeline`, `ach`, `doctrine`, `enrich`,
`rendering`, `pipeline`, `cli`, plus `__init__` and `__main__`.

`validators` owns:
- `ValidationFailure(code, message, path="$", remediation="")`, a ValueError
  exposing `.diagnostic()` -> {code,path,message,severity:"error",remediation}.
- `load_schema(kind)`; `validate(kind, value)` (raise, never silently repair).
- `loads_json(text)` rejects duplicate keys and nonfinite constants.
- `canonical_bytes(value)` uses RFC 8785; `content_hash(value)` is SHA-256 of it.
  Reject nonportable numbers/unpaired Unicode. Invalid original bytes belong in
  base64 fields, not non-Unicode strings. Validation never fetches remote refs.

## Common record shapes

All schema kinds have schema_version:"1"; fields listed as optional below remain
optional at the input boundary. Unknown fields are rejected in semantic records;
raw observations preserve unfamiliar source content in raw text/bytes.

Observation: required `schema_version,id,raw,source,parse_status`.
Preserve optional original LogEntry fields (timestamp, host, process, pid, user,
src_ip,dst_ip,src_port,dst_port,action,status,message,tags), source_id,line_number,
record_sha256,raw_bytes_base64,parse_error,parser,address_mentions,origin_id,
dependency_groups,timestamp_semantics,clock_domain,timestamp_uncertainty_seconds,
timestamp_context. Replace legacy observation_id with id at the engine boundary.
Add reliability (A|B|C|D|E|F|unknown, default unknown) and reliability_reason.
Unknown year/zone/clock bounds stay unknown. Rejected records survive ingestion.

Hypothesis: schema_version,id,description; optional category (string),
initial_probability (finite [0,1] or null), falsifier (string or null).
Falsifiers and numeric estimates are not mandatory forms to fill with fiction.

Evidence: schema_version,id,observation_id,ratings; optional rationale (string).
ratings maps known hypothesis IDs to ++,+,N,-,--. Missing is not N. Source,
reliability, origin and dependencies are inherited from the referenced observation,
not independently repeated assertions that can disagree with it.

Judgment: summary (nonempty string); optional selected_hypothesis_ids and
observation_ids (arrays of existing IDs), likelihood, confidence, implications.
Likelihood: proposition (nonempty), value (finite [0,1] or null), basis (nonempty),
optional term and horizon (strings). Confidence: level (low|moderate|high|unassessed),
reasoning (nonempty). Implications: array of strings. Judgment may be null.
The engine never manufactures a causal judgment or likelihood from scores.

Task: id,action (nonempty strings); optional owner,trigger (strings),
observation_ids,hypothesis_ids (arrays of existing IDs). Missing owner is visibly
unassigned, never an invented person or an automatic external action.

Calculation: id,operation. For sum/difference/product/ratio, operands is an array
of finite numbers (difference and ratio require exactly two). Optional unit.
reported_interval uses start_observation_id,end_observation_id instead of operands;
it returns seconds between resolved reported clocks with clock/semantics caveats,
not a physical-delivery claim. Unknown endpoints return unresolved, not zero.
Results include id,operation,value (number|null),unit,status,caveats.

## Analysis request

Required: schema_version,mode (LIGHT|FULL),submode
(BREACH|CRASH|FIX|STATEMENT|GENERAL),question (nonempty).
Optional: analysis_id (nonempty), revision (integer >=1, default1),
observations[],hypotheses[],evidence[],relationship
(unspecified|exclusive_exhaustive|exclusive_nonexhaustive|overlapping),
judgment (object|null), assumptions[],limitations[] (strings),tasks[],rule_ids[],
calculations[],timeline_options.
timeline_options: gap_threshold_seconds=300,rapid_threshold_seconds=1 (nonnegative
finite), optional default_year,default_timezone,fold (0|1).
Default empty arrays, unspecified relationship, and null judgment are explicit
normalization, not invented analysis. LIGHT cannot contain evidence ratings;
FULL may be incomplete and still produce a qualified artifact.
When absent, analysis_id is derived deterministically from the canonical input;
revision is caller managed. Inputs are deep-copied, never mutated.

## Computation and cross-record validation

Unique nonempty record IDs; all ratings, evidence references, selected hypotheses,
task references and interval endpoints must resolve. Same-origin rating conflicts
fail. Distinct independent observations about one business event remain distinct.
Only fully quantified exclusive/exhaustive hypothesis sets must total1 (1e-9
floating tolerance); exclusive/nonexhaustive totals <=1; overlap has no sum cap.
Reliability F/unknown remains unknown, never a numeric multiplier or confidence cap.
Source, origin and declared dependency groups participate in sensitivity.

`ach.compute_matrix(request)` returns schema-shaped ach_matrix with title,
relationship,hypotheses,evidence (engine records), assessment,sensitivity,
diagnosticity. It can adapt the corrected ACHMatrix internally. status is one of
insufficient_evidence,incomplete,underdetermined,differentiated; winner always null.
Scores/variance are descriptive. The selected_hypothesis_ids in analyst judgment
are not a computed winner. Do not reject a justified analyst conclusion merely
because heuristic totals disagree; expose the distinction.

`parsers.ingest_file(path, log_format="auto", **context)` returns an observation
list; `ingest_text(text, source="inline", source_id=None, log_format="auto",
**context)` also exists for portable tests and SDK callers. Keep legacy entrypoints
as compatibility wrappers. Every nonblank physical record, including invalid UTF8,
survives. Use replacement Unicode for its display raw field plus original bytes
in raw_bytes_base64; original byte hash must still match.

`timeline.build_timeline(observations, **timeline_options)` returns schema-shaped
timeline: schema_version,events,analysis,gap_threshold_seconds,rapid_threshold_seconds.
Retain original timestamps, unresolved context and source provenance. Allow
caller thresholds (including fractional seconds); no event timestamp normalization
in conformance fixtures. All reported intervals include physical_latency_established:false.

## Canonical snapshot and artifacts

`pipeline.assess(request)` -> EngineResult. Success: schema_version:"1",
engine_version:"1.0.0",status:"ok",diagnostics (warning/error records),artifacts.
Failure: status:"invalid",diagnostics,artifacts:null. Original supplied input/files
are untouched. Unknown evidence is not an invalid request.

Artifacts is {decision_card,analytic_trace,tasking_view}; LIGHT tasking_view=null.
Analytic trace: schema_version,engine_version,analysis_id,revision,request (normalized
analyst inputs),ach_matrix (null LIGHT),timeline,calculations,diagnostics,content_hash.
Compute hash over this complete trace without content_hash. No generated current
time is needed. `rendering.project(trace)` derives card/tasking, with the same
analysis_id,revision,content_hash; no independently authored duplicated judgments.

Decision card: schema_version,analysis_id,revision,content_hash,question,summary,
likelihood,confidence,implications,assessment_status,limitations,calculations.
Absent judgment -> explicit "No analyst judgment supplied."; likelihood/confidence
remain null. assessment_status is not_evaluated in LIGHT, otherwise matrix status.
Tasking view: schema_version,analysis_id,revision,content_hash,tasks,limitations.
Do not silently drop unresolved evidence/assumptions from the analytic trace.

`rendering.render_markdown(artifacts)` -> dict[str,str] with decision_card.md,
analytic_trace.md and FULL tasking_view.md. Use canonical computed fields, escape
untrusted Markdown/HTML, show diagnostics and review limits. Do not recompute
numbers in templates. `pipeline.verify_artifacts(artifacts)` recomputes the
analysis from trace.request and compares ALL projections and derived results;
hash equality alone is insufficient. Reject stale/contradictory/tampered output.

## Doctrine

Catalog: schema_version,catalog_version,rules[]. Rule fields: rule_id,title,summary,
standard,section,citation,url,severity (BLOCKING|WARNING|NOTE),implementation_policy
(boolean). Clearly distinguish engine adaptations from quotations of standards.
`doctrine.load_catalog()`; `resolve_rules(rule_ids,catalog=None)` return matched
rule objects, reject unknown IDs. No automatic network lookup.
`enrich.enrich(text, rule_ids, mode="appendix")` supports appendix and inline,
is idempotent, and returns a derived rendering without mutating canonical analysis.
Empty request rule_ids is allowed; default rules must not imply certified compliance.

## CLI, SDK, packaging and tests

Public imports: assess,verify_artifacts,ingest_file,ingest_text,validate,
ValidationFailure; engine __version__. python -m sat_engine and installed `sat`:
ingest,assess,validate,render,enrich,export-contracts. JSON stdout stays machine
readable; diagnostics use result JSON/stderr as appropriate. Error exit2. No
shell execution, model calls, or network actions derived from evidence.
File outputs are complete verified sets; refuse overwriting existing output
directories by default. Include schemas/catalogs in wheel and test clean install.

Retain the79 baseline regressions through wrappers or migrated equivalent tests.
Add integration tests for five FULL domains + LIGHT, independently reviewed golden
fixtures and refusal fixtures, exact RFC8785 vectors, forged-computation and stale
projection checks, source dependencies, invalid bytes, unknown clocks, and arithmetic.
Only nondeterministic run metadata may be normalized (not event times or hashes).
Portable fixtures are not proof of another platform's correctness until it runs them.
Preserve benchmark raw answers, case coverage, scoring and actual limitations.

## Acceptance mapping

ARCH-01 schemas/models; ARCH-02 provenance ingestion/timeline; ARCH-03 ACH semantics;
ARCH-04 canonical three-view output; ARCH-05 doctrine/enrichment; ARCH-06 SDK/CLI;
ARCH-07 thin skill LIGHT/FULL; ARCH-08 installed-package and portable contract tests;
ACC-01 preserved regressions; ACC-02 fresh blinded accuracy comparison.
Every item needs concrete files/tests and observed results before reporting complete.
