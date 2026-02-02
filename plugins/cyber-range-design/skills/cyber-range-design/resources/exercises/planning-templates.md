# Exercise Planning Templates

Templates for planning, executing, and evaluating cyber range exercises.

## Exercise Planning Document Template

```yaml
# ============================================================================
# CYBER RANGE EXERCISE PLAN
# ============================================================================

exercise_metadata:
  name: "[Exercise Name]"
  codename: "[Optional Codename]"
  version: "1.0"
  classification: "UNCLASSIFIED"  # Or appropriate marking
  
  dates:
    planning_start: "YYYY-MM-DD"
    exercise_start: "YYYY-MM-DD"
    exercise_end: "YYYY-MM-DD"
    hot_wash: "YYYY-MM-DD"
    final_report_due: "YYYY-MM-DD"
    
  stakeholders:
    sponsor: "[Name/Org]"
    exercise_director: "[Name]"
    technical_lead: "[Name]"
    white_team_lead: "[Name]"
    red_team_lead: "[Name]"

# ----------------------------------------------------------------------------
# EXERCISE OBJECTIVES
# ----------------------------------------------------------------------------

objectives:
  primary:
    - id: OBJ-001
      description: "[Primary objective 1]"
      success_criteria: "[Measurable criteria]"
      priority: critical
      
    - id: OBJ-002
      description: "[Primary objective 2]"
      success_criteria: "[Measurable criteria]"
      priority: critical
      
  secondary:
    - id: OBJ-003
      description: "[Secondary objective]"
      success_criteria: "[Measurable criteria]"
      priority: high
      
  training_objectives:
    - "[Specific skill to develop]"
    - "[Procedure to validate]"
    - "[Capability to assess]"

# ----------------------------------------------------------------------------
# EXERCISE SCENARIO
# ----------------------------------------------------------------------------

scenario:
  background: |
    [Narrative describing the fictional organization, its industry, 
    recent events leading up to the exercise, and threat landscape]
    
  organization_profile:
    name: "[Fictional Organization Name]"
    industry: "[Industry Sector]"
    size: "[Employee count, revenue, etc.]"
    geography: "[Locations]"
    
  threat_actor_profile:
    name: "[Threat Actor Name/Designation]"
    type: "[APT/Criminal/Hacktivist/Insider]"
    sophistication: "[Script Kiddie/Intermediate/Advanced/Nation-State]"
    motivation: "[Financial/Espionage/Disruption/Ideological]"
    known_ttps:
      - "[MITRE ATT&CK Technique]"
      - "[MITRE ATT&CK Technique]"
      
  attack_narrative: |
    [High-level description of the attack sequence without revealing
    specific technical details that would advantage blue team]

# ----------------------------------------------------------------------------
# PARTICIPANT STRUCTURE
# ----------------------------------------------------------------------------

participants:
  blue_teams:
    - team_id: "BLUE-1"
      name: "[Team Name]"
      organization: "[Real Org]"
      size: 8-12
      role: "Defenders"
      enclave: "Team1-Blue-Zone"
      
    - team_id: "BLUE-2"
      name: "[Team Name]"
      organization: "[Real Org]"
      size: 8-12
      role: "Defenders"
      enclave: "Team2-Blue-Zone"
      
  red_team:
    team_id: "RED-1"
    name: "[Red Team Name]"
    organization: "[Provider]"
    size: 4-6
    role: "Adversary Emulation"
    
  white_team:
    team_id: "WHITE-1"
    name: "Exercise Control"
    size: 6-10
    roles:
      - exercise_director
      - technical_controller
      - inject_coordinator
      - scoring_administrator
      - communications_lead
      - range_support

# ----------------------------------------------------------------------------
# RULES OF ENGAGEMENT
# ----------------------------------------------------------------------------

rules_of_engagement:
  general:
    - "All activity must remain within designated range boundaries"
    - "No denial-of-service attacks against range infrastructure"
    - "No attacks against out-of-game systems"
    - "Maintain exercise classification at all times"
    
  red_team_constraints:
    authorized:
      - "Exploitation of known vulnerabilities"
      - "Phishing within exercise email system"
      - "Lateral movement within blue team enclaves"
      - "Data exfiltration to red zone infrastructure"
    prohibited:
      - "Attacks against white/access/metrics zones"
      - "Cross-team attacks (unless scenario dictates)"
      - "Real-world reconnaissance"
      - "Physical security attacks"
      
  blue_team_constraints:
    authorized:
      - "Defensive actions within own enclave"
      - "Threat hunting and detection"
      - "Incident response procedures"
      - "Coordination via approved channels"
    prohibited:
      - "Offensive operations against red zone"
      - "Accessing other team enclaves"
      - "Contacting external resources"
      
  safety_protocols:
    - condition: "SAFEGUARD"
      description: "Pause exercise for safety concern"
      authority: "Any participant"
      
    - condition: "ENDEX"
      description: "Terminate exercise"
      authority: "Exercise Director only"

# ----------------------------------------------------------------------------
# EXERCISE SCHEDULE
# ----------------------------------------------------------------------------

schedule:
  pre_exercise:
    - event: "Participant briefing"
      date: "T-7 days"
      duration: "2 hours"
      
    - event: "Range access verification"
      date: "T-3 days"
      duration: "4 hours"
      
    - event: "Blue team familiarization"
      date: "T-1 day"
      duration: "4 hours"
      
  exercise_timeline:
    day_1:
      - time: "0800"
        event: "Exercise start (STARTEX)"
        
      - time: "0830"
        event: "Initial inject - suspicious activity reported"
        inject_id: "INJ-001"
        
      - time: "1200"
        event: "Lunch break (exercise continues)"
        
      - time: "1400"
        event: "Inject - escalation event"
        inject_id: "INJ-002"
        
      - time: "1700"
        event: "Day 1 end (overnight persistence)"
        
    day_2:
      - time: "0800"
        event: "Day 2 start"
        
      - time: "0900"
        event: "Inject - major incident"
        inject_id: "INJ-003"
        
      - time: "1500"
        event: "Exercise end (ENDEX)"
        
      - time: "1530"
        event: "Hot wash"
        duration: "2 hours"

# ----------------------------------------------------------------------------
# INJECT PLAN
# ----------------------------------------------------------------------------

injects:
  - inject_id: "INJ-001"
    time: "D1-0830"
    type: "scenario"
    title: "Suspicious email reported"
    description: |
      IT help desk receives report of suspicious email from employee.
      Email contains malicious attachment.
    delivery_method: "White team role player"
    expected_response: "Triage, analysis, initial containment"
    success_criteria:
      - "Identify malicious attachment within 30 min"
      - "Isolate affected workstation"
      - "Begin indicator extraction"
      
  - inject_id: "INJ-002"
    time: "D1-1400"
    type: "escalation"
    title: "Lateral movement detected"
    description: |
      SIEM alert fires on suspicious authentication pattern.
      Attacker has moved to secondary system.
    delivery_method: "Automated SIEM alert"
    expected_response: "Scope assessment, network containment"
    success_criteria:
      - "Identify compromised accounts"
      - "Implement network segmentation"
      - "Begin threat hunting"
      
  - inject_id: "INJ-003"
    time: "D2-0900"
    type: "crisis"
    title: "Data exfiltration in progress"
    description: |
      Large data transfer detected to external IP.
      Evidence of database access.
    delivery_method: "Network alert + White team notification"
    expected_response: "Emergency response, executive notification"
    success_criteria:
      - "Stop active exfiltration"
      - "Preserve forensic evidence"
      - "Initiate crisis communication"

# ----------------------------------------------------------------------------
# SCORING CRITERIA
# ----------------------------------------------------------------------------

scoring:
  methodology: "Weighted objective scoring"
  
  categories:
    - category: "Detection"
      weight: 25
      criteria:
        - item: "Initial compromise detection"
          points: 100
        - item: "Lateral movement detection"
          points: 100
        - item: "Exfiltration detection"
          points: 100
          
    - category: "Response"
      weight: 30
      criteria:
        - item: "Containment effectiveness"
          points: 100
        - item: "Eradication completeness"
          points: 100
        - item: "Recovery time"
          points: 100
          
    - category: "Process"
      weight: 25
      criteria:
        - item: "Communication quality"
          points: 100
        - item: "Documentation"
          points: 100
        - item: "Escalation appropriateness"
          points: 100
          
    - category: "Technical Depth"
      weight: 20
      criteria:
        - item: "Indicator extraction"
          points: 100
        - item: "Root cause analysis"
          points: 100
        - item: "Attack chain reconstruction"
          points: 100

# ----------------------------------------------------------------------------
# COMMUNICATIONS PLAN
# ----------------------------------------------------------------------------

communications:
  channels:
    primary:
      tool: "[Slack/Teams/Mattermost]"
      server: "[URL]"
      channels:
        - "#exercise-all" # General announcements
        - "#white-team" # Exercise control
        - "#blue-team-1" # Team-specific
        - "#blue-team-2"
        - "#red-team"
        
    backup:
      tool: "Radio"
      frequencies:
        white_team: "Channel 1"
        emergency: "Channel 9"
        
  reporting_requirements:
    blue_teams:
      - report: "Status update"
        frequency: "Every 2 hours"
        format: "SITREP template"
        
      - report: "Incident report"
        trigger: "Upon detection"
        format: "Incident template"
        
    white_team:
      - report: "Exercise status"
        frequency: "Every 4 hours"
        audience: "Stakeholders"

# ----------------------------------------------------------------------------
# LOGISTICS
# ----------------------------------------------------------------------------

logistics:
  facilities:
    - location: "[Primary Location]"
      purpose: "Exercise control center"
      capacity: 20
      
    - location: "[Team Room 1]"
      purpose: "Blue Team 1"
      capacity: 15
      
  equipment:
    provided:
      - "Workstations with range access"
      - "Network connectivity"
      - "Communication headsets"
      
    participant_supplied:
      - "Personal tools (if approved)"
      - "Reference materials"
      
  catering:
    - "Breakfast: 0730-0800"
    - "Lunch: 1200-1300"
    - "Snacks available throughout"
    
  parking:
    location: "[Parking info]"
    instructions: "[Access instructions]"

# ----------------------------------------------------------------------------
# RISK MANAGEMENT
# ----------------------------------------------------------------------------

risks:
  - risk_id: "RISK-001"
    description: "Range infrastructure failure"
    probability: low
    impact: high
    mitigation: "Redundant systems, tested failover"
    contingency: "Pause exercise, repair, resume"
    
  - risk_id: "RISK-002"
    description: "Participant unavailability"
    probability: medium
    impact: medium
    mitigation: "Backup personnel identified"
    contingency: "Redistribute responsibilities"
    
  - risk_id: "RISK-003"
    description: "Scenario too difficult/easy"
    probability: medium
    impact: medium
    mitigation: "Calibrated inject timing"
    contingency: "White team adjusts pace"
```

## Situation Report (SITREP) Template

```markdown
# SITUATION REPORT (SITREP)

**Team:** [Team Name]
**Report Number:** [#]
**Date/Time:** [YYYY-MM-DD HH:MM]
**Classification:** EXERCISE

---

## 1. CURRENT SITUATION

### 1.1 Incident Summary
[Brief description of current incident status]

### 1.2 Timeline of Events
| Time | Event |
|------|-------|
| [HH:MM] | [Event description] |
| [HH:MM] | [Event description] |

### 1.3 Systems Affected
- [ ] Workstations: [Count/Names]
- [ ] Servers: [Count/Names]
- [ ] Network Segments: [List]
- [ ] Applications: [List]

---

## 2. ACTIONS TAKEN

### 2.1 Completed Actions
- [Action 1]
- [Action 2]

### 2.2 Actions In Progress
- [Action 1] - ETA: [Time]
- [Action 2] - ETA: [Time]

### 2.3 Planned Actions
- [Action 1]
- [Action 2]

---

## 3. INDICATORS OF COMPROMISE (IOCs)

| Type | Value | Confidence |
|------|-------|------------|
| IP Address | [x.x.x.x] | [High/Med/Low] |
| Domain | [domain.com] | [High/Med/Low] |
| File Hash | [SHA256] | [High/Med/Low] |
| User Account | [username] | [High/Med/Low] |

---

## 4. RESOURCE STATUS

### 4.1 Personnel
- Available: [#]
- Engaged: [#]
- Fatigue Level: [Green/Yellow/Red]

### 4.2 Tools/Systems
- SIEM: [Operational/Degraded/Down]
- EDR: [Operational/Degraded/Down]
- Network Sensors: [Operational/Degraded/Down]

---

## 5. REQUESTS/NEEDS

- [Request 1]
- [Request 2]

---

## 6. NEXT REPORT

**Scheduled:** [YYYY-MM-DD HH:MM]

---

**Submitted By:** [Name]
**Approved By:** [Team Lead]
```

## Incident Report Template

```markdown
# INCIDENT REPORT

**Incident ID:** [INC-YYYY-###]
**Team:** [Team Name]
**Date/Time Detected:** [YYYY-MM-DD HH:MM]
**Classification:** EXERCISE

---

## 1. INCIDENT OVERVIEW

### 1.1 Summary
[One paragraph summary of the incident]

### 1.2 Classification
- **Category:** [Malware/Intrusion/Data Breach/Other]
- **Severity:** [Critical/High/Medium/Low]
- **Status:** [Open/Contained/Eradicated/Recovered/Closed]

---

## 2. DETECTION

### 2.1 Detection Method
- [ ] SIEM Alert
- [ ] EDR Alert
- [ ] User Report
- [ ] Network Sensor
- [ ] Threat Hunt
- [ ] Other: [Specify]

### 2.2 Initial Indicators
[Description of what was initially observed]

### 2.3 Detection Timeline
| Time | Source | Observation |
|------|--------|-------------|
| [HH:MM] | [Source] | [What was seen] |

---

## 3. ANALYSIS

### 3.1 Attack Vector
[How did the attacker gain initial access?]

### 3.2 Attack Chain
```
[Phase 1: Initial Access]
    └── [Technique used]
        └── [Phase 2: Execution]
            └── [Technique used]
                └── [Phase 3: ...]
```

### 3.3 MITRE ATT&CK Mapping
| Tactic | Technique | Technique ID |
|--------|-----------|--------------|
| [Tactic] | [Technique] | [T####] |

### 3.4 Scope Assessment
- **Users Affected:** [#]
- **Systems Affected:** [#]
- **Data at Risk:** [Description]

---

## 4. INDICATORS OF COMPROMISE

### 4.1 Network Indicators
| Indicator | Value | Notes |
|-----------|-------|-------|
| Source IP | [x.x.x.x] | [Country/ASN] |
| Dest IP | [x.x.x.x] | [Purpose] |
| Domain | [domain] | [Registration info] |

### 4.2 Host Indicators
| Indicator | Value | Notes |
|-----------|-------|-------|
| File Hash (SHA256) | [hash] | [Filename] |
| File Path | [path] | [Purpose] |
| Registry Key | [key] | [Persistence] |
| Process | [name] | [Behavior] |

### 4.3 Behavioral Indicators
- [Behavior pattern 1]
- [Behavior pattern 2]

---

## 5. RESPONSE ACTIONS

### 5.1 Containment
| Action | Time | Result |
|--------|------|--------|
| [Action taken] | [HH:MM] | [Outcome] |

### 5.2 Eradication
| Action | Time | Result |
|--------|------|--------|
| [Action taken] | [HH:MM] | [Outcome] |

### 5.3 Recovery
| System | Action | Status |
|--------|--------|--------|
| [System] | [Rebuild/Restore/Patch] | [Complete/In Progress] |

---

## 6. LESSONS LEARNED

### 6.1 What Worked Well
- [Item 1]
- [Item 2]

### 6.2 Areas for Improvement
- [Item 1]
- [Item 2]

### 6.3 Recommendations
- [Recommendation 1]
- [Recommendation 2]

---

## 7. EVIDENCE PRESERVATION

| Evidence Type | Location | Chain of Custody |
|---------------|----------|------------------|
| [Memory dump] | [Path] | [Handler] |
| [Disk image] | [Path] | [Handler] |
| [Log export] | [Path] | [Handler] |

---

**Report Prepared By:** [Name]
**Date:** [YYYY-MM-DD]
**Reviewed By:** [Name]
```

## Post-Exercise Hot Wash Template

```markdown
# POST-EXERCISE HOT WASH

**Exercise:** [Exercise Name]
**Date:** [YYYY-MM-DD]
**Facilitator:** [Name]
**Attendees:** [List]

---

## 1. EXERCISE SUMMARY

### 1.1 Objectives Achievement
| Objective | Status | Notes |
|-----------|--------|-------|
| [OBJ-001] | [Met/Partial/Not Met] | [Comments] |
| [OBJ-002] | [Met/Partial/Not Met] | [Comments] |

### 1.2 Key Statistics
- **Duration:** [X hours]
- **Participants:** [#]
- **Injects Executed:** [#]
- **Incidents Detected:** [#]

---

## 2. PARTICIPANT FEEDBACK

### 2.1 Blue Teams

**What worked well?**
- [Feedback item]
- [Feedback item]

**What could be improved?**
- [Feedback item]
- [Feedback item]

**Range/Environment feedback:**
- [Feedback item]

### 2.2 Red Team

**Challenges encountered:**
- [Item]

**Blue team strengths observed:**
- [Item]

**Blue team gaps observed:**
- [Item]

### 2.3 White Team

**Exercise execution feedback:**
- [Item]

**Logistical issues:**
- [Item]

---

## 3. SUSTAINS (Keep Doing)

| Item | Owner | Notes |
|------|-------|-------|
| [What to continue] | [Who] | [Why effective] |

---

## 4. IMPROVES (Change/Add)

| Item | Owner | Priority | Notes |
|------|-------|----------|-------|
| [What to change] | [Who] | [H/M/L] | [How to improve] |

---

## 5. ACTION ITEMS

| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| [Action] | [Name] | [Date] | [Open] |

---

## 6. NEXT STEPS

- [ ] Finalize scoring
- [ ] Distribute after-action report
- [ ] Schedule follow-up training
- [ ] Implement process improvements
- [ ] Plan next exercise

---

**Notes:** [Additional observations]
```

## Range Design Document Template

```markdown
# CYBER RANGE DESIGN DOCUMENT

**Document Version:** [1.0]
**Date:** [YYYY-MM-DD]
**Author:** [Name]
**Status:** [Draft/Review/Approved]

---

## 1. EXECUTIVE SUMMARY

[One-page summary of range purpose, scope, and key characteristics]

---

## 2. REQUIREMENTS

### 2.1 Use Cases
| Use Case | Description | Frequency |
|----------|-------------|-----------|
| [UC-001] | [Description] | [Weekly/Monthly/Quarterly] |

### 2.2 Capacity Requirements
- **Concurrent Users:** [#]
- **Team Enclaves:** [#]
- **Total VMs:** [#]

### 2.3 Fidelity Requirements
[Description of required realism level]

### 2.4 Constraints
- **Budget:** [$X]
- **Timeline:** [X months]
- **Staffing:** [X FTEs]
- **Compliance:** [Requirements]

---

## 3. ARCHITECTURE

### 3.1 Zone Design
[Include zone diagram]

### 3.2 Network Topology
[Include network diagram]

### 3.3 VM Inventory
| Zone | VM Name | OS | Resources | Purpose |
|------|---------|-----|-----------|---------|
| [Zone] | [Name] | [OS] | [vCPU/RAM/Disk] | [Purpose] |

### 3.4 Network Addressing
[IP addressing scheme]

---

## 4. INFRASTRUCTURE

### 4.1 Compute
[Hardware specifications]

### 4.2 Storage
[Storage specifications]

### 4.3 Network
[Network specifications]

---

## 5. IMPLEMENTATION PLAN

### 5.1 Phase 1: Foundation
[Tasks, timeline, resources]

### 5.2 Phase 2: Core Services
[Tasks, timeline, resources]

### 5.3 Phase 3: Full Deployment
[Tasks, timeline, resources]

---

## 6. OPERATIONS

### 6.1 Staffing Model
[Required roles and responsibilities]

### 6.2 Maintenance Procedures
[Regular maintenance tasks]

### 6.3 Reset Procedures
[How to reset the range]

---

## 7. COST ESTIMATE

| Category | Initial | Annual | Notes |
|----------|---------|--------|-------|
| Hardware | $X | $X | [Details] |
| Software | $X | $X | [Details] |
| Personnel | $X | $X | [Details] |
| **Total** | **$X** | **$X** | |

---

## 8. RISKS

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| [Risk] | [H/M/L] | [H/M/L] | [Mitigation] |

---

## 9. APPROVALS

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Technical Lead | | | |
| Project Sponsor | | | |
| Security | | | |
```
