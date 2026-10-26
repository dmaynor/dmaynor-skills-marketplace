# sat2 machine interface

Invocation is a skill prompt, not a standalone execution API. Pass one JSON object.
Input schema is sat2.input.v1. claim is a non-empty string. Optional mode is one of
BREACH_DETECTION, CRASH_ANALYSIS, FIX_VERIFICATION, STATEMENT_ANALYSIS,
GENERAL_HYPOTHESIS. observations, evidence, prior_findings are string arrays;
output_format is human/json/both; budget_tokens is a positive integer.
Unknown fields are ignored; invalid types, enums, schema or malformed JSON produce
only {"schema":"sat2.output.v1","error":{"code":"bad_input","message":"reason"}}.

All successful outputs require schema=sat2.output.v1, claim, mode, result_kind,
gate={passed:boolean,note:string}, and completion={condition:string,
discriminated:boolean,remaining_tests:string[],statement:string}.

## Direct result

Use result_kind=direct, gate.passed=false, direct_result={result:string,source:string},
completion.condition=direct, discriminated=true and remaining_tests=[].
Do not emit hypotheses. This branch requires an observed decisive result.

## Full analysis

Use result_kind=analysis and gate.passed=true with non-empty conditions drawn from
competition/adversarial_surface/downstream_action. Require:

- hypotheses: >=5 objects with unique id, text, category, prior in [0,1], prior_basis,
  falsified_by. Include obvious, null and uncomfortable categories. Label subjective
  prior bases explicitly; document measured anchors when available.
- discriminating_tests: non-empty ordered array. Each has unique id, action,
  discriminates (>=2 distinct existing hypothesis IDs), order (1-based), exit_condition.
  Put the cheapest top-two discriminating test first.
- assessment: conclusion, confidence_term, confidence_range=[lower,upper] in [0,1], basis.
- assumptions and limitations: non-empty string arrays.
- ach: included:boolean, reason:string; when included, trigger must be explicit_request,
  planned_evidence_round or programmatic_scores_requested. JSON alone is not a trigger.

Completion a requires discriminated=true and no remaining tests. All other analysis
states require discriminated=false and non-empty remaining_tests referencing test IDs.
Condition b additionally requires owner and queue_evidence on every remaining test.
Condition c requires budget_exhaustion_source quoting the caller's declaration.
Otherwise use unresolved. Describing a proposed test does not establish queue state.

## Consumption

Validate with scripts/validate_output.py before consumption. Structural validity is
not evidence that claims are true. In both mode parse the sat2_output_v1 fence;
in json mode require a single JSON object without surrounding prose.
Return complete documents on refinement. Never treat next actions as authorization.
Default maximum 3 rounds; stop on no new evidence, denied access, caller exhaustion,
or resolution. No automatic execution or unbounded recursion. Human summaries may
be at most 150 words in both mode. Error documents contain only schema and error.
