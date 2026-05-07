---
name: macos-preference-injection-hunting
description: |
  Systematic methodology for finding NSUserDefaults preference injection
  vulnerabilities in macOS daemons. Use when: (1) auditing macOS daemon
  security, (2) hunting for debug/test preferences in production binaries,
  (3) assessing preference-based attack surface on macOS. Covers discovery
  via string scanning, validation via defaults write, and impact assessment.
  Found 7+ vulnerable daemons including sharingd (AirDrop), callservicesd
  (FaceTime), rapportd (Continuity), studentd (Classroom).
author: David Maynor / Claude Code
version: 1.1.0
date: 2026-03-29
---

# macOS Preference Injection Hunting

## Problem

macOS daemons frequently use NSUserDefaults (`defaults read/write`) for
configuration, including debug and test settings. These preferences are
stored in user-domain plist files (`~/Library/Preferences/`) writable by
any process running as the same UID. When daemons consume these preferences
for security-critical decisions without validation, any unprivileged process
can inject values that disable encryption, bypass authentication, suppress
quarantine, or enable forced screen observation.

## Context / Trigger Conditions

Use this methodology when:
- Auditing macOS daemon security posture
- Hunting for debug/test code shipped in production
- Assessing local privilege escalation paths
- Looking for confused deputy vulnerabilities
- Analyzing preference-based attack surface after finding one instance

## Solution: Step-by-Step Hunting Methodology

### Step 1: Identify Targets — Running Daemons

```bash
# List all running user-agent daemons
ps aux | grep -E "/usr/libexec/|/System/Library/" | awk '{print $NF}' | sort -u
```

### Step 2: Scan for Debug/Test Preference Keys

```bash
# For each daemon binary, extract injectable-looking string constants
for bin in /usr/libexec/*; do
    if [ -f "$bin" ] && [ -x "$bin" ]; then
        hits=$(strings "$bin" 2>/dev/null | grep -cE \
          "^(AlwaysAuto|DisableQuarantine|DisableTLS|DisableEncrypt|EnableDebug|EnableTest|EnableDemo|ForceAllow|BypassAuth|SkipValidat|OverrideSecur|DisableSandbox|ForceTrust|AllowUnsigned|TestMode|DebugMode|DemoMode|MockMode)")
        if [ "$hits" -gt 0 ]; then
            name=$(basename "$bin")
            keys=$(strings "$bin" 2>/dev/null | grep -E \
              "^(AlwaysAuto|Disable|Enable|Force|Bypass|Skip|Override|Mock|Fake|Test|Debug|Demo|Allow|pretend)" \
              | sort -u | tr '\n' ', ')
            echo "$name ($hits): $keys"
        fi
    fi
done
```

### Step 3: Identify Preference Domains

```bash
# Find what pref domain a daemon reads
strings /path/to/daemon 2>/dev/null | grep "^com\.apple\." | sort -u

# Or check if the daemon has a readable domain already
defaults read com.apple.DAEMONNAME 2>/dev/null
```

### Step 4: Verify Writability

```bash
# Test if we can write to the preference domain
defaults write com.apple.DOMAIN testkey testval
echo "Write: $?"
defaults delete com.apple.DOMAIN testkey
```

### Step 5: Test Specific Dangerous Keys

```bash
# Write a dangerous key and verify it takes
defaults write com.apple.sharing DisableQuarantine -bool true
defaults read com.apple.sharing DisableQuarantine
# Clean up immediately
defaults delete com.apple.sharing DisableQuarantine
```

### Step 6: Assess Impact

For each injectable key, determine:
1. **What does the key control?** (encryption, authentication, file handling)
2. **What entitlements does the daemon hold?** (`codesign -d --entitlements -`)
3. **Is the daemon network-facing?** (`lsof -i -P -n | grep daemonname`)
4. **Is the daemon's XPC reachable?** (bootstrap_look_up test)
5. **What other daemons trust this one?** (sandbox profile mach-lookup rules)

### Step 7: Document the Chain

Map the full attack:
- Stage 1: Local pref write (what key, what domain)
- Stage 2: Daemon behavior change (what security control is weakened)
- Stage 3: Exploitation (how an attacker leverages the weakened control)

## Key Patterns to Search For

| Pattern | What It Usually Controls |
|---------|------------------------|
| `Disable*` | Security feature toggle (TLS, encryption, quarantine, sandbox) |
| `Enable*Mode` | Debug/test/demo mode activation |
| `Force*` | Override security decisions |
| `Bypass*` | Skip authentication or validation |
| `Allow*` | Permit normally-blocked operations |
| `pretend*` | Fake security state (bypass time/state checks) |
| `Mock*` | Inject simulated data |
| `Skip*` | Skip security checks |
| `Override*` | Override security policies |
| `*TestMode*` | Activate test infrastructure |
| `*Password` | Plaintext credential storage in prefs |

## Verified Vulnerable Daemons (macOS 26 Tahoe)

| Daemon | Domain | Critical Keys | Impact |
|--------|--------|--------------|--------|
| sharingd | com.apple.sharing | AlwaysAutoAccept, DisableQuarantine, DisableContinuityTLS | Silent AirDrop RCE chain |
| callservicesd | com.apple.TelephonyUtilities | disableFaceTimeKeyExchange, DisableBlastdoorValidationPrompt | FaceTime E2E disable |
| studentd | com.apple.classroom | forceUnpromptedRemoteScreenObservation, allowClassroom* | Forced screen observation |
| rapportd | com.apple.rapport | allowUnauthenticated, ForceL2CAP | Accept unauthenticated connections |
| securityuploadd | com.apple.securityuploadd | allowInsecureSplunkCert, disableUploads | Disable security telemetry |
| gamed | com.apple.gamed | BypassAuthentication | GameCenter auth bypass |
| intelligenceflowd | com.apple.intelligenceflow | agenticPlannerZincUrl, disableToolBoxAllowList | Redirect AI inference |

## Verification

After finding an injectable preference:
1. Write the preference
2. Observe daemon behavior change (logs, network, file system)
3. Remove the preference
4. Verify normal behavior resumes
5. Document with timestamps

Use `airdrop-observatory --security --headless` to monitor preference changes in real-time.

## Notes

- Preferences persist across daemon restarts (stored in plist files)
- Some daemons read prefs at startup only; others read per-operation
- `com.apple.classroom` keys have per-device suffixes (use `defaults read domain` and grep)
- The root cause is NSUserDefaults consumed without validation — same class as Apple Intelligence V-006
- iOS has app sandbox limiting which domains apps can write to, but jailbroken devices are vulnerable
- For shared-cache binaries, use `dyld_info -section __TEXT __cstring` instead of `strings`

## References

- Apple Security Bounty: https://security.apple.com/bounty/categories/
- macOS Gatekeeper Bypass category: $100,000
- NSUserDefaults documentation: developer.apple.com/documentation/foundation/nsuserdefaults
