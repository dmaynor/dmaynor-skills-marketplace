---
name: rca-investigation
description: >-
  Root Cause Analysis investigation for failures, outages, bugs, and process
  breakdowns. Enforces layered diagnosis (infrastructure before logic before
  process), timeline reconstruction, causal chain separation, and corrective
  action validation. Use when something failed and you need to understand why
  — not just what happened, but which layer broke and what evidence proves it.
  Triggers on "root cause", "RCA", "why did this fail", "hot wash",
  "post-mortem", "what went wrong", "failure analysis", "incident review".
  Modes: SYSTEM_FAILURE, PROCESS_FAILURE, SECURITY_INCIDENT, BUG_REGRESSION,
  GENERAL_INVESTIGATION.
author: dmaynor
version: 1.1.0
date: 2026-04-23
---

# Root Cause Analysis (RCA) Investigation

Systematic failure diagnosis that enforces layered thinking, separates
symptoms from causes, and validates corrective actions against the actual
root cause — not the first plausible explanation.

## Problem

When something fails, the natural response is to explain it immediately.
This produces three systematic errors:

1. **Layer confusion**: Blaming application logic when infrastructure failed.
   Blaming process when tooling broke. Fixing the wrong layer wastes effort
   and leaves the real cause active.

2. **Symptom-cause conflation**: The visible failure is rarely the root cause.
   "The agent timed out" is a symptom. "The API had a service outage" is a
   cause. "We delegated complex tasks to agents" is a misattributed cause
   when the real cause was infrastructure.

3. **Overcorrection**: Changing strategy based on a misdiagnosed cause leads
   to abandoning approaches that were actually working. The cure becomes
   worse than the disease.

## Mode Selection

Auto-select based on input:

| Input Pattern | Mode |
|--------------|------|
| Service/system/tool failed or errored | `SYSTEM_FAILURE` |
| Process/workflow/loop underperformed | `PROCESS_FAILURE` |
| Security event or breach | `SECURITY_INCIDENT` |
| Bug reappeared or fix didn't work | `BUG_REGRESSION` |
| Ambiguous or mixed failure | `GENERAL_INVESTIGATION` |

## Core Workflow

### 1. Timeline Reconstruction

Before ANY analysis, build the timeline. What happened, when, in what order.

```
| Time | Event | Source | Layer |
|------|-------|--------|-------|
| T1   | [what happened] | [how you know] | [infra/app/process/human] |
```

**Rules:**
- Use absolute timestamps when available from logs, git, or system records
- When exact timestamps are not available, use relative sequencing anchored to known events ("after commit abc1234", "before the user checked in", "between the agent launch and the timeout")
- **Never fabricate timestamps.** Fake precision is worse than honest imprecision — it presents inferences as observations
- Include non-events that matter ("Air was unreachable entire session")
- Source every event (log, git, observation, inference — label which)
- Assign a provisional layer to each event

### 2. Failure Taxonomy (Check in Order)

**CRITICAL: Walk the layers top-down. Do not skip to application/process
layers without ruling out infrastructure first.**

| Layer | Check | Examples | Diagnostic |
|-------|-------|----------|-----------|
| L1: External Infrastructure | Third-party services, APIs, cloud providers | API outage, DNS failure, CDN down | Check status pages, error rates, token counts |
| L2: Local Infrastructure | Hardware, network, storage, OS | Drive disconnected, network dropped, OOM, reboot | Check dmesg, disk, connectivity, uptime |
| L3: Environment | Config, permissions, dependencies, state | Disk full, wrong version, missing file, stale cache | Check logs, file existence, env vars |
| L4: Tooling | The tools/agents/scripts used to do the work | Agent prompt was wrong, script had a bug, wrong tool chosen | Check tool output, compare to expected behavior |
| L5: Application Logic | The actual code or system under investigation | Bug, race condition, logic error | Code review, debugging, reproduction |
| L6: Process/Human | Workflow, decisions, prioritization, communication | Wrong priority, fixation, missed signal | Post-hoc analysis of decisions made |

**The layer where the failure originated is the root cause layer.**
**The layer where the failure was visible is the symptom layer.**
These are often different.

### 3. Evidence Collection per Layer

For each layer, collect:

| Evidence Type | What It Tells You |
|--------------|-------------------|
| **Positive evidence** | Something happened that shouldn't have |
| **Negative evidence** | Something didn't happen that should have |
| **Absence of evidence** | Can't tell — need more data |
| **Environmental evidence** | Context that makes a cause more/less likely |

**Token count heuristic for agent failures:**
- Near-zero tokens (< 100) → L1 (API never responded) or L2 (network)
- Normal tokens + timeout → L1 (stream limit) or L4 (task too large)
- Normal tokens + wrong output → L4 (bad prompt) or L5 (logic)
- Normal tokens + correct partial output → L1 (interrupted mid-work)

### 4. Causal Chain Separation

Distinguish:

```
ROOT CAUSE → PROXIMATE CAUSE → SYMPTOM → OBSERVED EFFECT
     ↓              ↓              ↓              ↓
 API outage → Agent stream  → "Agent timed → "Only 20 min
               timeout         out"           of useful work"
```

**The corrective action must target the root cause, not the symptom.**

| Target | Example Good Fix | Example Bad Fix |
|--------|-----------------|-----------------|
| Root cause | "Add retry logic for API failures" | — |
| Proximate cause | — | "Don't use agents for complex tasks" |
| Symptom | — | "Run more loop iterations" |
| Observed effect | — | "Work harder" |

### 5. Contributing Factor Analysis

After identifying the root cause, identify **contributing factors** that
made the failure worse but didn't cause it:

- Would the failure have occurred without this factor? → If yes: contributing, not causal
- Did this factor increase blast radius or recovery time? → Contributing
- Is this factor independently fixable? → Worth addressing even if not root cause

### 6. Corrective Action Validation

For each proposed corrective action, validate:

| Check | Question |
|-------|----------|
| **Layer match** | Does this fix target the same layer as the root cause? |
| **Proportionality** | Is the fix proportional to the failure, or an overcorrection? |
| **Side effects** | Does this fix break something that was working? |
| **Testability** | Can you verify this fix would have prevented the failure? |
| **Overcorrection test** | Would you still propose this fix if the failure hadn't happened? If no → probably overcorrecting |

### 7. Confidence Assessment

Use the same calibration as SAT:

| Term | Range | Usage |
|------|-------|-------|
| Almost Certain | 90-99% | Clear evidence at identified layer, alternatives ruled out |
| Highly Likely | 80-89% | Strong evidence, one layer clearly dominant |
| Likely | 65-79% | Preponderance points to one layer |
| Moderate | 50-64% | Multiple layers plausible |
| Uncertain | 20-49% | Insufficient evidence to isolate layer |

## Output Template

```markdown
## RCA INVESTIGATION: [Title]

**Mode**: [Mode]
**Root Cause Layer**: L[N] — [Layer Name]
**Confidence**: [Term] ([X-Y%])
**Date**: [Date of analysis]

---

### TIMELINE
| Time | Event | Source | Layer |
|------|-------|--------|-------|

### FAILURE TAXONOMY WALKTHROUGH
| Layer | Checked | Finding | Evidence |
|-------|---------|---------|----------|
| L1: External Infra | ✓/✗ | [Clear/Suspect/Ruled Out] | [evidence] |
| L2: Local Infra | ✓/✗ | ... | ... |
| L3: Environment | ✓/✗ | ... | ... |
| L4: Tooling | ✓/✗ | ... | ... |
| L5: Application | ✓/✗ | ... | ... |
| L6: Process/Human | ✓/✗ | ... | ... |

### CAUSAL CHAIN
```
ROOT CAUSE: [what actually broke]
  → PROXIMATE CAUSE: [immediate trigger of visible failure]
    → SYMPTOM: [what was observed]
      → EFFECT: [business/mission impact]
```

### CONTRIBUTING FACTORS
| Factor | Layer | Impact | Independently fixable? |
|--------|-------|--------|----------------------|

### ROOT CAUSE STATEMENT
[One paragraph: what failed, at which layer, with what evidence]

### CORRECTIVE ACTIONS
| Action | Targets Layer | Proportional? | Overcorrection test |
|--------|--------------|---------------|-------------------|

### WHAT WOULD NOT HAVE HELPED
[Actions that seem obvious but don't address the root cause]

### ASSUMPTIONS
1. [Assumption]

### OPEN QUESTIONS
- [What you still don't know]
```

## Mode-Specific Guidance

### SYSTEM_FAILURE

Focus on L1-L3. Check:
- Status pages for all external dependencies
- System logs (dmesg, syslog, journalctl)
- Resource utilization (disk, memory, CPU, network)
- Recent changes (deploys, config changes, OS updates)

### PROCESS_FAILURE

Focus on L4-L6 **but only after ruling out L1-L3.**
Check:
- Decision log (what choices were made and why)
- Task completion rate vs. plan
- Where time was actually spent vs. where it should have been
- Feedback loops (were signals of failure detected and acted on?)

### SECURITY_INCIDENT

Full layer sweep. Additionally:
- Attacker vs. defender timeline (parallel tracks)
- Dwell time analysis
- Detection gap analysis
- Map to MITRE ATT&CK where applicable

### BUG_REGRESSION

Focus on L3-L5. Check:
- What changed between "working" and "broken"
- Test coverage of the regression path
- Whether the original fix addressed root cause or symptom
- Environmental differences between test and production

## Anti-Patterns to Catch

| Anti-Pattern | Signal | Correction |
|-------------|--------|-----------|
| **Narrative fallacy** | RCA reads like a story with a moral | Strip narrative, show evidence → conclusion |
| **Hindsight bias** | "We should have known" | What signals were actually available at decision time? |
| **Overcorrection** | Fix is bigger than the failure | Apply proportionality test |
| **Layer skip** | Jump to L5/L6 without checking L1-L3 | Walk taxonomy top-down |
| **Single cause fixation** | "It was X" with no alternatives considered | Generate ≥3 candidate causes |
| **Blame assignment** | RCA identifies a person, not a system gap | Systems fail, not people. What allowed the error? |

## Cognitive Discipline Checklist

Before ANY output, verify:

- [ ] Timeline reconstructed with sources
- [ ] All 6 layers checked (or explicitly ruled out with evidence)
- [ ] Root cause layer identified with evidence
- [ ] Causal chain separated (root → proximate → symptom → effect)
- [ ] Contributing factors distinguished from root cause
- [ ] Corrective actions target root cause layer
- [ ] Overcorrection test applied to each corrective action
- [ ] Confidence has numeric range
- [ ] Open questions documented
- [ ] Anti-patterns checked

## Interaction

Support iterative refinement:
- "check layer N" → deep-dive specific layer
- "what about [alternative cause]" → evaluate as candidate
- "is this overcorrecting" → apply proportionality test
- "what evidence would change this" → falsification criteria
- "brief version" → compress to causal chain + corrective actions only

## Verification

1. Confirm the taxonomy walkthrough shows evidence for ruling out each layer, not just the identified root cause layer.
2. Verify the causal chain has at least 3 levels (root → proximate → symptom) and they are at different layers.
3. Check that every corrective action passes the overcorrection test.
4. Confirm at least one entry in "What Would Not Have Helped" — if everything helps, the analysis isn't discriminating enough.
5. Validate that the root cause statement includes specific evidence, not just reasoning.
