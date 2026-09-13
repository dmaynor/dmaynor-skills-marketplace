# Evidence checks with valid conclusions

Use this reference when proposing a check or deciding whether a negative result
excludes an explanation. Specify a discriminating observation, not just a tool.

## Check record

For each consequential check, state:

| Field | Required content |
|---|---|
| Question | Exact proposition, mechanism, and decision the result bears on. |
| Measured event | What is observed: submission, transmission, receipt, display, acknowledgment, or another defined state. |
| Competing predictions | Expected results for the plausible alternatives, including combinations. Distinguish necessary from probable predictions. |
| Scope and opportunity | Target, route, input class, load, time window, sampling, and whether the expected event would be observable. |
| Validity assumptions | Clock alignment, field semantics, independent measurement chain, parser correctness, or other material dependencies. |
| Feasibility | Owner, access, time, disruption, and required authorization. |
| Decision consequence | What each result changes, what it does not establish, and when the check is inconclusive. |

Do not invent baselines, acceptable delay, expected thresholds, or measurement
precision. Use supplied or verified values; otherwise identify a needed threshold
or state the result qualitatively. A needed threshold is a decision prerequisite,
not a reason to pretend that normality has already been defined.

## Common failures of inference

| Check result | Invalid conclusion | Defensible conclusion |
|---|---|---|
| A probe reports a fast response | The application transaction cannot be delayed. | This probe's traffic had this result on the tested path and interval; compare actual transaction behavior. |
| A gateway log timestamp differs from the dispatch system timestamp | The difference is true delivery latency. | The difference includes any clock offset and semantic mismatch; establish both or use an appropriate shared clock. |
| One order arrives normally | There is no fleetwide or intermittent problem. | This order completed normally under the observed conditions. |
| A local independent measurement confirms delay | The telemetry calculation is correct. | Real delay exists for this measurement; independent telemetry inflation can still coexist. |
| Several interfaces show the same anomaly | The anomaly has independent corroboration. | Establish whether their source and transformation chains are independent before counting corroboration. |
| Recovery follows two changes | Either change alone is confirmed as the fix. | The joint intervention preceded recovery; their individual effects remain unresolved. |
| Search finds no matching record | The event did not occur. | Bound the result by collection, retention, parser coverage, and the event's detectability. |

Where clock domains differ, an observed timestamp difference contains both the
event interval and clock offset. Unknown offset is not zero. Even one continuous
recording measures only the events it captures; a spoken acknowledgment interval
does not separately measure network receipt or screen display.

Prefer an observation that distinguishes mechanisms within the real transaction.
If varying a condition, hold other material factors constant where feasible; record
uncontrolled factors rather than silently treating the comparison as causal proof.
Check coverage first when a negative finding drives an exclusion.

## Relate findings to action

Distinguish a logical contradiction of a necessary prediction, a change in relative
support, and an inconclusive result. A noisy negative test usually changes support
within its tested scope rather than refuting every version of a hypothesis.
Do not cancel a proportionate protective action merely because one check is clean.

Give the action a decision deadline independent of investigation completion. Use
current and forecast capacity separately, assign acknowledgment/escalation ownership
where needed, and identify a trigger observable before delayed reconciliation or
irreversible harm. Root cause can remain unresolved while a bounded action is justified.
