# Failure Taxonomy Reference

## Layer Definitions and Diagnostic Signals

### L1: External Infrastructure
**Definition:** Services, APIs, and systems outside your control.

| Signal | Meaning |
|--------|---------|
| Status page shows incident | Confirmed L1 |
| Error rates spike across multiple unrelated tasks | Likely L1 |
| Token count near-zero on API call | API never responded |
| Timeout with no error message | Connection-level failure |
| Same failure across different task types simultaneously | Common dependency failure |
| Works from different network/machine | Not L1 (probably L2) |

**Common L1 failures:**
- API rate limiting or outage
- DNS resolution failure
- CDN or edge cache corruption
- Third-party auth provider down
- Cloud region degradation

### L2: Local Infrastructure
**Definition:** Your hardware, OS, network, and storage.

| Signal | Meaning |
|--------|---------|
| dmesg shows hardware errors | Confirmed L2 |
| Disk I/O errors or "no space" | Storage failure |
| SSH drops mid-session | Network instability |
| Process killed by OOM | Memory pressure |
| Machine rebooted unexpectedly | Kernel panic, watchdog, power |
| Performance degrades over time | Resource leak or thermal throttle |

**Common L2 failures:**
- Drive disconnected or full
- Network interface down or IP changed
- RAM failure or OOM
- Kernel panic from driver or hardware
- Power loss or sleep/wake failure

### L3: Environment
**Definition:** Configuration, dependencies, state, and permissions.

| Signal | Meaning |
|--------|---------|
| "Permission denied" | File/process permissions |
| "No such file or directory" | Missing dependency or wrong path |
| Works for root but not user | Privilege/entitlement issue |
| Works on machine A but not B | Environment-specific config |
| Worked yesterday, fails today | State drift or update |

**Common L3 failures:**
- Missing or wrong version dependency
- Stale cache or state file
- Environment variable not set
- File permissions changed
- OS update changed behavior

### L4: Tooling
**Definition:** The tools, scripts, agents, or automation used.

| Signal | Meaning |
|--------|---------|
| Tool produces wrong output for correct input | Tool bug |
| Tool works but for wrong task | Tool selection error |
| Agent prompt misunderstood | Prompt engineering issue |
| Script fails on edge case | Script bug |
| Automation does unexpected thing | Automation logic error |

**Common L4 failures:**
- Wrong tool for the job
- Bad agent prompt (unclear, ambiguous, missing context)
- Script doesn't handle edge case
- Tool version incompatibility
- Automation race condition

### L5: Application Logic
**Definition:** The actual code, system, or target under investigation.

| Signal | Meaning |
|--------|---------|
| Reproducible with minimal case | Confirmed bug |
| Crash dump points to specific code | Code defect |
| Logic produces wrong result deterministically | Algorithm error |
| State machine reaches invalid state | State management bug |
| Works with input A, fails with input B | Input validation issue |

### L6: Process/Human
**Definition:** Workflow decisions, prioritization, communication.

| Signal | Meaning |
|--------|---------|
| Spent 30 min on low-priority item while high-priority waited | Priority inversion |
| Repeated same failing approach 4+ times | Fixation (tunnel vision) |
| Didn't check obvious thing | Assumption error |
| Changed strategy based on single failure | Overcorrection |
| Didn't communicate blocker | Communication gap |

## Cross-Layer Interactions

Failures often span layers. Common patterns:

| Pattern | Example | Real Root Cause |
|---------|---------|----------------|
| L1 masquerading as L4 | "Agents can't do complex tasks" | API was down |
| L2 masquerading as L5 | "Code has a race condition" | Machine was swapping |
| L3 masquerading as L6 | "Developer made a mistake" | Config was wrong |
| L6 amplifying L1 | API blip + no retry = total loss | Both, but L1 is root |
