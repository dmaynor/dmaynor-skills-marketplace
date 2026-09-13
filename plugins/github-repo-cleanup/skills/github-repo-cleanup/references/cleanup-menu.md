# Additional cleanup activities to suggest

Choose from observed repository state; these are not a mandatory checklist or blanket authorization.

| Activity | Useful evidence | Default treatment |
|---|---|---|
| Stale remote-tracking refs | Ref absent on current remote | Prune within authorized local ref cleanup; preserve local branches. |
| Local default branch synchronization | Clean checkout and fast-forward relation | Fast-forward; leave dirty/diverged checkouts intact. |
| Abandoned worktrees and stashes | Owner, dirty files, branch use, unique content | Inventory and recommend retention/removal; ask before discarding content. |
| Duplicate or superseded PRs/issues | Explicit replacement and preserved scope | Propose cross-links and closure reasons; closing/commenting needs authorization. |
| Branch ownership and retention conventions | Repeated ambiguous stale branches | Recommend owner labels, naming, review dates, protected release branches, and merged-branch deletion policy. Changing repo settings is separate authorization. |
| Obsolete CI workflows and redundant jobs | Trigger graph, callers, release requirements | Propose a focused PR; validate retained coverage, permissions, and branch filters. |
| Build caches and workflow artifacts | Measured size and retention/audit needs | Recommend retention changes; deletion may destroy evidence and requires explicit scope. |
| Untracked/generated files and ignore rules | Build reproducibility and tracked-file inventory | Propose ignore-rule fixes; do not run broad git clean or delete user files. |
| Stale documentation and broken links | Default branch, supported commands, current release | Create a scoped documentation PR when edits are authorized. |
| Dependency and lockfile hygiene | Maintained package tooling, actual unused references | Separate update/removal PR with relevant tests; do not equate age with obsolescence. |
| Release tags, packages, and assets | Consumers, provenance, support/rollback policy | Inventory only by default; never delete released artifacts as branch cleanup. |
| Permissions, deploy keys, webhooks, secrets | Authorized owner review and active consumers | Suggest a separate access review; never print, revoke, or rotate secrets incidentally. |
| Large blobs or leaked secrets in history | Size/provenance analysis or confirmed exposure | Escalate to a dedicated plan. History rewriting, garbage collection with aggressive expiry, and force-pushing shared refs are outside routine cleanup. |

Prioritize low-risk changes that remove confusion without losing evidence. Report expected benefit, affected owners, validation, and reversibility for each recommendation.
