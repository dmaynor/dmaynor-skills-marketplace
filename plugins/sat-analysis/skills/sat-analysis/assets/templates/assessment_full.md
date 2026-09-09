# SAT assessment: {{TITLE}}

<!-- Adapt to the user's format. Remove unused sections and placeholders; do not
     invent content to complete a form. Use VERSION for release metadata. -->

**Question and scope:** {{PROPOSITION_OR_DECISION_ASSET_AND_TIME_WINDOW}}
**Domain:** {{DOMAIN}}
**Decision deadline:** {{DEADLINE_OR_NOT_APPLICABLE}}
**Evidence cutoff:** {{CUTOFF}}

## Judgment and action

{{MAIN_JUDGMENT_SUPPORTED_BY_IDENTIFIED_EVIDENCE_WITH_ALTERNATIVES_AND_LIMITS}}

**Proposition likelihood:** {{QUALITATIVE_TERM_OR_UNQUANTIFIED_WITH_BASIS}}
<!-- A numeric likelihood is optional. If used, state its scope, horizon,
     vocabulary and basis; label a subjective estimate explicitly. -->

**Confidence in the judgment's basis:** {{LEVEL_OR_DESCRIPTION_AND_REASONS}}

{{BOUNDED_RECOMMENDATION_WITH_OWNER_DEADLINE_AND_CHANGE_TRIGGER}}

## Evidence and provenance

| Source | Location/record IDs | Coverage and quality | Origin/shared dependencies |
|---|---|---|---|
| {{SOURCE}} | {{LOCATOR}} | {{LIMITS}} | {{KNOWN_DEPENDENCIES_OR_UNKNOWN}} |

| Evidence ID | Source assertion or extracted observation | Source location | Time meaning and uncertainty |
|---|---|---|---|
| {{SOURCE_QUALIFIED_ID}} | {{EXACT_SCOPE_OF_OBSERVATION}} | {{LOCATOR}} | {{CLOCK_SEMANTICS_OR_UNRESOLVED}} |

**Extraction:** {{METHOD_AND_TOTAL_PARSED_UNPARSED_REJECTED_COUNTS_IF_APPLICABLE}}
**Independent corroboration:** {{WHAT_IS_INDEPENDENT_AND_WHAT_IS_DERIVATIVE}}
**Material gaps:** {{MISSING_COVERAGE_FIELDS_RECORDS_OR_CONTEXT}}

## Explanations

**Relationship:** {{UNSPECIFIED_EXCLUSIVE_EXHAUSTIVE_EXCLUSIVE_NONEXHAUSTIVE_OR_OVERLAPPING}}
**Generation approach:** {{METHODS_THAT_ADDED_DISTINCT_EXPLANATIONS}}

| ID | Mechanism and scope | Necessary assumptions | Distinguishing prediction |
|---|---|---|---|
| {{HYPOTHESIS_ID}} | {{EXPLANATION}} | {{ASSUMPTIONS}} | {{PREDICTION_AND_LIMITS}} |

{{RELEVANT_BASELINE_ASSUMPTION_CHALLENGE_AND_COMBINED_CAUSE_RELATIONSHIPS}}
<!-- Add only materially distinct hypotheses. Do not impose a fixed count.
     Optional probabilities apply to the defined propositions, not category labels. -->

## Evidence comparison

<!-- Add hypothesis columns as needed. Symbols: ++ strong relative support,
     + relative support, N evaluated/nondiscriminating, - tension, -- strong
     contradiction. Leave missing ratings explicit. All ratings are judgments. -->

| Evidence ID | {{HYPOTHESIS_ID}} | Rating rationale and validity assumptions |
|---|---|---|
| {{EVIDENCE_ID}} | {{RATING_OR_MISSING}} | {{WHY_IT_DISTINGUISHES_OR_DOES_NOT}} |

**Decisive comparison:** {{DISCRIMINATING_EVIDENCE_AND_STRONGEST_COUNTEREVIDENCE}}
**Unresolved alternatives:** {{WHAT_REMAINS_POSSIBLE_AND_WHY}}
**Sensitivity:** {{PIVOTAL_ITEM_AND_DEPENDENCY_GROUP_OR_ASSUMPTION_CHANGES_AND_EFFECT}}
<!-- If helper output is used, report its status and caveats. Descriptive scores
     and heuristic leaders are not causal winners or probability estimates. -->

## Assumptions and evidence that would change the judgment

| Assumption | Why it matters | Result if false | How it could be checked |
|---|---|---|---|
| {{ASSUMPTION}} | {{DEPENDENT_JUDGMENT}} | {{CONSEQUENCE}} | {{CHECK_OR_LIMIT}} |

| Hypothesis | Contrary observation | Necessary prediction or probabilistic expectation? | Validity and detection requirements |
|---|---|---|---|
| {{H_ID}} | {{OBSERVATION_OR_NO_AVAILABLE_TEST}} | {{TYPE_AND_SCOPE}} | {{REQUIREMENTS}} |

## Next evidence checks

| Check/owner/time | Measured event and coverage | Competing predictions | Validity assumptions | Decision consequence and inconclusive result |
|---|---|---|---|---|
| {{CHECK}} | {{TARGET_AND_OPPORTUNITY}} | {{RESULTS_BY_HYPOTHESIS}} | {{CLOCK_SOURCE_ACCESS_LIMITS}} | {{BOUNDED_UPDATE}} |

## Operational decision

| Action/owner | Feasibility now and under forecast demand | Burden and failure mode | Fallback/reversibility | Observable trigger and deadline |
|---|---|---|---|---|
| {{ACTION}} | {{CAPACITY_AND_ASSUMPTIONS}} | {{BURDEN_AND_RISK}} | {{ALTERNATIVE}} | {{EARLY_TRIGGER}} |

**Alternative becomes preferable when:** {{CONDITION}}
**Residual limits:** {{WHAT_THIS_ANALYSIS_AND_ACTION_DO_NOT_ESTABLISH}}
**Change from prior judgment, if applicable:** {{NEW_EVIDENCE_OR_REVISED_REASONING}}
