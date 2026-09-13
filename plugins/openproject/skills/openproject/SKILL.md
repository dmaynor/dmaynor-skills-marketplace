---
name: openproject
description: >-
  Inspect, plan, create, update, reconcile, and verify OpenProject projects and
  work packages through API v3, an available OpenProject connector, or the UI.
  Use for OpenProject/OpenMine work-package hierarchies, PRD imports, activity
  comments, attachments, relations, schedules, Gantt date staggering, status
  reconciliation, and audit-ready progress updates. Do not activate for generic
  project-management advice that does not involve an OpenProject instance.
metadata:
  author: dmaynor
  version: 1.0.0
  date: 2026-09-10
---

# OpenProject

Treat OpenProject as an evidence-preserving execution ledger, not merely a task
list. Preserve the original requirement, separate current state from requested
state, and make every mutation attributable and verifiable.

## Select the access path

1. Prefer an installed OpenProject connector or MCP server when it exposes the
   required operation.
2. Otherwise use API v3. Discover capabilities from `/api/v3`, schemas, forms,
   and returned HAL links instead of assuming IDs, types, statuses, priorities,
   custom fields, or workflows are identical across instances.
3. Use authenticated browser interaction only when neither connector nor API
   supports the required operation or when visual verification is essential.

For API behavior and endpoint guidance, read
[references/api-v3.md](references/api-v3.md). For workflows derived from prior
OpenProject usage, read [references/workflows.md](references/workflows.md).

## Authorization boundary

- Reads, inspection, comparison, planning, and dry-run generation do not imply
  permission to mutate OpenProject.
- Before a write, identify the instance, project, exact targets, fields to
  change, and expected write count. Obtain explicit authorization if the user
  has not already requested the mutation.
- Default automation to dry-run. Require an explicit apply mode for writes.
- Deletion, bulk reassignment, hierarchy replacement, and large schedule shifts
  require a target preview even when writes were requested.
- Never expose API keys, authorization headers, cookies, or credential-file
  contents. A configured credential such as `~/.op` may be used without printing
  it. Do not invent its format; inspect only what is necessary to authenticate.

## Core workflow

### 1. Resolve scope and current state

- Normalize product aliases: “OpenMine” may refer to an OpenProject instance,
  while “Redmine” is a distinct product. Confirm the actual API from the server
  root; do not select endpoints from the nickname alone.
- Resolve projects and work packages by canonical API identity. Treat names,
  query IDs, and browser URLs as discovery inputs, not proof of identity.
- Read the target work package, its parent/children, relations, activities,
  attachments, status, dates, assignees, and `lockVersion` when relevant.
- Record unavailable, contradictory, or permission-hidden evidence explicitly.

### 2. Build a change plan

Produce a compact plan containing:

| Target | Current | Proposed | Evidence | Risk |
|---|---|---|---|---|
| Work package ID/link | Exact current value | Exact new value | Requirement/source | Conflict or side effect |

For bulk operations include totals for create, update, unchanged, ambiguous,
and blocked. Apply a bounded maximum write count. Stop if the planned count
exceeds it.

### 3. Validate before writing

- Follow action and form links when available to validate writable fields and
  allowed values against the current user, project, type, and status.
- Preserve stable external identifiers or sync keys in a deterministic field or
  description marker. Abort if one sync key maps to multiple work packages.
- Re-fetch each update target immediately before mutation and submit its current
  `lockVersion`; do not overwrite a concurrent edit.
- Preserve unrelated description content. Use a dedicated, clearly delimited
  managed block when synchronizing generated content.

### 4. Apply narrowly

- Create parents before children; resolve returned IDs before linking children.
- Update only explicitly planned fields.
- Retry transient transport failures with a small bounded backoff. Do not retry
  authorization, validation, conflict, or semantic errors unchanged.
- Persist resumable state after each successful write in bulk jobs.
- Notifications are opt-in for high-volume automation.

### 5. Verify from the server

Re-read every mutated resource. Verify the intended values, hierarchy,
relations, activity rendering, attachments, and schedule behavior. Report
canonical work-package IDs/links and separate verified results from attempted
or blocked changes.

## Evidence and writing conventions

- Use headings to separate status, evidence, decisions, next actions, and
  blockers.
- In activity comments, use Markdown blockquotes for quoted source material and
  keep conclusions outside the quote. Do not simulate shaded quote styling with
  raw HTML unless the instance explicitly supports it.
- Attach source artifacts when they are part of the work record; do not claim an
  attachment succeeded until the returned resource and filename are verified.
- Never allow linked pull requests, remediation notes, or later commentary to
  overwrite the original request. Store them as separate evidence.
- For repository reconciliation, distinguish repository facts (merged PR,
  commit, CI result) from the OpenProject lane’s stale or current claims, then
  update only the fields or activity needed to close the discrepancy.

## Fail-safe conditions

Stop without mutation when identity is ambiguous, the server product/API does
not match expectations, the project or work package is unresolved, duplicate
sync keys exist, a form rejects the plan, `lockVersion` changed, permissions are
insufficient, attachments are missing, or the server response cannot be
verified. Return the exact blocker and the smallest safe next action.
