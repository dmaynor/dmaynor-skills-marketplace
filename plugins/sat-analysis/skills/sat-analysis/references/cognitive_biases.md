# Bias checks that change the analysis

Use these checks on consequential judgments, not as a mandatory output checklist.
Do not infer bias from disagreement, a particular phrase, or an undesired conclusion.

| Risk | Diagnostic question | Corrective action |
|---|---|---|
| Confirmation and anchoring | Would the same evidence receive the same rating if another hypothesis came first? | Compare plausible alternatives before committing; revisit pivotal ratings after counterevidence. |
| Layering | Did a prior report's inference become a fact in this assessment? | Trace the claim to its original record; keep inherited assumptions and missing sources explicit. |
| Source repetition | Do several reports depend on one observation or measurement chain? | Record the origin and shared dependencies; test removing the group. |
| Availability and vividness | Does a memorable incident explain the base rate or only suggest a mechanism? | Use relevant reference classes when available; do not invent a prevalence estimate. |
| Source prestige or distrust | What access and measurement process produced this item? | Evaluate reliability and content together without accepting or discarding it solely by reputation. |
| Mirror imaging | Is an actor's supposed motive necessary to the mechanism? | Separate capability, observed behavior, and inferred intent; test a plausible different incentive. |
| Clientism or conformity | Which material fact or consequence would the audience prefer omitted? | State it with its evidence limits; use independent initial judgments before team convergence. |
| Missingness | Would the collection process reliably show the event if it occurred? | Bound negative evidence by coverage, retention, parsing, and detection opportunity. |
| Hindsight | What was actually knowable at the original decision time? | Preserve contemporaneous evidence and predictions; assess decision quality using that information. |
| Overprecision | What distinguishes this probability from a nearby estimate? | State the basis, widen or remove unsupported precision, and keep confidence separate. |
| Structure-induced authority | Is the conclusion persuasive because the table looks complete? | Inspect discriminating evidence and decisions; headings, scores, and hashes do not validate reasoning. |
| Reflexive abstention | Is uncertainty being used to avoid a justified bounded decision? | State what can be decided now and the conditions that would change it. |

## Probability traps

**Conjunction.** A detailed narrative cannot be more probable than one of its
necessary components: `P(A ∩ B) ≤ min(P(A), P(B))`. The general multiplication rule
is `P(A ∩ B) = P(A) × P(B | A)` when `P(A) > 0`. Multiplying marginal probabilities
requires independence. Narrative simplicity alone does not establish higher
probability; evaluate how the available evidence bears on each component.

**Base rates.** Use a reference class only if its population, ascertainment,
environment, and time window fit the current question. A selected incident queue
has different prevalence from all operating systems. Unknown prevalence is not
permission to invent a prior or ignore strong discriminating evidence.

**Overlapping causes.** A parser error can coexist with a real incident. A working
fix can introduce an unrelated regression. Do not force contributing mechanisms
into a single exclusive list or a total of 100% without changing their definitions.

**Confidence.** More information can increase conviction without increasing
accuracy. Record source independence and diagnosticity instead of adding fixed
percentage bonuses. Demonstrate calibration with predictions and resolved outcomes,
not with verbal labels or narrow numerical ranges.

## Focus the challenge

Pick the most consequential hidden assumption. State what breaks if it is wrong
and what observation would reveal that failure. For high-consequence decisions,
briefly assume the recommendation fails and identify the mechanism, operator burden,
or unverified capacity that would explain it. Prefer a modification that bounds the
harm over an additional generic caveat.
