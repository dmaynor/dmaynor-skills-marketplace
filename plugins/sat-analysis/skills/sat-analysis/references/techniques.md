# SAT techniques

Use the technique that changes the assessment; omit steps with no analytic value.

Contents: [generation](#generate-distinguishable-explanations),
[ACH](#compare-evidence-with-ach), [sensitivity](#test-sensitivity-and-falsification),
[uncertainty](#express-likelihood-and-confidence), [decisions](#compare-actions-separately-from-causes).

## Generate distinguishable explanations

| Method | Useful prompt | Guard against |
|---|---|---|
| Causal decomposition | Which different mechanisms can produce this specific effect? | Confusing an initiating cause with a downstream symptom. |
| Inversion | What if the measurement, assumed intent, or stated scope is wrong? | Denying an established event merely to create a null. |
| Actor enumeration | Who has relevant access, incentives, or an authorized reason? | Treating opportunity or identity as proof of intent. |
| Dimensional decomposition | Which changes in environment, timing, load, or state change predictions? | Assuming these dimensions are independent. |
| Assumption challenge | Which plausible condition would invalidate the preferred explanation? | Choosing an uncomfortable story only for its dramatic effect. |

Use multiple methods when they yield distinct alternatives, not as an unconditional
quota. In a **requested hypothesis-saturation drill**, set the target and method count
in the exercise instructions. Generate broadly, then remove duplicates, scope vague
claims, and identify distinguishable predictions. Score training compliance separately
from analytic quality; more hypotheses do not establish a better answer.

Define the event, mechanism, scope, and necessary assumptions for each explanation.
Keep component hypotheses and combinations explicit. “A contributes” and “B
contributes” may both be true; “A alone” makes a different claim. A broad fallback
such as “some other cause” records model incompleteness but predicts little.

## Compare evidence with ACH

Assess each material observation against each hypothesis using the same scope.
Record ratings as analyst judgments, with an explanation for pivotal cells:

| Rating | Interpretation |
|---|---|
| `++` | Strong relative support under stated assumptions; explain why rival explanations predict it less well. |
| `+` | Some relative support; mere compatibility does not suffice. |
| `N` | Evaluated and nondiscriminating, irrelevant, or equally compatible within this comparison. |
| `-` | Tension with an expected prediction; not necessarily exclusion. |
| `--` | Strong contradiction under stated scope and measurement assumptions; justify any exclusion separately. |
| Missing | Not evaluated or insufficient basis to rate; retain as missing, never silently zero. |

Diagnosticity depends on alternatives. An observation compatible with all columns
may establish an event while doing little to distinguish its cause. Recheck the
interpretation of evidence that drives the assessment.
[Heuer, chapter 8](https://www.cia.gov/resources/csi/static/Pyschology-of-Intelligence-Analysis.pdf)

The helper maps symbols to descriptive values `2, 1, 0, -1, -2`. Do not convert
their sums, variance, or contradiction counts into probabilities, certainty, or an
automatic causal winner. One verified contradiction of a necessary prediction
matters differently from several weakly compatible observations. An untestable
hypothesis does not win by avoiding contradictions.

Inspect source identity before counting evidence. Exact derivative copies of one
established observation do not create corroboration. Different measurements of one
business event can have different origins; do not merge them merely by order or
incident ID. Distinct observations can share a collector, clock, parser, or author;
these dependencies matter even when records are not duplicates. Unknown dependence
is a limitation.

## Test sensitivity and falsification

Vary the evidence or assumption that could plausibly change the conclusion:

- Remove a pivotal observation, then an entire established dependency group.
- Reassess a disputed rating or the meaning of a key field.
- Check the assumption behind the best explanation and its strongest competitor.
- Report loss of discrimination, including a unique heuristic leader becoming tied.

State what was varied and what remained unchanged. Do not call a conclusion robust
because one row removal leaves a numerical order intact. Preserve the helper's
`insufficient_evidence`, `incomplete`, `underdetermined`, or `differentiated` result as
a description of its inputs; a differentiated score still requires causal reasoning.

Falsification requires a verified observation inconsistent with a necessary
prediction. A failed search supports exclusion only within its collection coverage.
For noisy or probabilistic predictions, explain how the result changes relative
support; do not claim logical disproof. Use the measurement-check reference for
independence, clocks, detection opportunity, and combined-cause traps.

## Express likelihood and confidence

Use a consistent declared likelihood vocabulary. If no customer vocabulary is given,
these terms and approximate bands come from
[ICD 203, D.6.e.(2)](https://archive.dni.gov/files/documents/ICD/ICD-203.pdf):

| Likelihood term | Approximate probability band |
|---|---|
| Almost no chance | 1–5% |
| Very unlikely | 5–20% |
| Unlikely | 20–45% |
| Roughly even chance | 45–55% |
| Likely | 55–80% |
| Very likely | 80–95% |
| Almost certain | 95–99% |

These published bands communicate meaning; they are not numerical measurements or
strict interval-validation bins. A number is optional in this adapted skill. If
quantifying, label a subjective estimate as such and state its scope and basis.
Use confidence separately to describe source quality, coverage, reasoning, and
dependence on assumptions. Unknown reliability remains unknown.

For exclusive and exhaustive alternatives, quantified point probabilities must sum
to one; exclusive nonexhaustive sets may sum to less. For overlapping propositions,
there is no arbitrary total band. Do not invent missing estimates or redistribute
beliefs to pass validation. The general conjunction rule is
`P(A ∩ B) = P(A) × P(B | A)` for `P(A) > 0`; use `P(A) × P(B)` only with independence.
Always `P(A ∩ B) ≤ min(P(A), P(B))`.

## Compare actions separately from causes

Use a weighted option matrix only when criteria and weights represent the decision
maker's actual priorities. Label weights as preferences, apply consistent units,
and test plausible weight changes. A preferred action need not depend on the most
likely cause; it may preserve acceptable outcomes across unresolved alternatives.

Record immediate feasibility, the assumption that forces a different action, and
what measurable capability the action improves. Expose burden, alternate capacity,
reversibility, and triggers before a delayed adverse outcome. Stop adding analysis
when it cannot change the bounded decision within its deadline; preserve unresolved
questions for a named later check rather than disguising them as certainty.
