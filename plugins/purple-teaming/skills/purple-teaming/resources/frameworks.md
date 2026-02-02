# Security Frameworks Quick Reference

## MITRE ATT&CK

### Object Identifiers

| Type | Format | Example |
|------|--------|---------|
| Tactic | TAxxxx | TA0001 (Initial Access) |
| Technique | Txxxx | T1566 (Phishing) |
| Subtechnique | Txxxx.xxx | T1566.001 (Spearphishing Attachment) |
| Group | Gxxxx | G0016 (APT29) |
| Software | Sxxxx | S0154 (Cobalt Strike) |
| Campaign | Cxxxx | C0024 (SolarWinds) |
| Mitigation | Mxxxx | M1049 (Antivirus/Antimalware) |
| Data Source | DSxxxx | DS0009 (Process) |

### Enterprise Tactics (Ordered)

1. **TA0043** - Reconnaissance
2. **TA0042** - Resource Development
3. **TA0001** - Initial Access
4. **TA0002** - Execution
5. **TA0003** - Persistence
6. **TA0004** - Privilege Escalation
7. **TA0005** - Defense Evasion
8. **TA0006** - Credential Access
9. **TA0007** - Discovery
10. **TA0008** - Lateral Movement
11. **TA0009** - Collection
12. **TA0011** - Command and Control
13. **TA0010** - Exfiltration
14. **TA0040** - Impact

### Companion Tools

- **ATT&CK Navigator**: Layer visualization, coverage heatmaps
- **D3FEND**: Defensive technique countermeasures
- **CAR (Cyber Analytics Repository)**: Detection pseudocode

---

## Cyber Kill Chain (Lockheed Martin)

Seven sequential phases:

```
1. Reconnaissance    → Gather target information
         ↓
2. Weaponization     → Create deliverable payload
         ↓
3. Delivery          → Transmit to target (email, USB, web)
         ↓
4. Exploitation      → Trigger vulnerability
         ↓
5. Installation      → Establish persistence
         ↓
6. Command & Control → Establish communication channel
         ↓
7. Actions on Objectives → Achieve mission goal
```

### Key Insight

- Earlier detection = lower remediation cost
- Defenders work backward from detection point
- Breaking any link disrupts the chain

### Mapping to ATT&CK

| Kill Chain Phase | ATT&CK Tactics |
|------------------|----------------|
| Reconnaissance | Reconnaissance |
| Weaponization | Resource Development |
| Delivery | Initial Access |
| Exploitation | Initial Access, Execution |
| Installation | Persistence, Defense Evasion |
| C2 | Command and Control |
| Actions on Objectives | Collection, Exfiltration, Impact |

---

## Diamond Model of Intrusion Analysis

### Core Features (Vertices)

```
        Adversary
           ↑
           |
    [Meta-Features]
           |
Infrastructure ←─→ Capability
           |
           |
           ↓
         Victim
```

**Adversary Types:**
- Operator: Hands-on-keyboard attacker
- Customer: Entity directing the operation

**Infrastructure Types:**
- Type 1: Adversary-owned (bulletproof hosting, VPS)
- Type 2: Compromised legitimate infrastructure
- Service Providers: Third-party services abused

**Capability Elements:**
- Arsenal: Available tools and techniques
- Capacity: Resources to develop/acquire capabilities

**Victim Elements:**
- Assets: Systems, networks, data
- Persona: Identity attributes (employee, admin)
- Susceptibilities: Vulnerabilities, misconfigurations

### Meta-Features

| Feature | Description |
|---------|-------------|
| Timestamp | When the event occurred |
| Phase | Kill Chain phase |
| Result | Success, failure, unknown |
| Direction | i2v, v2i, i2i, bidirectional |
| Methodology | General class of activity |
| Resources | Required assets (software, hardware, funds) |

### Extended Model

- **Social-Political**: Adversary-victim relationship (nation-state, competitor, hacktivist)
- **Technology**: Infrastructure-capability relationship (how tools leverage infrastructure)

### Analytic Pivoting

Start from known vertex, pivot to discover unknowns:

| Starting Point | Pivot Direction |
|----------------|-----------------|
| Victim-centric | What assets targeted? What susceptibilities exploited? |
| Capability-centric | What tools used? What techniques employed? |
| Infrastructure-centric | What IPs/domains? What hosting providers? |
| Adversary-centric | Who is the operator? Who is the customer? |

### Activity Threads

Chain of diamond events forming attack timeline:

```
Event 1 → Event 2 → Event 3 → ... → Event N
(Phishing) (Execution) (Discovery)    (Exfil)
```

---

## Pyramid of Pain (David Bianco)

Defensive impact on adversary operations (bottom = easiest to change):

```
                    ╱╲
                   ╱  ╲
                  ╱TTPs╲          ← TOUGH
                 ╱──────╲
                ╱ Tools  ╲        ← CHALLENGING
               ╱──────────╲
              ╱  Network/  ╲      ← ANNOYING
             ╱    Host      ╲
            ╱   Artifacts    ╲
           ╱──────────────────╲
          ╱   Domain Names     ╲  ← SIMPLE
         ╱──────────────────────╲
        ╱     IP Addresses       ╲ ← EASY
       ╱──────────────────────────╲
      ╱         Hashes             ╲← TRIVIAL
     ╱──────────────────────────────╲
```

### Detection Strategy by Level

| Level | Example Indicators | Adversary Response |
|-------|-------------------|-------------------|
| **Hashes** | MD5, SHA256 of malware | Recompile (seconds) |
| **IP Addresses** | C2 server IPs | Rotate infrastructure (minutes) |
| **Domain Names** | Phishing domains | Register new domains (hours) |
| **Network/Host Artifacts** | User agents, file paths, registry keys | Modify tools (days) |
| **Tools** | Cobalt Strike signatures, Mimikatz patterns | Develop new tools (weeks) |
| **TTPs** | Technique-level behavior | Change tradecraft (months/years) |

### Application

1. **Layer detections** across all levels
2. **Prioritize TTP-level** detections for highest impact
3. **Combine indicators** for robust detection
4. **Track adversary adaptation** to understand their pain threshold

---

## Framework Integration Example

Scenario: Phishing campaign delivers Cobalt Strike

**ATT&CK Mapping:**
- T1566.001 (Spearphishing Attachment)
- T1059.001 (PowerShell)
- T1071.001 (Web Protocols)

**Kill Chain Position:**
- Delivery → Exploitation → C2

**Diamond Model:**
- Adversary: Unknown threat actor
- Capability: Cobalt Strike beacon
- Infrastructure: cdn.legitimate-looking[.]com
- Victim: Finance department users

**Pyramid of Pain Coverage:**
- Hash: Beacon DLL hash (trivial to change)
- IP: C2 server IP (easy to rotate)
- Domain: cdn.legitimate-looking[.]com (simple)
- Artifact: User-Agent string, named pipe (annoying)
- Tool: Cobalt Strike malleable C2 signature (challenging)
- TTP: PowerShell download cradle → beacon behavior (tough)

**Detection Recommendation:** Focus on TTP-level detection (PowerShell spawned by Office, beacon sleep/jitter patterns) rather than IOC-based detection (hashes, IPs).
