---
name: apple-silicon-attack-surface-enumeration
description: |
  Systematic attack surface enumeration for Apple Silicon devices (A-series, M-series).
  Use when: (1) starting security research on a new Apple chip/device, (2) need to map
  IOKit UserClients, Mach services, kexts, DART units, and coprocessor boundaries,
  (3) want to identify cross-platform (Mac↔iPhone/iPad) vulnerability applicability,
  (4) assessing which attack surfaces are unprivileged vs entitlement-gated.
  Covers: chip identification, device tree analysis, firmware inventory, boot chain,
  kext inventory, IOKit driver enumeration, system service mapping, and cross-platform
  diff methodology.
author: Claude Code
version: 1.1.0
date: 2026-03-12
---

# Apple Silicon Attack Surface Enumeration

## Problem
When starting security research on a new Apple Silicon device, you need a systematic
approach to enumerate all attack surfaces before diving deep. Without methodology,
researchers waste time on well-hardened surfaces while missing exposed ones.

## Context / Trigger Conditions
- New Apple Silicon device acquired for security research
- Need to understand what's unique about this chip vs others (A-series vs M-series)
- Want to identify unprivileged attack surfaces before entitlement-gated ones
- Planning cross-platform vulnerability research (Mac as iPhone proxy)
- Starting a new phase of Apple hardware/OS security assessment

## Solution

### Phase 1: Hardware Fingerprinting

**1.1 Chip Identification**
```bash
# SoC identity
sysctl -a | grep -E 'hw\.(chip|product|target|model|cpufamily|cputype)'
# Core topology and frequencies
sysctl -a | grep -E 'hw\.(perflevel|ncpu|physicalcpu)'
# ARM feature registers (PAC, MTE, BTI, SME, SSBS, SPECRES)
sysctl -a | grep hw.optional
# IOPlatformExpertDevice for board-id, chip-id, silicon revision
ioreg -d2 -c IOPlatformExpertDevice -r
```

**Key things to check:**
- FPAC (faults on bad PAC) vs plain PAC — determines exploitation difficulty
- MTE presence — if absent, UAF/heap corruption remain viable
- SME/SME2 — new matrix extension = new context leakage surface
- SSBS/SPECRES — speculation mitigation presence

**1.2 Device Tree Analysis**
```bash
# Full IODeviceTree dump
ioreg -p IODeviceTree -l > device-tree-full.txt
# arm-io children (coprocessors, DARTs, MMIO)
ioreg -p IODeviceTree -n arm-io -r | grep -E '"name"|"compatible"|"AAPL,phandle"'
# DART (IOMMU) inventory
ioreg -p IODeviceTree -l | grep -B2 -A5 'dart'
# Chosen node (security flags, boot args)
ioreg -p IODeviceTree -n chosen -r
```

**Key things to check:**
- `security-downgradable` flag (1 = macOS allows SIP disable; 0 = locked like iPhone)
- DART count and compatible strings (shared IP = shared bugs)
- Exclave nodes (new isolation model for ANE, ISP)
- MMIO region sizes (larger = more attack surface)
- `exclaves-test` presence (active development = less mature)

**1.3 Firmware Inventory**
```bash
# Boot firmware
system_profiler SPiBridgeDataType SPHardwareDataType
nvram -p | grep -i boot  # boot breadcrumbs
# WiFi/BT (may differ from device tree compatible string!)
system_profiler SPBluetoothDataType SPAirPortDataType
ioreg -l -n wlan | head -50
# NVMe
system_profiler SPNVMeDataType
# All firmware versions accessible from userspace
ioreg -l | grep -i 'firmware\|fw-version\|rom-version'
```

**Critical gotcha:** Device tree `compatible` strings may not match actual hardware.
Example: MacBook Neo reports `wlan-pcie,bcm4387` but ships MediaTek MT7932.
Always cross-check with system_profiler and driver IORegistry entries.

**1.4 Boot Chain**
```bash
# Security policy
csrutil status
# Signed System Volume
diskutil apfs listSnapshots /
# Boot mode
nvram -p | grep boot-mode
# Secure Element (if present)
system_profiler SPSecureElementDataType
```

### Phase 2: OS Enumeration

**2.1 Kernel Extensions**
```bash
# Loaded kexts with addresses
kextstat
# All kexts on disk
find /System/Library/Extensions /Library/Extensions -name '*.kext' -maxdepth 2 2>/dev/null | wc -l
# Chip-specific kexts (replace t8140 with your chip ID)
kextstat | grep -i 't8140\|H16\|Everest\|Sunrise'
# DriverKit extensions
systemextensionsctl list
```

**Identify:**
- Chip-unique kexts (platform-specific drivers)
- iOS-shared kexts (cross-platform vulnerability surface)
- DriverKit vs kernel kexts (userspace = debuggable)
- Largest kexts by size (more code = more bugs)
- Sandbox profiles for camera/ANE/GPU daemons

**2.2 IOKit Drivers**
```bash
# Full IOService plane
ioreg -p IOService -l > ioservice-full.txt
# All registry planes
ioreg -l | grep -E '^\+-o .* <class' | head -20
# UserClient classes
ioreg -p IOService -l | grep -c 'UserClient'
# UserClient entitlement requirements
ioreg -p IOService -l | grep -A20 'UserClient' | grep -i 'entitlement\|require'
```

**Priority finding: unprotected UserClients.** Count how many have NO entitlement gating.
On A18 Pro: 240/248 UserClient instances had zero IOKit-level entitlement checks.

**2.3 System Services**
```bash
# System domain Mach services
launchctl print system/ | grep -E '^\s+(A|D)\s' | wc -l
# User domain
launchctl print gui/$(id -u)/ | grep -E '^\s+(A|D)\s' | wc -l
# LaunchDaemon/Agent counts
ls /System/Library/LaunchDaemons/ | wc -l
ls /System/Library/LaunchAgents/ | wc -l
# XPC services in frameworks
find /System/Library/Frameworks /System/Library/PrivateFrameworks -name '*.xpc' -maxdepth 3 2>/dev/null | wc -l
```

**Look for:**
- New service namespaces (e.g., Apple Intelligence = `intelligenceplatform`)
- Always-on daemons (KeepAlive = larger window of exposure)
- Debug flags in production security daemons (DEBUGSCOPE, etc.)
- Services with tool-calling or credential storage (confused deputy risk)

### Phase 3: Cross-Platform Assessment

**Key question: Which findings apply to iPhone?**

| Surface | Mac | iPhone | Cross-applicable? |
|---------|-----|--------|-------------------|
| Kernel/IOKit bugs | Full access | Same code, sandboxed | YES — same drivers |
| DART/IOMMU | Same silicon | Same silicon | YES — same IP |
| SEP/ANE/ISP | Same coprocessors | Same coprocessors | YES |
| WiFi/BT | May differ (MTK vs BCM) | Check model | DEPENDS on chipset |
| UserClients | No sandbox | App sandbox limits reach | PARTIALLY — need reachability |
| Mach services | No sandbox | App sandbox limits reach | PARTIALLY |
| Entitlements | Fewer required | More required | BUGS yes, REACH maybe not |

**Mac advantages for research:**
- No app sandbox by default
- Developer tools: dtrace, lldb, instruments, kperf
- SIP disableable (`security-downgradable = 1`)
- DriverKit drivers debuggable in userspace
- No code signing enforcement for research tools

**Porting barriers to iPhone:**
- Stricter entitlement checks on many paths
- App sandbox limits which services/UserClients are reachable
- No permissive boot mode
- Some kexts are Mac-only or iPhone-only

## Verification
- Chip identification: cross-reference sysctl output with ioreg IOPlatformExpertDevice
- Firmware: verify system_profiler matches ioreg driver entries (watch for compat string mismatches)
- Kext count: loaded (kextstat) + on-disk (find) should be consistent
- UserClient count: manual spot-check entitlement gating on 5-10 UserClients
- Cross-platform: compare chip-id between devices to confirm shared silicon

## Example

**Scenario:** New MacBook Neo (A18 Pro) acquired for research.

1. Chip ID → t8140, same as iPhone 16 Pro. FPAC enabled, no MTE, SME/SME2 present.
2. Device tree → 21 DARTs (all `dart,t8110`), 16 Exclave services, ISP has 67MB MMIO.
3. Firmware → MediaTek MT7932 WiFi despite BCM4387 compat string. First MTK in Mac.
4. Boot chain → Full Security, `security-downgradable = 1`.
5. Kexts → 249 loaded, 14 A18-unique, 42 iOS-shared (17%). Sunrise BT has test-driver entitlement.
6. IOKit → 240 unprotected UserClients out of 248.
7. Services → 2,007 Mach services. Apple Intelligence is 29+ services (largest new surface).
8. Assessment: develop kernel/IOKit exploits here, port to iPhone 16 Pro.

## Notes
- Run this enumeration on each new device/chip. Results differ significantly across A-series vs M-series.
- The "compatible" string in device tree is NOT authoritative for actual hardware — always verify.
- Save all raw dumps as artifacts (JSON + text) for cross-device diffing later.
- Prioritize unprivileged surfaces first: unprotected UserClients > entitlement-gated > kernel-only.
- Apple Intelligence services are brand new in macOS Tahoe — less battle-tested code.
- Exclave framework (`exclaves-test` node) suggests active development — likely immature.

## See Also
- `autonomous-research-loop` — for running this enumeration autonomously across many tasks

## References
- Developed during MacBook Neo (A18 Pro / t8140) security research, 2026-03-12
- Cross-referenced with iPhone 16 Pro (t8140 / D94AP) known configurations
