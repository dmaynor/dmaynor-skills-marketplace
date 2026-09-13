---
name: repeatable-demo-evidence
description: Prepare and rehearse a repeatable application demonstration with synthetic accounts, role-specific journeys, recovery instructions, screenshots, and a portable offline walkthrough ZIP. Use for demo preparation and evidence handoff, not ordinary screenshot capture.
metadata:
  version: "1.0.0"
  lifecycle: active
---

# Repeatable demo and evidence

Make the demonstration repeatable by another presenter and preserve evidence of what actually ran. Respect the requested application, environment, audience, and output format.

## Prepare the demonstration

Inspect repository instructions, supported launch/test commands, authentication, fixture setup, and existing evidence. Define a coherent scenario, participant roles, intentional event sequence, and observable outcome. Use synthetic data where appropriate; keep account identifiers, ports, provider settings, and passwords in environment-specific configuration, not reusable skill instructions.

Use maintained application scripts to provision an isolated cohort. Give concurrent people separate browser profiles or contexts. Exercise normal invitation and activation paths. If email is captured locally, document who can retrieve links and how; captured delivery is not real-inbox delivery. Do not publish activation/reset links, session tokens, or real credentials in screenshots or reports.

Keep historical evidence intact. Prepare a fresh rerun or filter the current cohort rather than clearing shared databases. Document startup, expected ready state, pause/resume, interruption recovery, stopping without data loss, and rerun preparation using [the presenter template](assets/presenter-guide.md). Do not assume an exercise is ready merely because its page loads.

## Rehearse and capture

Walk the named workflows as each relevant role. Include the failure/recovery behavior required by the request, using bounded test hooks in the isolated environment. Capture screenshots during actual execution, with readable content and enough context to identify the state. Inspect each selected image; replace blank, clipped, stale, or misleading evidence. Keep sensitive data out of capture rather than relying on later redaction.

Record source revision, configuration identity without secrets, fixture IDs, assertions, test results, and limitations. Verify server-side readback for committed work and preserved original evidence after rerun. Distinguish observations from hypotheses. Keep real-provider qualification separate from provider-independent acceptance and document a truthful facilitator/operator fallback.

## Build the handoff

Produce a report explaining the user journey, decisions, recovery, and outcomes; put detailed release metadata in a linked evidence record so it does not overwhelm the walkthrough. Include full-resolution screenshots, presenter instructions, required exports, and exact release identity. Adapt the template to the real product; remove unused fields.

For an offline HTML package, keep index.html beside an images directory and use relative image, stylesheet, and asset references. Include only the intended public/synthetic evidence, not working logs, browser profiles, or private environment files. Review text and images for credentials; automated scanning is only a supplement.

Create the ZIP from the completed folder. Extract it into a fresh temporary directory, open the extracted entrypoint in a browser, and verify every image loads, important links work, and the layout remains readable. A checksum verifies bytes, not usability.

Run `python3 scripts/verify_walkthrough.py PATH_TO_EXTRACTED_FOLDER --entry index.html --zip PATH_TO_ZIP` from this skill directory. The helper checks static local HTML dependencies, rejects non-relative dependency URLs and paths outside the package, flags likely credentials without printing values, and checks ZIP parity/CRC. It does not execute JavaScript, parse CSS dependencies or srcset, inspect image contents, or prove application behavior. Inspect those dependencies and browser network activity separately when present. External hyperlinks may remain for citations; distinguish them from assets required offline.

Deliver a clickable report and ZIP, concise launch steps, exact validation scope, and remaining limitations. If publication or external delivery is requested, verify it at the destination; creating a local ZIP is not publication.
