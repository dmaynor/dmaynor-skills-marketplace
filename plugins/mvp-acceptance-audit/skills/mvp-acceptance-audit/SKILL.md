---
name: mvp-acceptance-audit
description: Audit an MVP or release against its actual requirements, qualify recovery and user journeys, and produce evidence-backed completion and delivery records. Use for readiness assessments and requested release qualification, not routine isolated code edits.
metadata:
  version: "1.0.0"
  lifecycle: active
---

# MVP acceptance audit

Turn the requested product outcome into verifiable acceptance evidence. An assessment request authorizes inspection; implementation, deployment, and merge follow the user's actual authorization. Preserve the original scope throughout the audit.

## Establish the contract

Read repository guidance and the supplied objective, specification, issues, and acceptance documents. Resolve the repository, branch, current commit, uncommitted changes, and intended deployment. Preserve unrelated work. Distinguish a local demo from production or capacity qualification; use the user's chosen boundary rather than narrowing it to match passing tests.

Create a requirement-to-evidence record using [the acceptance template](assets/acceptance-record.md). Split requirements where they need different evidence. Include named artifacts, commands, roles, lifecycle states, error/recovery behavior, and delivery gates. Record missing evidence as unverified, not implicitly passed. A historical report is a lead to evidence, not current acceptance.

## Inspect before expanding tests

Map each requirement to implementation, existing checks, and runtime evidence. Inspect test assertions before treating a green job as proof. Reuse maintained repository commands; keep application setup and fault injection in repository tests/scripts rather than duplicating them in the skill.

For stateful applications, read [the recovery and identity probes](references/recovery-probes.md) and select those required by the objective. Do not turn every probe into mandatory scope for unrelated products. Prefer tests that distinguish failure modes over tests that mirror implementation.

Trace visible commands to their named workflows for each relevant role. Verify deep links and back/forward navigation, loading/empty/error states, and the next action through the full user journey. Inspect generated deliverables and their contents, not just successful download responses.

If implementation is authorized, fix demonstrated gaps, run relevant checks, and commit completed increments according to repository conventions. Otherwise report gaps with concrete acceptance criteria. Do not weaken controls, delete retained evidence, or substitute synthetic success for required behavior.

## Separate qualification lanes

Record source/unit checks, authenticated browser journeys, durable storage/recovery, provider acceptance, and deployment/capacity checks separately. A mocked provider can qualify application behavior; it cannot qualify the real provider. Provider-independent acceptance must not accidentally require external accounts. A screenshot proves visible state, not persistence or isolation.

Use existing specialized review workflows when requested or relevant and available; do not claim this audit is an independent security assessment. Address review findings with evidence. Explain rejected findings using inspected behavior rather than dismissing them because tests passed.

## Verify delivery and close

Record exact tested commit and CI run, failures/skips, reviewer disposition, delivered commit, and deployment identity where applicable. After a merge, compare the resulting tree to the tested revision; if it differs, qualify the changed result. Observe required jobs to terminal state. A polling timeout is not proof that work stopped, and a local commit is not remote delivery.

Before completion, revisit every requirement row. Missing, indirect, contradicted, or incomplete evidence prevents a full completion claim. Report what remains and continue authorized work. When every required item is proven, provide the acceptance record, usable artifact links, operating limits, and exact delivery identity. If the environment has an active goal tracker, close it only after this audit; do not create one just to use this skill.
