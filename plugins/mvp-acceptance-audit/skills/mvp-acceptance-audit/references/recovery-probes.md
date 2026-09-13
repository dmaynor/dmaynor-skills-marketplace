# Select probes from the actual requirements

| Required invariant | Discriminating evidence |
|---|---|
| Draft survives interruption | Enter unsent content and selection; refresh and restart the service using the same storage; verify both survive. State whether drafts are browser-local or server-backed. |
| Uncertain submission is recoverable | Commit the request but suppress its confirmation using an isolated test hook; refresh; retry the persisted identical body and command ID; verify original receipt and exactly one durable record. |
| Recovery after lifecycle change | Recover the same committed receipt after pause and completion. A changed request body with the same ID must not silently become a new operation. |
| Access is withdrawn | Revoke/expire permission while the browser and connection remain open; verify protected activity ends. Retry/receipt paths must check current authorization. |
| Tenant/account isolation | Operate independent authenticated contexts concurrently; inspect each export and protected view. Switch identity with populated caches and open connections. |
| Shared edits do not silently overwrite | Two editors load the same version; first saves; second conflicts; retain second editor's text and offer explicit reconciliation against latest state. |
| Navigation preserves intent | Open a deep link, change tabs, refresh, go back and forward; verify URL and displayed workflow agree for each relevant role. |
| Rerun preserves evidence | Compare original responses/events before and after creation; new run has independent state and explicitly prepared membership/readiness. |
| Outcomes are traceable | Follow a response/evidence reference through observation, finding, recommendation and assigned action; inspect the downloaded artifact and ownership. |

Run destructive or interruption probes only within authorized, isolated resources with a defined recovery path. The table is a selection aid, not blanket permission or mandatory scope for every product.
