# Exercise Tracking Templates

Templates for tracking purple team exercise planning, execution, and results.

---

## Exercise Planning Template

```yaml
# Purple Team Exercise Plan
# -------------------------

exercise:
  id: "PT-YYYY-QN-NNN"
  name: ""
  methodology: atomic | scenario
  
planning:
  start_date: "YYYY-MM-DD"
  execution_date: "YYYY-MM-DD"
  lead: ""
  
authorization:
  approver: ""
  approval_date: ""
  roe_document: ""
  scope_limitations:
    - ""
    
infrastructure:
  environment: lab | staging | production
  target_systems:
    - hostname: ""
      ip: ""
      role: ""
  tools_required:
    - name: ""
      version: ""
      
team:
  offensive:
    - name: ""
      role: "Technique Executor"
  defensive:
    - name: ""
      role: "SOC Analyst"
  administrative:
    - name: ""
      role: "Facilitator"
      
communication:
  primary_channel: ""
  backup_channel: ""
  escalation_contact: ""
  
schedule:
  kickoff: "YYYY-MM-DD HH:MM"
  execution_window:
    start: "YYYY-MM-DD HH:MM"
    end: "YYYY-MM-DD HH:MM"
  debrief: "YYYY-MM-DD HH:MM"
```

---

## Technique Scope Template

```yaml
# Exercise Technique Scope
# ------------------------

scope:
  exercise_id: "PT-YYYY-QN-NNN"
  
tactics:
  - id: "TA0007"
    name: "Discovery"
    techniques:
      - id: "T1087.002"
        name: "Domain Account Discovery"
        priority: high
        test_ids: ["ATOMIC-T1087.002-001", "ATOMIC-T1087.002-002"]
        
      - id: "T1069.002"
        name: "Domain Groups"
        priority: high
        test_ids: ["ATOMIC-T1069.002-001"]
        
      - id: "T1018"
        name: "Remote System Discovery"
        priority: medium
        test_ids: ["ATOMIC-T1018-001"]
        
  - id: "TA0006"
    name: "Credential Access"
    techniques:
      - id: "T1003.001"
        name: "LSASS Memory"
        priority: critical
        test_ids: ["ATOMIC-T1003.001-001"]
        exclusions: "No execution on production DC"
        
      - id: "T1003.006"
        name: "DCSync"
        priority: critical
        test_ids: ["ATOMIC-T1003.006-001"]
        exclusions: "Lab environment only"
        
  - id: "TA0008"
    name: "Lateral Movement"
    techniques:
      - id: "T1021.002"
        name: "SMB/Admin Shares"
        priority: high
        test_ids: ["ATOMIC-T1021.002-001"]
        
exclusions:
  global:
    - "No actual malware deployment"
    - "No production data exfiltration"
    - "No denial of service"
  technique_specific:
    T1003.001: "Use only comsvcs.dll method"
    T1003.006: "Single user only, not full domain dump"
```

---

## Test Case Execution Log

```yaml
# Test Case Execution Log
# -----------------------

execution_log:
  exercise_id: "PT-YYYY-QN-NNN"
  date: "YYYY-MM-DD"
  executor: ""
  
tests:
  - test_id: "ATOMIC-T1087.002-001"
    technique: "T1087.002"
    name: "Domain Account Discovery - net.exe"
    
    execution:
      timestamp: "YYYY-MM-DD HH:MM:SS"
      target_host: ""
      source_host: ""
      user_context: ""
      commands_run:
        - "net group \"Domain Admins\" /domain"
        - "net group \"Enterprise Admins\" /domain"
      execution_success: true | false
      notes: ""
      
    outcomes:
      telemetry:
        logged: true | false
        sources:
          - source: "Sysmon"
            event_ids: [1]
            sample_event: ""
          - source: "Windows Security"
            event_ids: [4688]
            sample_event: ""
            
      detection:
        alerted: true | false
        alert_name: ""
        alert_time: "YYYY-MM-DD HH:MM:SS"
        detection_latency_seconds: 
        alert_severity: ""
        alert_fidelity: true_positive | false_positive | unknown
        
      prevention:
        blocked: true | false
        prevention_tool: ""
        block_action: ""
        
    classification: logged | alerted | blocked | missed
    
    action_items:
      - priority: high | medium | low
        description: ""
        assignee: ""
        
    cleanup:
      required: true | false
      completed: true | false
      commands_run: []
```

---

## Results Summary Template

```yaml
# Exercise Results Summary
# ------------------------

summary:
  exercise_id: "PT-YYYY-QN-NNN"
  name: ""
  date: "YYYY-MM-DD"
  methodology: atomic | scenario
  
metrics:
  techniques_tested: 
  techniques_logged: 
  techniques_alerted: 
  techniques_blocked: 
  techniques_missed: 
  
  detection_rate: ""  # alerted / tested
  prevention_rate: ""  # blocked / tested
  visibility_rate: ""  # logged / tested
  
  mean_detection_time_seconds: 
  min_detection_time_seconds: 
  max_detection_time_seconds: 
  
coverage_by_tactic:
  - tactic: "Discovery"
    tested: 
    detected: 
    rate: ""
  - tactic: "Credential Access"
    tested: 
    detected: 
    rate: ""
  - tactic: "Lateral Movement"
    tested: 
    detected: 
    rate: ""
    
gaps_identified:
  critical:
    - technique: ""
      description: ""
      remediation: ""
  high:
    - technique: ""
      description: ""
      remediation: ""
  medium:
    - technique: ""
      description: ""
      remediation: ""
      
detection_improvements:
  - technique: ""
    current_state: ""
    recommended_action: ""
    priority: ""
    estimated_effort: ""
    
telemetry_gaps:
  - data_source: ""
    missing_events: []
    impact: ""
    remediation: ""
```

---

## CSV Export Format

For spreadsheet tracking:

```csv
exercise_id,test_id,technique_id,technique_name,tactic,execution_time,target_host,executor,telemetry_logged,telemetry_sources,alert_fired,alert_name,detection_time_sec,blocked,prevention_tool,classification,notes,action_required
PT-2026-Q1-001,ATOMIC-T1087.002-001,T1087.002,Domain Account Discovery,Discovery,2026-01-28 10:15:00,WORKSTATION01,jsmith,true,"Sysmon,WinSec",true,Domain Enumeration,45,false,,alerted,Alert fired correctly,
PT-2026-Q1-001,ATOMIC-T1003.001-001,T1003.001,LSASS Memory,Credential Access,2026-01-28 10:30:00,WORKSTATION01,jsmith,true,Sysmon,false,,,,missed,Sysmon Event 10 present but no alert,Create LSASS access alert
PT-2026-Q1-001,ATOMIC-T1021.002-001,T1021.002,SMB Admin Shares,Lateral Movement,2026-01-28 10:45:00,WORKSTATION01,jsmith,true,"WinSec,Zeek",true,Lateral Movement Detected,12,true,CrowdStrike,blocked,EDR blocked at network level,
```

---

## VECTR Import Format (ATTiRe)

For VECTR integration:

```json
{
  "attpitre_version": "1.0",
  "execution_data": {
    "execution_id": "PT-2026-Q1-001-001",
    "execution_source": "manual",
    "execution_category": "purple_team",
    "execution_time_start": "2026-01-28T10:15:00Z",
    "execution_time_end": "2026-01-28T10:15:30Z",
    "executing_user": "CORP\\jsmith",
    "target_host": "WORKSTATION01",
    "target_ips": ["10.0.1.100"],
    "attack_technique": "T1087.002",
    "attack_technique_name": "Domain Account Discovery",
    "attack_variant": "net.exe enumeration",
    "test_id": "ATOMIC-T1087.002-001",
    "commands": [
      "net group \"Domain Admins\" /domain"
    ],
    "success": true
  },
  "detection_data": {
    "detected": true,
    "detection_time": "2026-01-28T10:15:45Z",
    "detection_source": "Splunk",
    "detection_rule": "Domain Enumeration Alert",
    "alert_severity": "medium",
    "analyst_notes": "Alert correctly identified domain enumeration activity"
  },
  "prevention_data": {
    "prevented": false,
    "prevention_tool": null,
    "prevention_action": null
  },
  "outcome": "detected"
}
```

---

## Comparison Report Template

Track progress across multiple exercises:

```yaml
# Multi-Exercise Comparison
# -------------------------

comparison:
  exercises:
    - id: "PT-2025-Q4-001"
      date: "2025-10-15"
      techniques_tested: 15
      detection_rate: "60%"
      
    - id: "PT-2026-Q1-001"
      date: "2026-01-28"
      techniques_tested: 18
      detection_rate: "72%"
      
  improvements:
    - technique: "T1087.002"
      q4_2025: missed
      q1_2026: alerted
      change: "New Splunk alert deployed"
      
    - technique: "T1003.001"
      q4_2025: logged
      q1_2026: alerted
      change: "LSASS access detection rule created"
      
  regressions:
    - technique: "T1053.005"
      q4_2025: alerted
      q1_2026: logged
      change: "Alert disabled during SIEM migration"
      action: "Re-enable scheduled task alert"
      
  persistent_gaps:
    - technique: "T1055"
      status: "missed"
      exercises_missed: 2
      blocker: "Sysmon config doesn't capture Event ID 8"
      remediation_owner: ""
      target_date: ""
```

---

## Action Item Tracker

```yaml
# Action Items from Exercise
# --------------------------

action_items:
  exercise_id: "PT-2026-Q1-001"
  
  items:
    - id: "AI-001"
      priority: critical
      category: detection_gap
      technique: "T1003.001"
      title: "Create LSASS access detection rule"
      description: "Sysmon Event ID 10 is logged but no alert exists"
      assignee: ""
      due_date: "YYYY-MM-DD"
      status: open | in_progress | completed | deferred
      completion_date: ""
      verification: "Re-test in next exercise"
      
    - id: "AI-002"
      priority: high
      category: telemetry_gap
      technique: "T1055"
      title: "Enable Sysmon Event ID 8"
      description: "CreateRemoteThread events not being collected"
      assignee: ""
      due_date: "YYYY-MM-DD"
      status: open
      completion_date: ""
      verification: "Confirm events appear in SIEM"
      
    - id: "AI-003"
      priority: medium
      category: alert_tuning
      technique: "T1087.002"
      title: "Increase alert severity for domain enumeration"
      description: "Current INFO severity should be MEDIUM"
      assignee: ""
      due_date: "YYYY-MM-DD"
      status: open
      completion_date: ""
      verification: "Alert fires with correct severity"
      
summary:
  total: 3
  critical: 1
  high: 1
  medium: 1
  completed: 0
  in_progress: 0
  open: 3
```
