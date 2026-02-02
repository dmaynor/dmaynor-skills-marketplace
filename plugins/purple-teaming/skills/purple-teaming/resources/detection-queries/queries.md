# Detection Query Templates

Ready-to-use detection queries for purple team exercises.

---

## Splunk SPL Queries

### Discovery Detection

#### Burst Reconnaissance Detection
```spl
index=sysmon EventCode=1 
Image IN ("*\\net.exe", "*\\nltest.exe", "*\\dsquery.exe", "*\\whoami.exe", "*\\systeminfo.exe", "*\\ipconfig.exe", "*\\nbtstat.exe", "*\\arp.exe", "*\\route.exe")
| bin _time span=60s
| stats count values(Image) as tools dc(Image) as tool_count by _time, ComputerName, User
| where count > 5 OR tool_count > 3
| eval severity=case(count>10, "high", count>5, "medium", 1=1, "low")
```

#### Domain Enumeration via net.exe
```spl
index=sysmon EventCode=1 Image="*\\net.exe"
| rex field=CommandLine "(?i)(group|user|localgroup|view|share|accounts|time)"
| where isnotnull(match)
| stats count values(CommandLine) as commands by ComputerName, User
| where count > 3
```

#### LDAP Query Monitoring (Kerberoasting/Delegation)
```spl
index=wineventlog sourcetype="WinEventLog:Directory Service" EventCode=1644
| rex field=SearchFilter "(?<query_type>servicePrincipalName|userAccountControl|msDS-AllowedToDelegateTo)"
| where isnotnull(query_type)
| stats count by query_type, ClientIP, User
```

### Credential Access Detection

#### LSASS Access (High-Fidelity)
```spl
index=sysmon EventCode=10 TargetImage="*\\lsass.exe"
| where NOT match(SourceImage, "(?i)(csrss|wininit|services|MsMpEng|svchost|lsass|System)\.exe$")
| eval access_type=case(
    GrantedAccess="0x1fffff", "FULL_ACCESS",
    GrantedAccess="0x1410", "QUERY_READ",
    GrantedAccess="0x1010", "QUERY_LIMITED",
    GrantedAccess="0x143a", "COMMON_DUMP",
    1=1, "OTHER"
)
| where access_type IN ("FULL_ACCESS", "COMMON_DUMP")
| table _time, ComputerName, SourceImage, GrantedAccess, access_type
```

#### DCSync Detection (Network-Based)
```spl
index=zeek sourcetype=zeek_dce_rpc 
operation IN ("DRSGetNCChanges", "DsGetDomainControllerInfo", "DRSReplicaSync")
| lookup dc_inventory ip AS id.orig_h OUTPUT is_dc, hostname
| where is_dc!="true" OR isnull(is_dc)
| table _time, id.orig_h, id.resp_h, operation, hostname
| rename id.orig_h as source_ip, id.resp_h as dc_ip
```

#### Kerberoasting Detection
```spl
index=wineventlog sourcetype="WinEventLog:Security" EventCode=4769 
ServiceName!="krbtgt" ServiceName!="*$" 
TicketEncryptionType="0x17"
| stats count by TargetUserName, ServiceName, IpAddress
| where count > 3
| rename IpAddress as source_ip
```

### Execution Detection

#### Encoded PowerShell Commands
```spl
index=sysmon EventCode=1 Image="*\\powershell.exe"
| where match(CommandLine, "(?i)(-enc|-e\s|-encodedcommand|-ec\s)")
| eval decoded=if(match(CommandLine, "(?i)-enc"), "true", "false")
| table _time, ComputerName, User, ParentImage, CommandLine
```

#### MSBuild/Trusted Binary Execution
```spl
index=sysmon EventCode=1 
| where match(Image, "(?i)(msbuild|installutil|regsvcs|regasm|csc|vbc)\.exe$")
| stats count values(CommandLine) as commands by Image, ParentImage, User, ComputerName
```

#### Suspicious Parent-Child Relationships
```spl
index=sysmon EventCode=1
| eval suspicious=case(
    match(ParentImage, "(?i)msbuild\.exe$") AND match(Image, "(?i)(powershell|cmd|wscript|cscript)\.exe$"), "msbuild_shell",
    match(ParentImage, "(?i)wmiprvse\.exe$") AND NOT match(Image, "(?i)(wmiprvse|scrcons)\.exe$"), "wmi_child",
    match(ParentImage, "(?i)(winword|excel|powerpnt)\.exe$") AND match(Image, "(?i)(powershell|cmd|wscript)\.exe$"), "office_shell",
    match(ParentImage, "(?i)rundll32\.exe$") AND match(Image, "(?i)(powershell|cmd)\.exe$"), "rundll_shell",
    1=1, null
)
| where isnotnull(suspicious)
| table _time, ComputerName, User, ParentImage, Image, CommandLine, suspicious
```

### Lateral Movement Detection

#### ADMIN$ Share Access
```spl
index=wineventlog sourcetype="WinEventLog:Security" EventCode=5140 
ShareName IN ("\\\\*\\ADMIN$", "\\\\*\\C$", "\\\\*\\IPC$")
| stats count values(ShareName) as shares by IpAddress, SubjectUserName, SubjectDomainName
| where count > 1
| eval account=SubjectDomainName."\\".SubjectUserName
```

#### WMI Remote Process Creation
```spl
index=sysmon EventCode=1 ParentImage="*\\WmiPrvSE.exe"
| where NOT match(Image, "(?i)(wmiprvse|scrcons|mofcomp)\.exe$")
| table _time, ComputerName, ParentImage, Image, CommandLine, User
```

#### PsExec-Style Service Installation
```spl
index=wineventlog sourcetype="WinEventLog:System" EventCode=7045
| where match(ImagePath, "(?i)(cmd|powershell|\\\\)")
| table _time, ComputerName, ServiceName, ImagePath, ServiceType, StartType
```

### Persistence Detection

#### Scheduled Task Creation
```spl
index=wineventlog sourcetype="WinEventLog:Security" EventCode=4698
| spath input=TaskContent
| where match(TaskContent, "(?i)(powershell|cmd\.exe|wscript|cscript|mshta)")
| table _time, ComputerName, SubjectUserName, TaskName, TaskContent
```

#### Registry Run Key Modification
```spl
index=sysmon EventCode IN (12, 13, 14) 
TargetObject="*\\CurrentVersion\\Run*" OR TargetObject="*\\CurrentVersion\\RunOnce*"
| eval registry_action=case(EventCode=12, "CreateKey", EventCode=13, "SetValue", EventCode=14, "RenameKey")
| table _time, ComputerName, User, registry_action, TargetObject, Details
```

#### New Service Installation
```spl
index=wineventlog sourcetype="WinEventLog:System" EventCode=7045
| table _time, ComputerName, ServiceName, ImagePath, ServiceType, StartType, AccountName
| sort -_time
```

### Defense Evasion Detection

#### Process Injection (CreateRemoteThread)
```spl
index=sysmon EventCode=8
| where NOT match(SourceImage, "(?i)(csrss|services|svchost|lsass|System)\.exe$")
| eval injection_type="CreateRemoteThread"
| table _time, ComputerName, SourceImage, TargetImage, StartAddress, injection_type
```

#### Unsigned DLL Loading
```spl
index=sysmon EventCode=7 Signed="false"
| where NOT match(ImageLoaded, "(?i)\\\\Windows\\\\")
| stats count by Image, ImageLoaded, ComputerName
| sort -count
```

### C2 Detection

#### Beaconing Analysis
```spl
index=zeek sourcetype=zeek_conn id.resp_p IN (80, 443, 8080, 8443)
| bin _time span=1m
| stats count by _time, id.orig_h, id.resp_h, id.resp_p
| streamstats window=10 avg(count) as avg_count stdev(count) as stdev_count by id.orig_h, id.resp_h
| where stdev_count < 2 AND count > 0
| eval potential_beacon="true"
```

#### DNS Tunneling Detection
```spl
index=sysmon EventCode=22
| eval query_length=len(QueryName)
| eval subdomain_count=mvcount(split(QueryName, "."))
| where query_length > 50 OR subdomain_count > 5
| stats count avg(query_length) as avg_len by QueryName, Image
| sort -avg_len
```

#### Uncommon User-Agent Strings
```spl
index=zeek sourcetype=zeek_http
| stats count by user_agent
| where count < 10
| sort count
```

---

## Sigma Rules

### Discovery

#### Domain Group Enumeration
```yaml
title: Domain Group Enumeration via net.exe
id: d6d13c24-8f6b-4a3e-b8e5-7f2c1a9e0d3f
status: stable
description: Detects enumeration of domain groups using net.exe
references:
    - https://attack.mitre.org/techniques/T1069/002/
author: Purple Team Skill
logsource:
    category: process_creation
    product: windows
detection:
    selection:
        Image|endswith: '\net.exe'
        CommandLine|contains:
            - 'group'
            - 'localgroup'
    filter:
        CommandLine|contains: '/add'
    condition: selection and not filter
level: low
tags:
    - attack.discovery
    - attack.t1069.002
```

#### Multiple Reconnaissance Commands
```yaml
title: Burst Reconnaissance Activity
id: a8b9c1d2-3e4f-5a6b-7c8d-9e0f1a2b3c4d
status: experimental
description: Detects multiple reconnaissance commands in short timeframe
references:
    - https://attack.mitre.org/tactics/TA0007/
author: Purple Team Skill
logsource:
    category: process_creation
    product: windows
detection:
    selection:
        Image|endswith:
            - '\net.exe'
            - '\nltest.exe'
            - '\dsquery.exe'
            - '\whoami.exe'
            - '\systeminfo.exe'
            - '\ipconfig.exe'
    timeframe: 60s
    condition: selection | count() by ComputerName > 5
level: medium
tags:
    - attack.discovery
```

### Credential Access

#### LSASS Memory Access
```yaml
title: LSASS Memory Access for Credential Dumping
id: f5e6d7c8-b9a0-1234-5678-90abcdef1234
status: stable
description: Detects suspicious access to LSASS process memory
references:
    - https://attack.mitre.org/techniques/T1003/001/
author: Purple Team Skill
logsource:
    category: process_access
    product: windows
detection:
    selection:
        TargetImage|endswith: '\lsass.exe'
        GrantedAccess|contains:
            - '0x1fffff'
            - '0x1410'
            - '0x143a'
            - '0x1010'
    filter:
        SourceImage|endswith:
            - '\csrss.exe'
            - '\wininit.exe'
            - '\services.exe'
            - '\MsMpEng.exe'
            - '\svchost.exe'
    condition: selection and not filter
level: high
tags:
    - attack.credential_access
    - attack.t1003.001
```

### Execution

#### MSBuild Spawning Shell
```yaml
title: MSBuild Spawning Command Shell
id: c3d4e5f6-7890-abcd-ef12-34567890abcd
status: stable
description: Detects MSBuild.exe spawning command interpreters
references:
    - https://attack.mitre.org/techniques/T1127/001/
author: Purple Team Skill
logsource:
    category: process_creation
    product: windows
detection:
    selection:
        ParentImage|endswith: '\MSBuild.exe'
        Image|endswith:
            - '\cmd.exe'
            - '\powershell.exe'
            - '\pwsh.exe'
            - '\wscript.exe'
            - '\cscript.exe'
    condition: selection
level: high
tags:
    - attack.execution
    - attack.defense_evasion
    - attack.t1127.001
```

#### Encoded PowerShell Execution
```yaml
title: Encoded PowerShell Command
id: b2c3d4e5-f678-90ab-cdef-1234567890ab
status: stable
description: Detects execution of encoded PowerShell commands
references:
    - https://attack.mitre.org/techniques/T1059/001/
author: Purple Team Skill
logsource:
    category: process_creation
    product: windows
detection:
    selection:
        Image|endswith:
            - '\powershell.exe'
            - '\pwsh.exe'
        CommandLine|contains:
            - '-enc'
            - '-encodedcommand'
            - '-e '
            - '-ec '
    condition: selection
level: medium
tags:
    - attack.execution
    - attack.t1059.001
```

### Lateral Movement

#### Remote Service Installation
```yaml
title: Remote Service Installation via sc.exe
id: 9a8b7c6d-5e4f-3a2b-1c0d-ef9876543210
status: stable
description: Detects remote service installation using sc.exe
references:
    - https://attack.mitre.org/techniques/T1021/002/
author: Purple Team Skill
logsource:
    category: process_creation
    product: windows
detection:
    selection:
        Image|endswith: '\sc.exe'
        CommandLine|contains:
            - '\\\\' 
            - 'create'
    condition: selection
level: medium
tags:
    - attack.lateral_movement
    - attack.t1021.002
```

#### WMI Remote Process Creation
```yaml
title: WMI Spawning Unexpected Process
id: 1a2b3c4d-5e6f-7890-abcd-ef1234567890
status: stable
description: Detects WmiPrvSE spawning suspicious child processes
references:
    - https://attack.mitre.org/techniques/T1047/
author: Purple Team Skill
logsource:
    category: process_creation
    product: windows
detection:
    selection:
        ParentImage|endswith: '\WmiPrvSE.exe'
    filter:
        Image|endswith:
            - '\WmiPrvSE.exe'
            - '\scrcons.exe'
            - '\mofcomp.exe'
    condition: selection and not filter
level: high
tags:
    - attack.lateral_movement
    - attack.t1047
```

### Persistence

#### Scheduled Task with Suspicious Command
```yaml
title: Scheduled Task Executing Shell Commands
id: 4d5e6f70-8901-2345-6789-0abcdef12345
status: stable
description: Detects scheduled task creation with command interpreter execution
references:
    - https://attack.mitre.org/techniques/T1053/005/
author: Purple Team Skill
logsource:
    product: windows
    service: security
detection:
    selection:
        EventID: 4698
    keywords:
        TaskContent|contains:
            - 'powershell'
            - 'cmd.exe'
            - 'wscript'
            - 'cscript'
            - 'mshta'
    condition: selection and keywords
level: medium
tags:
    - attack.persistence
    - attack.t1053.005
```

#### Registry Run Key Persistence
```yaml
title: Registry Run Key Modification
id: 5e6f7081-9012-3456-7890-1bcdef234567
status: stable
description: Detects modification of Run keys in registry
references:
    - https://attack.mitre.org/techniques/T1547/001/
author: Purple Team Skill
logsource:
    category: registry_set
    product: windows
detection:
    selection:
        TargetObject|contains:
            - '\CurrentVersion\Run'
            - '\CurrentVersion\RunOnce'
    suspicious_values:
        Details|contains:
            - 'powershell'
            - 'cmd.exe'
            - 'wscript'
            - 'mshta'
            - '.vbs'
            - '.js'
    condition: selection and suspicious_values
level: medium
tags:
    - attack.persistence
    - attack.t1547.001
```

### Defense Evasion

#### Process Injection via CreateRemoteThread
```yaml
title: CreateRemoteThread Injection
id: 6f708192-0123-4567-8901-2cdef3456789
status: stable
description: Detects potential process injection via CreateRemoteThread
references:
    - https://attack.mitre.org/techniques/T1055/
author: Purple Team Skill
logsource:
    category: create_remote_thread
    product: windows
detection:
    selection:
        EventType: CreateRemoteThread
    filter:
        SourceImage|endswith:
            - '\csrss.exe'
            - '\services.exe'
            - '\svchost.exe'
            - '\lsass.exe'
    condition: selection and not filter
level: high
tags:
    - attack.defense_evasion
    - attack.t1055
```

---

## Query Conversion Reference

| Sigma Field | Splunk Equivalent | Example |
|-------------|-------------------|---------|
| `Image\|endswith` | `Image="*\\value"` | `Image="*\\net.exe"` |
| `CommandLine\|contains` | `CommandLine="*value*"` | `CommandLine="*group*"` |
| `\|count() by field > N` | `\| stats count by field \| where count > N` | - |
| `ParentImage` | `ParentImage` | Same |
| `EventID` | `EventCode` | `EventCode=4688` |

### Sigma to Splunk Conversion

```bash
# Using sigmac
sigmac -t splunk -c sysmon rule.yaml

# Using sigma-cli (newer)
sigma convert -t splunk -p sysmon rule.yaml
```
