---
name: purple-teaming
description: |
  Plan and execute purple team exercises for detection validation.
  Collaborative offensive/defensive testing using atomic or scenario-based methodologies.

  TRIGGERS - Use this skill when user:
  - Wants to plan a purple team exercise or detection validation
  - Needs atomic test cases for specific ATT&CK techniques
  - Asks about detection engineering for offensive techniques
  - Wants Splunk/Sigma queries for threat detection
  - Needs to track exercise results or coverage metrics
  - Asks about ATT&CK, Kill Chain, Diamond Model, or Pyramid of Pain
  - Says "purple team", "detection validation", "atomic test", "adversary emulation"
  - Wants to assess detection coverage gaps

  METHODOLOGIES: ATOMIC (isolated techniques), SCENARIO (attack chains)
---

# Purple Teaming

Plan, execute, and track collaborative offensive/defensive exercises that validate detection capabilities against adversary techniques.

## When to Use

- Designing detection validation exercises
- Building atomic test cases for technique coverage
- Planning scenario-based adversary emulation
- Mapping detections to ATT&CK techniques
- Assessing detection coverage gaps
- Creating detection engineering requirements from offensive techniques
- Tracking exercise results and coverage metrics

## When NOT to Use

- Covert red team engagements (use traditional red team methodology)
- Penetration testing for vulnerability discovery
- Threat hunting without defined technique scope
- Production incident response

## Core Concept

Purple teaming sacrifices attack realism for faster feedback loops and broader technique coverage.

| Aspect | Red Team | Purple Team |
|--------|----------|-------------|
| Transparency | Covert | Full collaboration |
| Feedback loop | End of engagement | Real-time |
| Coverage | Narrow (attack path) | Broad (technique catalog) |
| Realism | Highest | Medium-High |
| Detection validation | Binary (caught/missed) | Granular (logged/alerted/blocked) |

## Methodologies

### Atomic Testing

Execute individual techniques in isolation, dechained from full attack sequences.

**Best For**: Detection benchmarking, environmental comparison, tooling evaluation, regression testing, automation pipelines

**Limitations**: Loses attack realism, threshold-based detections may not fire, doesn't test investigation processes

### Scenario-Based Testing

Execute end-to-end attack chains honoring chronological sequence.

**Best For**: Process/response testing, detection engineering, attack familiarization, SOC training

**Limitations**: Resource intensive, requires offensive expertise, harder to repeat consistently

## Exercise Planning

### Pre-Exercise Checklist

| Item | Notes |
|------|-------|
| Authorization documented | Rules of engagement signed |
| Infrastructure selected | Lab vs. production |
| Technique scope defined | ATT&CK IDs listed |
| Detection baseline captured | Current alert/log state |
| Communication channel established | Out-of-band coordination |
| Rollback procedures documented | How to undo changes |

### Scope Definition

```yaml
exercise:
  name: "Q1 2026 Detection Validation"
  methodology: atomic
  techniques:
    - T1087.002  # Domain Account Discovery
    - T1069.002  # Domain Groups
    - T1018      # Remote System Discovery
    - T1003.001  # LSASS Memory
    - T1003.006  # DCSync
    - T1021.002  # SMB/Admin Shares
```

## Test Case Structure

```yaml
test_case:
  id: PT-2026-001
  technique: T1087.002
  name: Domain Account Discovery via net.exe
  
  execution:
    platform: windows
    executor: command_prompt
    command: |
      net group "Domain Admins" /domain
    
  expected_telemetry:
    - source: Sysmon
      event_id: 1
      fields:
        Image: "*\\net.exe"
        CommandLine: "*group*/domain*"
        
  expected_detection:
    - name: "Domain Group Enumeration"
      type: correlation
      threshold: "3+ net group commands in 60 seconds"
      
  outcome:
    telemetry: [logged | not_logged]
    alert: [fired | not_fired]
    prevention: [blocked | not_blocked]
```

## Detection Engineering Patterns

### Parent-Child Process Anomalies

| Parent | Suspicious Child | Technique |
|--------|------------------|-----------|
| `msbuild.exe` | `powershell.exe`, `cmd.exe` | T1127.001 |
| `wmiprvse.exe` | Any unexpected child | T1047 |
| `rundll32.exe` | Network connection | C2 indicator |
| `excel.exe` | `powershell.exe` | Macro execution |

### Threshold-Based Detection (Splunk)

```spl
index=sysmon EventCode=1 
Image IN ("*\\net.exe", "*\\nltest.exe", "*\\dsquery.exe")
| bin _time span=60s
| stats count by _time, user, ComputerName
| where count > 5
```

### Key Telemetry Sources

| Source | Key Events | Covers |
|--------|------------|--------|
| Windows Security | 4624, 4625, 4688, 4720, 4732 | Auth, process, account changes |
| PowerShell | 4104 (Script Block) | Encoded/obfuscated commands |
| Sysmon | 1, 3, 7, 8, 10, 11, 22 | Process, network, injection, files, DNS |
| Network (Zeek) | conn, dns, http, ssl | Lateral movement, C2, exfil |

## Outcome Tracking

### Per-Technique Outcomes

| Outcome | Definition |
|---------|------------|
| **Logged** | Telemetry exists in SIEM |
| **Alerted** | Detection rule fired |
| **Blocked** | Prevention control stopped execution |
| **Missed** | No telemetry or detection |

### Coverage Metrics

- Detection rate: `techniques_detected / techniques_tested`
- Alert fidelity: `true_positives / total_alerts`
- Mean time to detect (MTTD)

## Emulation Tool Selection

| Tool | Best For | Complexity |
|------|----------|------------|
| **Atomic Red Team** | Atomic tests, regression, automation | Low |
| **MITRE Caldera** | Autonomous operations, fact-based chains | Medium |
| **Mythic** | Full C2, realistic scenario ops | High |

### Atomic Red Team Quick Start

```powershell
# Install
IEX (IWR 'https://raw.githubusercontent.com/redcanaryco/invoke-atomicredteam/master/install-atomicredteam.ps1' -UseBasicParsing)

# Execute technique
Invoke-AtomicTest T1087.002 -TestNumbers 1,2,3

# Execute with logging (for VECTR)
Invoke-AtomicTest T1087.002 -LoggingModule "Attire-ExecutionLogger"
```

## Exercise Workflow

```
1. SCOPE      → Define techniques, select methodology, document authorization
2. PREPARE    → Capture baseline, prepare tools, establish comms
3. EXECUTE    → Run techniques, blue team monitors, document outcomes
4. ANALYZE    → Classify results, identify root cause for misses
5. IMPROVE    → Build/tune detections, update telemetry collection
6. TRACK      → Record in tracking system, update coverage metrics
```

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Testing only known-bad | Include suspected blind spots |
| Atomic tests without context | Run atomic first, then scenario for realism |
| No baseline comparison | Capture detection state before exercise |
| Skipping cleanup | Always run cleanup, validate no persistence |
| Production without safeguards | Lab first; if prod required: off-hours, rollback ready |

## Resources

See `resources/` directory:
- `frameworks.md` - ATT&CK, Kill Chain, Diamond Model, Pyramid of Pain reference
- `test-cases/atomic-templates.md` - Ready-to-use atomic test cases
- `detection-queries/queries.md` - Splunk SPL and Sigma rules
- `tracking-templates/templates.md` - Exercise planning and tracking templates
