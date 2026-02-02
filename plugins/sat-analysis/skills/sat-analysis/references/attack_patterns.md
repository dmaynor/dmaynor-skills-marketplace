# Attack Patterns Reference

## Initial Access

### Spearphishing
**Indicators**:
- Email from external with attachment/link
- Macro-enabled document execution
- Child process from Office/email client
- Outbound connection after document open

**False Positives**: Legitimate macros, marketing tracking, automated email processing

### Valid Credentials
**Indicators**:
- Auth from unusual location/time
- No prior failed attempts (unlike brute force)
- Immediate resource access after login
- VPN/remote access usage

**Distinguishing**: User denies login, concurrent sessions from different locations, pattern differs from baseline

**False Positives**: User traveling, new device, VPN exit changes

### Brute Force
**Indicators**:
- Many failed auth attempts (>10 in short window)
- Same source, multiple targets OR same target, multiple sources
- Automated timing pattern (consistent intervals)
- Eventually successful after failures

**False Positives**: Forgotten password, misconfigured service, password manager sync

### Exploitation of Public App
**Indicators**:
- Unusual web/app requests
- Error spikes → successful unusual requests
- Process spawned by web server
- File writes by web server process

**False Positives**: Authorized scanners, app bugs, security team fuzzing

---

## Execution

### PowerShell Abuse
**Indicators**:
- Encoded commands (`-enc`, `-e`)
- Download cradles (`IEX`, `DownloadString`, `Invoke-WebRequest`)
- Spawned by unusual parent (Office, wscript, cscript)
- Execution policy bypass (`-ep bypass`)
- Hidden window (`-w hidden`)

**Key Evidence**: Decoded command content, download destination, subsequent processes

**False Positives**: IT admin scripts, software installation, config management

### Living-off-the-Land
**Common LOLBins**:
| Tool | Suspicious Use |
|------|----------------|
| certutil | `-urlcache -f` (download) |
| bitsadmin | `/transfer` (download) |
| regsvr32 | `/s /n /u /i:URL` (execute) |
| mshta | URL execution |
| rundll32 | DLL execution |
| wmic | Process creation |

**False Positives**: Sysadmin tasks, software deployment, troubleshooting

### Script Execution
**Indicators**:
- wscript/cscript with external files
- VBScript/JScript from unusual locations
- Script downloads or creates executables

---

## Persistence

### Scheduled Tasks
**Indicators**:
- Task created (especially via CLI: `schtasks`)
- Runs from unusual path (`\Temp`, `\AppData`, `\ProgramData`)
- SYSTEM or elevated privileges
- Unusual schedule (boot, logon, frequent)

**Key Evidence**: Creator identity, executable content, schedule timing

**False Positives**: Software installation, IT automation, backup tools

### Registry Run Keys
**Locations**:
```
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
HKLM\Software\Microsoft\Windows\CurrentVersion\Run
HKCU\...\RunOnce
HKLM\...\RunOnce
```

**Indicators**: Modification by unusual process, executable in unusual path

**False Positives**: Software installation, updates, user customization

### Services
**Indicators**:
- New service created
- Service binary in unusual location
- Service runs as SYSTEM
- Service name mimics legitimate services

---

## Credential Access

### Credential Dumping
**Indicators**:
- LSASS access (especially by non-security tools)
- Mimikatz signatures
- SAM/SECURITY/SYSTEM registry hive access
- NTDS.dit access (domain controllers)

**Tools**: mimikatz, procdump, comsvcs.dll, secretsdump

### Kerberoasting
**Indicators**:
- TGS requests for many SPNs
- RC4 encryption requested (downgrade)
- Single source requesting multiple service tickets

---

## Discovery

### Network Scanning
**Indicators**:
- Connections to many IPs in short time
- Sequential port scanning
- ICMP sweeps
- Common scan tool artifacts

**False Positives**: Legitimate network management, monitoring tools

### Account Discovery
**Indicators**:
- net user/group/localgroup commands
- LDAP queries for all users/groups
- whoami /all, nltest

---

## Lateral Movement

### Remote Services
**Indicators**:
- PsExec/similar tool usage
- Remote service creation
- WMI remote execution
- WinRM connections

**Key Evidence**: Source/destination relationship, credential used, payload

### Pass-the-Hash/Ticket
**Indicators**:
- NTLM auth from unusual source
- Kerberos ticket from unusual source
- Credential reuse across systems

---

## Exfiltration

### Data Staging
**Indicators**:
- Large file copies to single location
- Archive creation (zip, rar, 7z)
- Sensitive directory access → archive
- Unusual volume of file reads

**False Positives**: Backups, project archival, legitimate transfers

### Exfiltration Over Web
**Indicators**:
- Unusual outbound data volume
- File sharing sites (mega, dropbox, gdrive)
- HTTP POST with large body
- Cloud storage sync from unusual paths

**Key Evidence**: Destination reputation, volume vs baseline, timing, user authorization

**False Positives**: Authorized cloud storage, updates, video calls, legitimate uploads

---

## Command and Control

### Beaconing
**Indicators**:
- Regular interval connections (±jitter)
- Consistent destination
- Small outbound, variable inbound
- Unusual user-agent or headers

**Analysis**: Calculate interval consistency, check destination reputation

### DNS Tunneling
**Indicators**:
- Long DNS queries (>50 chars)
- High volume of DNS to single domain
- Unusual query types (TXT, NULL)
- Base64/hex-like subdomains

### Encrypted Channels
**Indicators**:
- HTTPS to unusual destinations
- Non-standard ports (443 on non-443)
- Certificate anomalies

---

## MITRE ATT&CK Quick Reference

| Tactic | Key Techniques | Primary Log Sources |
|--------|---------------|---------------------|
| Initial Access | T1566 (Phishing), T1078 (Valid Accounts) | Email, Auth |
| Execution | T1059 (Scripting), T1204 (User Execution) | Process, CLI |
| Persistence | T1053 (Scheduled Task), T1547 (Boot/Logon) | Task, Registry |
| Priv Esc | T1548 (Abuse Elevation), T1134 (Token) | Security Events |
| Defense Evasion | T1027 (Obfuscation), T1070 (Indicator Removal) | Process, File |
| Cred Access | T1003 (OS Credential Dump), T1110 (Brute Force) | Auth, LSASS |
| Discovery | T1087 (Account), T1046 (Network Scan) | Process, Network |
| Lateral Movement | T1021 (Remote Services), T1550 (Alt Auth) | Auth, Network |
| Collection | T1005 (Local Data), T1114 (Email) | File Access |
| Exfiltration | T1041 (C2 Channel), T1567 (Web Service) | Network, DLP |
| C2 | T1071 (App Layer), T1095 (Non-App Layer) | Network, DNS |

---

## Kill Chain Mapping

```
RECON → WEAPONIZE → DELIVER → EXPLOIT → INSTALL → C2 → ACTIONS
  |         |          |         |         |       |       |
  |         |          |         |         |       |       └─ Exfil/Impact
  |         |          |         |         |       └─ Beaconing, tunneling
  |         |          |         |         └─ Persistence, backdoor
  |         |          |         └─ Code execution, priv esc
  |         |          └─ Phishing, exploit delivery
  |         └─ Malware creation (rarely visible)
  └─ Scanning, OSINT (often pre-attack)
```

**Analysis Tip**: Map observed indicators to kill chain phases. Multiple phases = higher confidence of compromise.
