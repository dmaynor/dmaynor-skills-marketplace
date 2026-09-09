# Security evidence patterns

Use patterns to generate and distinguish explanations, not to classify an event
as compromise by resemblance. Scope the asset, account, time window, observed
action, authorization question, and possible impact separately.

Consider external misuse, internal misuse, authorized unusual activity, accidental
policy violations, and collection artifacts when each is plausible. Do not require
every category. Preserve combined causes such as a real unauthorized action plus
misattributed telemetry. Successful authentication establishes the system's
authentication result, not the human operator or authorization of subsequent work.

| Reported pattern | Plausible mechanisms | Evidence that may discriminate |
|---|---|---|
| Login from a new location or at an unusual time | Credential misuse, travel, changed VPN exit, automation, geolocation error | Account/session linkage, device context, authorized work, actions within the session, independent operator confirmation. |
| Repeated failed authentication | Guessing, expired service credentials, retry loop, user mistakes | Target distribution, exact failure reason, cadence, service ownership, scope of subsequent success. No universal count proves an attack. |
| Office or browser process launches a script interpreter | User workflow, installer, automation, unwanted execution | Verified parent-child lineage, script content and provenance, file origin, authorization, resulting process and network activity. |
| Encoded or unusual command content | Packaging, administration, evasion, corrupted logging | Decoded content through an authorized safe method, command semantics, expected workflow, outcomes. A substring or tool name is not intent. |
| New task, service, or startup entry | Deployment, maintenance, persistence, user configuration | Creator and session, configured content, scope, installation records, execution history and authorization. |
| Access to credential-related processes or files | Security tooling, backup, troubleshooting, credential theft | Exact access rights and operations, process identity, resulting artifacts, approved purpose, downstream account activity. |
| Many host connections or directory queries | Inventory, monitoring, discovery, misconfiguration | Collection topology, schedule, tool ownership, queried objects, follow-on actions and declared authorization. |
| Remote administration activity | Support, deployment, lateral movement | Established source/destination roles, session identity, requested work, executed action, target scope. |
| Periodic outbound connections or unusual DNS labels | Health checks, synchronization, application protocol, remote control, data transfer | Process ownership, protocol semantics, request/response content when available, baseline, destination relationship. Periodicity alone is nondiagnostic. |
| Large reads, archives, or outbound transfers | Backup, migration, user work, collection, exfiltration | Data identity, verified direction, destination control, authorization, volume relative to the relevant workload, completion evidence. |

## Preserve what the source actually establishes

- Quote a detector's verdict as the detector's verdict. Inspect the underlying
  records before adopting “malware,” “attack attempt,” or “exfiltration.”
- Keep untyped address mentions separate from source and destination. A first IP
  in free text may identify a target, proxy, quoted example, or previous hop.
- Check identity translation, NAT/proxy behavior, duplicate forwarding, clock
  domains, retention, and gaps where they affect the inference.
- Correlate events only with an explicit linkage, such as session or transaction
  identifiers and compatible time bounds. Close timestamps alone do not establish
  one actor or causal sequence.
- Absence of later activity is informative only if the relevant telemetry was
  collected and capable of observing it. A normal sampled endpoint does not clear
  a fleet or an intermittent condition.

## Use taxonomies after establishing behavior

If an ATT&CK mapping helps the user's investigation, verify the current technique
definition against official MITRE material and cite it. Label the observed behavior
and any tentative mapping separately. Do not infer actor identity from a technique,
or increase confidence by counting phases, tools, tactics, or matching keywords.

## Choose a bounded response

Separate factual compromise judgment from a precautionary containment decision.
For any recommendation, identify the affected scope, responsible role, likely
disruption, available fallback, and the evidence or deadline that changes it.
Do not wait for confirmed impact if a proportionate reversible measure can bound
credible harm. Conversely, unexplained telemetry alone does not justify an
unbounded disruptive response. Analysis does not authorize operational changes.
