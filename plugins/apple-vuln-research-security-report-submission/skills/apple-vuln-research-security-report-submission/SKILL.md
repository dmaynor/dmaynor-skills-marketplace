---
name: apple-vuln-research-security-report-submission
description: |
  Submit vulnerability reports to Apple Security Research (security.apple.com).
  Use when: (1) preparing a macOS/iOS vulnerability report for Apple's bounty program,
  (2) need to know which affected area dropdown to select, (3) structuring PoC code
  and panic logs for Apple's submission form, (4) estimating bounty category and payout,
  (5) understanding Target Flags for maximum rewards.
  Covers: submission process, form fields, affected area mapping, bounty categories,
  report structure, attachment packaging, and Target Flag eligibility.
author: Claude Code
version: 1.1.0
date: 2026-03-14
---

# Apple Security Report Submission

## Problem
Apple's security vulnerability reporting process has specific requirements for form fields,
affected area categories, and attachment formats that aren't well-documented publicly.

## Context / Trigger Conditions
- You have a verified vulnerability in an Apple product
- You need to submit to security.apple.com
- You need to choose the right affected area category
- You want to maximize bounty eligibility

## Solution

### Submission URL
**https://security.apple.com/submit** (requires Apple ID login)

Alternative: email product-security@apple.com (no tracking)

### Form Fields

| Field | What to put |
|-------|-------------|
| **Title** | Short, specific: "Unprivileged kernel panic via [component] [mechanism]" |
| **Affected Area** | See dropdown mapping below |
| **Description** | Full report: summary, affected versions, reproduction steps, PoC inline, root cause, impact, CVSS, remediation |
| **Attachments** | Zip with: report.md, PoC source, panic logs, crash reports. Max 500MB. |
| **Credit** | Your name (or click "anonymous researcher" link to hide identity) |

### Affected Area Dropdown Mapping

| Bug Type | Select |
|----------|--------|
| Kernel panic from IOKit UserClient | **Daemons and Frameworks** |
| Bluetooth driver crash | **Bluetooth** |
| WiFi driver issue | **WiFi** (scroll down past Bluetooth) |
| Siri/Apple Intelligence | **Siri** |
| Sandbox escape | **Sandbox** |
| TCC bypass | **TCC** |
| Gatekeeper bypass | **Gatekeeper** |
| Safari/WebKit | **Safari** or **WebKit** |
| iCloud | **iCloud** |
| Code signing (AMFI/TXM) | **Daemons and Frameworks** (no dedicated category) |
| Kernel memory corruption | **Daemons and Frameworks** (no Kernel category in dropdown) |

### Report Structure Template

```
[Title]

SUMMARY: [1-2 sentences]

AFFECTED: [product] [version] ([build]). [scope statement]

REPRODUCTION:
Save as [filename]:
[inline PoC code]
Compile: [command]
Run: [command]
[Expected result]

ROOT CAUSE: [technical explanation]

IMPACT: [what an attacker can do]

See attached zip for full report, panic logs, and PoC.
```

### Bounty Categories and Estimates

| Category | Payout |
|----------|--------|
| Network → Kernel (no interaction) | $2,000,000 |
| Network → Kernel (with interaction) | $1,000,000 |
| Wireless proximity → App processor | $1,000,000 |
| App → Kernel (sandbox escape) | $500,000 |
| Physical → Sensitive data | $500,000 |
| Browser → Kernel | $1,000,000 |
| iCloud unauthorized access | $1,000,000 |
| macOS Gatekeeper bypass | $100,000 |
| Logic flaw / privilege escalation | $50,000 |
| Local unprivileged DoS (kernel panic) | $50,000-$100,000 (estimate) |
| TCC bypass | $5,000-$10,000 |

**Bonuses:** +50% beta, +100% Lockdown Mode bypass, +150% both

### Target Flags (Maximum Rewards)

Target Flags are built-in CTF markers in Apple OS. Required for maximum bounty in applicable categories (marked with ⚑).

- **Commpage Target Flag:** Demonstrate register control, arbitrary R/W, or code execution at predefined addresses
- **TCC Target Flag:** Demonstrate write access to TCC database via `tccutil flag check`
- **DoS bugs don't qualify** for Target Flags — they use the "detailed exploitability analysis" path

### Attachment Packaging

```bash
mkdir -p /tmp/report-name
cp report.md /tmp/report-name/
cp poc.c /tmp/report-name/
cp *.panic /tmp/report-name/       # kernel panic logs
cp *.ips /tmp/report-name/         # crash reports
cd /tmp && zip -r ~/Desktop/report-name.zip report-name/
```

## Verification
- Reports appear under "Open" tab at security.apple.com after submission
- Apple typically acknowledges within days, resolves within 90 days
- Track status online (email submissions can't be tracked)

## Notes
- Submit each vulnerability as a separate report (Apple tracks/pays per-issue)
- Submit highest-severity first
- Include inline PoC in description AND as attachment (redundancy)
- Always include build number (e.g., 25D2140) not just version
- Be honest about what you tested and what you didn't
- If prompt injection didn't work, say so — credibility matters
- Don't publicly disclose until Apple patches or 90 days elapse
