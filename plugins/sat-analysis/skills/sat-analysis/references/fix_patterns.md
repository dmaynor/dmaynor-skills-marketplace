# Fix verification

Define the original violated invariant, the supplied failure case, supported
versions/configurations, and the behavior the change is intended to preserve.
Trace how the change interrupts the causal path. Separate source review from
executed validation, and state which evidence supports each conclusion.

## Evaluate separate dimensions

| Dimension | Possible judgments | Required scope |
|---|---|---|
| Intended repair | Supported, partially supported, unsupported, contradicted | Which invariant, entry points, inputs, and environment were examined? |
| Mechanism | Removes cause, prevents exposure, bounds impact, suppresses symptom | Does the remedy change the faulty state or only its visible result? |
| Completeness | Covered paths established; other paths remain unresolved | What evidence supports coverage beyond the reported example? |
| Regression | Identified regression, tested compatible behavior, unassessed risk | Which existing contracts, resource limits, or callers can change? |
| Operational use | Feasible, conditional, infeasible under current constraints | Who deploys and operates it, with what fallback and burden? |

A repair can work for the original defect and introduce a regression. These are
not mutually exclusive hypotheses. Reserve “complete” for a defined scope backed
by adequate evidence; do not imply every possible future failure is excluded.

## Review mechanisms rather than patch appearance

| Pattern | Question that changes the assessment |
|---|---|
| Enforcement at the wrong boundary | Is the invariant enforced at an authoritative boundary reached by all relevant callers, or only by a cooperative client? |
| Incomplete path coverage | Which alternate entry points reach the same operation, and do they share the repaired invariant? Avoid expanding scope to unrelated code without evidence. |
| Integer or size handling | Are operand domains, signedness, conversions, overflow, and zero cases handled before unsafe arithmetic? A type change or post-overflow comparison is insufficient by itself. |
| Check/use gap | Does the checked object remain the same object at use? Could opening or probing it already cause a side effect before authorization? A handle check is not a universal race fix. |
| Representation mismatch | Do validation and consumption interpret the same representation, and can a later transformation change its meaning? Test only relevant formats and boundaries. |
| State/lifetime repair | Does every applicable state transition preserve the invariant, including exceptional and concurrent paths? |
| Error handling | Does failure leave a defined safe state, or hide the error while damaged state or an unsafe action persists? |
| Configuration/dependency assumption | Is the required behavior present in supported deployed configurations and actual dependency versions? |
| Regression | What existing capability or resource envelope changes as a consequence of this fix? |

Do not infer quality from patch length, “workaround” wording, the presence of new
tests, or an extra defensive layer. A small central fix can be sufficient. A
temporary mitigation can be appropriate when its limits and expiration are clear.
Additional checks can also create inconsistent policies or new failure states.

## Match validation to the remaining claim

1. Compare the reported failure before and after the change when execution is
   authorized and a suitable reproduction exists. Record the actual build and
   environment; a test that passes both versions may not demonstrate the repair.
2. Exercise boundary, error, and alternate-path behavior only where it bears on the
   repaired invariant or a concrete regression risk. Keep legitimate behavior in
   scope; rejection of the original bad case alone does not establish correctness.
3. For concurrent or intermittent failures, state what instrumentation and trial
   coverage establish. Failure to reproduce under different timing is inconclusive.
4. Distinguish unexecuted tests, missing coverage, and passing results. Do not claim
   “no bypass” from a source scan or a handful of examples. Keep analysis within
   the user's requested review and testing authorization.
5. Stop broadening tests when the meaningful remaining risk is resolved or the
   required gate is met. List residual uncertainty instead of implying exhaustive
   correctness through test quantity.

## Decide within the evidence

State whether the intended fix is supported for the reviewed scope, what remains
blocking, and which targeted evidence would change the judgment. If deployment is
part of the request, account for rollout feasibility, operator burden, rollback
effects, retained data compatibility, and early observable triggers. Where root
cause remains uncertain, distinguish a reversible impact-reduction measure from
an established repair. Do not turn approval of a code review into authorization
to deploy or alter a live system.
