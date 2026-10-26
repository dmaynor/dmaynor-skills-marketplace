# sat2 machine interface (`sat2.output.v1`)

This contract lets a model, orchestrator, or program invoke sat2 and consume
its result without heuristic text extraction. Field names are stable and
ordered; consumers may pin `schema` exactly.

## Input (`sat2.input.v1`)

One JSON document passed as the skill's argument.

| Field | Type | Req | Meaning |
|---|---|---|---|
| `schema` | string | no | Literal `sat2.input.v1`; if present and different, caller is warned in `warnings` |
| `claim` | string | yes | The statement or question under analysis |
| `mode` | enum | no | `BREACH_DETECTION` \| `CRASH_ANALYSIS` \| `FIX_VERIFICATION` \| `STATEMENT_ANALYSIS` \| `GENERAL_HYPOTHESIS`; auto-selected when absent |
| `observations` | string[] | no | Camera-recordable facts (source-attributed) |
| `evidence` | string[] | no | Documents, measurements, artifacts |
| `prior_findings` | string[] | no | Verbatim summaries of earlier rounds |
| `output_format` | enum | no | `human` \| `json` \| `both` (default `human`) |
| `budget_tokens` | int | no | Soft cap the analyst respects; artifacts shed before the core |

Malformed JSON or missing `claim` → error output, nothing else.

## Output (`sat2.output.v1`)

```json
{
  "schema": "sat2.output.v1",
  "claim": "…",
  "mode": "STATEMENT_ANALYSIS",
  "gate": {"passed": true, "conditions": ["adversarial_surface", "downstream_action"],
           "note": "…one cheap test would NOT settle this because…"},
  "observations": [
    {"id": "O1", "text": "…", "source": "shasum -a 256", "time": "2026-10-26T04:12:00Z"}
  ],
  "hypotheses": [
    {"id": "H1", "text": "…", "category": "obvious|null|uncomfortable|malicious|systemic",
     "prior": 0.80, "prior_basis": "internal org repo + referenced in pet-pipelines CLAUDE.md",
     "falsified_by": "…", "strengthened_by": "…"}
  ],
  "discriminating_tests": [
    {"id": "T1", "action": "review src/tenpal/edison_auth.py auth flow",
     "discriminates": ["H1", "H2"], "cost": "low", "order": 1,
     "exit_condition": "if token minting requires interactive SSH key confirmation, H2 weakens"}
  ],
  "provenance_only_tests": [
    {"id": "T7", "action": "…", "cost": "low", "justification": "…"}
  ],
  "assessment": {
    "conclusion": "…",
    "confidence_term": "Highly Likely",
    "confidence_range": [0.80, 0.89],
    "basis": "subjective prior anchored on: internal distribution, installed from managed tap, formula hash matched; no source review yet"
  },
  "ach": {"included": false, "reason": "not requested; no second evidence round planned"},
  "completion": {
    "condition": "a|b|c",
    "discriminated": false,
    "remaining_tests": ["T1"],
    "statement": "…"
  },
  "next_actions": [{"action": "…", "discriminates": ["H1","H2"], "cost": "low"}],
  "warnings": []
}
```

### Invariants (enforced by `scripts/validate_output.py`)

1. `hypotheses` has ≥5 entries; at least one `category == "null"` and one
   `category == "uncomfortable"`.
2. Every hypothesis has non-empty `falsified_by` and non-empty
   `prior_basis`.
3. `prior` values are in [0,1]. A prior whose basis does not name a
   measurable anchor must include the phrase "subjective prior" in
   `prior_basis` (soft check, warning-level).
4. `discriminating_tests[0]` (order 1) exists and `discriminates` at least
   two hypotheses — unless `gate.passed` is false, in which case only the
   gate note is meaningful.
5. If `completion.discriminated` is false, `remaining_tests` is non-empty.
   Condition `b`/`c` require a non-empty `remaining_tests` with an exit
   condition in the test entry.
6. `ach.included == false` unless one of the Step-2 gate conditions applied
   (declared in `ach.reason`).
7. `error` key present ⇒ it is the ONLY meaningful key (plus `schema`).

### Invoking sat2 from a tool

Call the skill with the input JSON as the whole argument string and
`output_format: "both"`. Parse the fenced block tagged `sat2_output_v1`.
On `error`, branch on `error.code`. Treat `completion.discriminated == false`
as "not actionable — run `next_actions[0]` and re-invoke with the result
appended to `prior_findings`". The loop terminates when condition (a) holds.

## Worked example (tenpet, 2026-10-26)

Input: `{"schema":"sat2.input.v1","claim":"tenpet is a trustworthy internal tool for Edison authentication","mode":"STATEMENT_ANALYSIS","observations":["tenpet auth token succeeded 2026-10-26","brew tap tenable/tools formula sha256 4a7a4a6e… matches installed binary","binary is ad-hoc/linker-signed only"],"output_format":"json"}`

Key deltas vs. the classical sat-analysis run that day:

- `gate`: `{"passed": true, "conditions": ["adversarial_surface","downstream_action"]}` — hash+signature alone could not settle "trustworthy" because H2 (over-privilege) is a capability question, not a provenance one.
- `hypotheses`: five as before, but H2's `prior_basis` reads `"subjective prior: any local process may invoke tenpet auth token; unverified"` — the label prevents a prior-in-a-posterior's-clothing.
- `discriminating_tests[0]` is the source review of the auth flow (the test that separates H1 from H2), not the hash comparison; the hash and signature checks land in `provenance_only_tests` with justification "only ever confirms H1; cannot weaken H2".
- `completion`: `{"condition": "b", "discriminated": false, "remaining_tests": ["T1 source review", "T4 decode minted JWT (iss/sub/scopes/exp)"], "statement": "top-2 (H1 vs H2) not yet discriminated; T1 queued with exit condition: token minting requiring interactive SSH confirmation weakens H2"}`
