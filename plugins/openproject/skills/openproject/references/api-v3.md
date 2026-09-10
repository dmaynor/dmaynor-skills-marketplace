# OpenProject API v3 Guidance

Use the instance’s `/api/v3` root and returned HAL links as the source of truth.
The official documentation is versioned with the live product and may differ
from an older self-hosted instance.

## Official sources

- [API introduction](https://www.openproject.org/docs/api/)
- [Work packages](https://www.openproject.org/docs/api/endpoints/work-packages/)
- [Activities](https://www.openproject.org/docs/api/endpoints/activities/)
- [Attachments](https://www.openproject.org/docs/api/endpoints/attachments/)
- [Relations](https://www.openproject.org/docs/api/endpoints/relations/)
- [Projects](https://www.openproject.org/docs/api/endpoints/projects/)
- [Queries](https://www.openproject.org/docs/api/endpoints/queries/)
- [Schemas](https://www.openproject.org/docs/api/endpoints/schemas/)
- [API filters](https://www.openproject.org/docs/api/filters/)
- [API forms](https://www.openproject.org/docs/api/forms/)

## Representation and discovery

- API resources use HAL-style links. Prefer `_links.<relation>.href` over
  constructing related URLs from guessed identifiers.
- Collection responses may be paginated. Follow returned pagination links or
  explicitly iterate pages; do not treat the first page as complete.
- Filters are encoded JSON query data. Generate them with a JSON serializer and
  URL encoder rather than hand-built escaping.
- Instance configuration controls available projects, work-package types,
  statuses, priorities, custom fields, workflows, and permissions.

## Work packages

Important fields include `subject`, `description`, dates, duration, estimated
time, scheduling mode, and links to project/workspace, type, status, priority,
assignee, responsible user, parent, version, and other resources. Write linked
resources using their HAL link representation as required by the live schema.

The work-package update model requires `lockVersion` for optimistic locking.
Fetch the current work package before an update. On conflict, re-read, compare
the concurrent edit with the plan, and stop or re-plan; never increment a stale
value locally and retry blindly.

Parent dates can be derived or constrained by child schedules depending on
manual/automatic scheduling. Validate a bulk Gantt change against scheduling
rules before applying it.

## Forms and schemas

Forms provide validation and allowed-value feedback for a proposed resource.
Use them before creating or updating when fields depend on project, type,
status, workflow, or permissions. Treat a validation error as a plan defect, not
a transient failure.

## Activities and comments

Work-package comments are represented in activity/journal history. Read recent
activities before posting to prevent duplicate updates. Keep generated comments
concise and provenance-aware. Verify the returned activity and its association
after creation.

## Relations and hierarchy

Parent/child hierarchy is represented on work packages; semantic relations such
as follows, blocks, relates, duplicates, or includes are separate relation
resources. Do not substitute a relation for a parent link or infer a dependency
from adjacent Gantt dates. Relation creation is scoped to a work package and
must reference the other work package using the schema accepted by the instance.

## Attachments

Attachment operations may use multipart upload and can be scoped to a work
package or activity. Respect server size/type policy. Verify the returned
attachment metadata, container association, and accessible download link.

## Error handling

| Class | Response |
|---|---|
| Authentication/authorization | Stop; report missing capability without retrying credentials blindly |
| Not found | Re-resolve canonical identity and visibility |
| Validation | Surface field-level errors and revise the plan |
| Optimistic-lock conflict | Re-fetch, compare, and re-plan |
| Rate limit/transient 5xx/network | Retry with bounded backoff and a write-safe idempotency strategy |
| Ambiguous or malformed success | Stop and verify before any dependent write |

For create operations, timeouts are dangerous because the server may have
committed before the client lost the response. Search by stable sync key before
retrying; do not issue a blind duplicate create.
