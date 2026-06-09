---
name: apple-vuln-research-kernelcache-kext-binary-diff
description: |
  Reliably diff a single macOS kext between two macOS versions (e.g. 26.4.1
  vs 26.5) when both ship inside the kernelcache. Use when: (1) confirming
  whether a kext actually changed across a point release (kext CFBundleVersion
  is unreliable in macOS 26+ — bumps with no code change, and code changes
  with no bump, both happen); (2) two extracted .macho files differ in raw
  hash entirely due to linker relocation churn; (3) ruling out a silent CVE
  patch in a security-sensitive kext (AppleJPEGDriver, IOAESAccelerator,
  AppleUSBAudio, MT7932 DEXT); (4) a 100-version kext bump that may be just an
  SDK marker; (5) the same kext at different load VAs shows ~16% raw byte
  difference. Covers kernelcache extraction (pyimg4 + ipsw), kext extraction
  (kmutil splitkc), PC-relative-immediate and load/store-offset masking,
  opcode-class change counting, LC_UUID comparison, kalloc_type_view tag
  stability, per-function masked diff. Applies to all kexts shipped in the
  kernelcache on Apple Silicon (all since macOS 11).
author: Claude Code
version: 1.1.0
date: 2026-05-31
---

# Kernelcache kext binary diff (opcode-mask methodology)

## Problem

You need to know whether a specific kext actually changed between two
macOS releases. Naïve approaches all fail in modern macOS:

- **kext `CFBundleVersion`** is unreliable in both directions on macOS
  26+. Examples observed on the same OS upgrade (26.4.1 → 26.5):
  - `AppleH16CameraInterface` bumped 5.405 → 5.502 (~100 versions) →
    no actual code change. Pure SDK/build-marker bump.
  - `AppleUSBAudio` bumped 841.2 → 850.5 → no actual code change.
  - MediaTek `AppleSunriseBluetooth` DEXT `CFBundleVersion=1` stable
    across versions → binary actually doubled in size (557 KB →
    1.16 MB).
- **Raw kext file SHA-256** is useless because the kernelcache linker
  relocates instructions and patches load/store offsets when it places
  the kext at a different load VA. Two functionally-identical kexts can
  show ~16% raw byte difference purely from relocation churn.
- **`nm -gU` symbol diff** misses inline changes and code-only changes
  inside existing functions.

This skill is the methodology that actually answers the question
"did this kext change semantically?" — verified on multiple kexts in
the VS67 work loop for the macOS 26.5 enumeration.

## Trigger conditions

Use this skill when ANY of:

- You need to confirm whether a security-sensitive kext was patched
  in a point release before retriggering a known bug.
- You see a kext CFBundleVersion bump and want to know if it's real.
- Two kernelcache-extracted kexts hash differently but you suspect
  it's only relocation noise.
- You're auditing what silent fixes Apple shipped in a release.
- You're confirming a watchpoint kext is still vulnerable after an
  OS update.

Don't use this skill for:

- Standalone DEXTs in /System/Library/DriverExtensions — those are
  Mach-O files on disk, diff them directly with hash + `nm` + opcode
  mask, no extraction needed.
- Kernelcache-level structural diffs (use `joker` or `ipsw kernel`
  diff for the cache, not for a single kext).

## Solution — step-by-step

### Step 1: extract kernelcache from both versions

Kernelcaches on Apple Silicon are IM4P-wrapped LZFSE-compressed
Mach-O. Use `pyimg4` (Python tool) or `ipsw` (Blacktop) — both work.

```sh
# Locate the kernelcache for your SoC. On macOS 26 the path looks like:
ls /System/Volumes/Preboot/*/restore/kernelcache.release.mac17g
# mac17g = MacBook Mac17,5 (Neo, t8140 / A18 Pro)
# mac16g = MacBook Air M3
# mac15g = older
# See apple-vuln-research-apple-silicon-kernel-layout skill for the full map.

# Extract:
pyimg4 im4p extract -i kernelcache.release.mac17g -o kc-mac17g.macho
# Verify:
file kc-mac17g.macho   # -> "Mach-O 64-bit kernelcache arm64e"
```

If `pyimg4` not installed: `pip install pyimg4`. Alternative:
`ipsw kernel extract <kernelcache>`.

For 26.4.1 baseline, the repo typically already has
`artifacts/kernelcache-25E253-arm64e.macho`. Verify with `file`.

### Step 2: split out the specific kext

```sh
# Modern (Apple Silicon) kernelcaches are prelinked. Use kmutil:
kmutil splitkc -k kc-mac17g.macho -o split-mac17g/
ls split-mac17g/   # includes com.apple.driver.AppleJPEGDriver.kext/

# Alternative: ipsw kernel kexts <kc> --extract com.apple.driver.AppleJPEGDriver
# Or fall back to symbol-grep extraction if both fail.
```

You now have two Mach-O kext binaries (one per version).

### Step 3: first-pass cheap checks (often decisive)

```sh
# LC_UUID equality is the strongest signal: identical UUID means Apple
# did not even rebuild the kext. Found this on AppleJPEGDriver across
# 26.4.1 -> 26.5: same LC_UUID 44530213-6160-3DB4-9987-BC76BCBE423D.
otool -l v1.kext | awk '/LC_UUID/{print NR; getline; print}' 
otool -l v2.kext | awk '/LC_UUID/{print NR; getline; print}'

# File size + __text section size — both invariant under linker relocation
# unless code actually changed
size v1.kext v2.kext
otool -l v1.kext | grep -A2 __text
otool -l v2.kext | grep -A2 __text

# Symbol count + names — all relocation-invariant
nm -gU v1.kext | wc -l
nm -gU v2.kext | wc -l
diff <(nm -gU v1.kext | awk '{print $3}' | sort) \
     <(nm -gU v2.kext | awk '{print $3}' | sort)

# __cstring / __const sections — pure data, relocation-invariant
# (read-only data; if changed, code likely changed)
otool -s __TEXT __cstring v1.kext | shasum -a 256
otool -s __TEXT __cstring v2.kext | shasum -a 256
```

**If LC_UUID is identical → done. Kext is bit-identical. No further
work needed.** (Observed on AppleJPEGDriver 26.4.1 → 26.5.)

**If symbol names diverge or __cstring hashes differ → real change.**
Skip to step 5 (per-function diff).

**If everything matches except the raw hash → continue to step 4.**

### Step 4: opcode-mask diff (the key technique)

This is the technique that handles the relocation-noise problem. After
the kernelcache linker patches a kext at a different load VA, every
PC-relative branch immediate and many load/store offsets will change
even though the underlying code is identical.

Mask those two classes of bytes before comparing.

```sh
# Python pseudocode for the mask. The exact instructions to mask on arm64:
#   B   imm26      (0x14000000 / 0xfc000000)  - mask low 26 bits
#   BL  imm26      (0x94000000 / 0xfc000000)  - mask low 26 bits
#   B.cond imm19   (0x54000000 / 0xff000010)  - mask bits 5..23
#   CBZ/CBNZ imm19 (0x34000000 / 0x7e000000)  - mask bits 5..23
#   TBZ/TBNZ imm14 (0x36000000 / 0x7e000000)  - mask bits 5..18
#   ADR/ADRP imm21 (0x10000000 / 0x9f000000)  - mask imm21 (split across instruction)
#   LDR/STR imm12  (PC-relative literal / page-relative) - mask offset bits 10..21
#
# Then compare instruction-by-instruction. Count instructions where the
# OPCODE CLASS changes (i.e., post-mask bits differ).

# A working implementation lives at:
#   tools/custom/kext-binary-diff/  (created as part of this skill)
# or use Capstone-Python:
#   pip install capstone
```

Reference implementation skeleton (Python + capstone):

```python
import capstone
import struct

def mask_arm64_instr(insn_bytes):
    """Mask PC-relative immediates so two relocated copies compare equal."""
    word = struct.unpack('<I', insn_bytes)[0]
    op = word
    # B / BL: clear imm26
    if (word & 0x7c000000) == 0x14000000:
        op = word & 0xfc000000
    # B.cond / CBZ / CBNZ: clear imm19 (bits 5..23)
    elif (word & 0xfe000000) == 0x54000000 or \
         (word & 0x7e000000) == 0x34000000:
        op = word & 0xff00001f
    # TBZ / TBNZ: clear imm14 (bits 5..18)
    elif (word & 0x7e000000) == 0x36000000:
        op = word & 0xfff8001f
    # ADR / ADRP: clear immlo:immhi
    elif (word & 0x1f000000) == 0x10000000:
        op = word & 0x9f00001f
    # LDR (literal) — PC-relative imm19
    elif (word & 0xbf000000) == 0x18000000 or \
         (word & 0xbf000000) == 0x58000000:
        op = word & 0xff00001f
    return struct.pack('<I', op)

def diff_text(text1, text2):
    """Return count of opcode-class changes between two equal-length __text sections."""
    assert len(text1) == len(text2), "different __text sizes -> real change, no need to mask"
    changes = 0
    for i in range(0, len(text1), 4):
        if mask_arm64_instr(text1[i:i+4]) != mask_arm64_instr(text2[i:i+4]):
            changes += 1
    return changes
```

Run it on the two `__text` sections. If the count of opcode-class
changes is **0**, the kext is functionally identical and the byte
diff is 100% relocation noise. (Observed across 26.4.1 → 26.5 for
AppleH16CameraInterface — 0 of 129,778 instruction words changed
despite ~16% raw diff.)

### Step 5: per-function masked diff (only if step 4 found changes)

If opcode-class changes are non-zero, narrow down to which functions
changed. Use `nm` + addresses + section data:

```sh
# Get function boundaries
nm -n v1.kext | awk '/T/ {print $1, $3}' > v1_funcs.txt
nm -n v2.kext | awk '/T/ {print $1, $3}' > v2_funcs.txt

# For each function present in both, apply the opcode-mask diff to
# just that function's byte range. Report functions with non-zero
# change count.
```

Pay special attention to:

- `externalMethod` and any function ending in `UserClient::*` (IOKit
  external dispatch surface)
- Functions whose names match the bug-triggering API (e.g.
  `startDecoderExt` for AppleJPEGDriver — V-047)
- Functions ending in `Gated` (IOCommandGate-protected critical
  sections)
- `kalloc_type_view` tag numbers — if any allocation site changed,
  the tag numbers will shift even if the call is identical. Stable
  tags = stable allocation sites.

### Step 6: verify entitlement / sandbox surface

Even if the kext binary is bit-identical, the reachability may have
changed via:

- Sandbox profile changes (`/System/Library/Sandbox/Profiles/*.sb`)
- New entitled callers (run an entitlement diff on `/usr/libexec`,
  `/usr/sbin`, `/usr/bin`)
- New `iokit-user-client-class` exceptions in any daemon's profile

This is what flipped V-047 from "unprivileged DoS" to "pre-FileVault
RCE candidate" in macOS 26.5 — the kext was bit-identical, but
`com.apple.AppSSODaemon.preboot.sb` newly allowed
`AppleJPEGDriverUserClient` open from the FVUnlock baseSystem.

## Verification

You know you got it right when:

- LC_UUID equality leads to "0 opcode changes" (sanity check on your
  mask implementation)
- The same masked diff on two known-identical kernelcaches (e.g. two
  fresh extracts of the same kernelcache file with different VAs from
  the same OS) reports 0 changes
- For a known-changed kext (e.g. compare 26.3.x vs 26.5 for any kext
  that had a real fix), the diff reports a non-zero but small change
  count concentrated in 1–3 functions

## Example: the VS67 result table

From the macOS 26.4.1 → 26.5 work loop, this methodology produced:

| Kext | CFBundleVersion change | Opcode-class changes | Verdict |
|---|---|---|---|
| AppleJPEGDriver | none | 0 | bit-identical (same LC_UUID) |
| AppleH16CameraInterface | 5.405 → 5.502 | 0 / 129,778 | no-op bump |
| AppleUSBAudio | 841.2 → 850.5 | 0 | no-op bump |
| IOUSBHostFamily::createPipe | n/a | +148 instructions | real hardening (silent CVE) |
| AppleSunriseBluetooth DEXT | none (still v1) | DEXT binary doubled (557 KB → 1.16 MB) | major code change |

Note the asymmetry: large CFBundleVersion bumps can be no-ops, and
stable CFBundleVersion can hide doubled-size binaries. **Never trust
the version number.**

## Notes

- The mask in step 4 covers arm64 only. For x86_64 kernelcaches (Intel
  Macs, or the x86_64 stub at `/System/Library/Kernels/kernel` on
  Apple Silicon), mask different instruction classes (E8/E9 call/jmp
  relative, RIP-relative MOV/LEA).
- If `pyimg4` and `ipsw` both fail to extract the kernelcache (rare:
  Apple sometimes changes the IM4P wrapper), fall back to a
  string-level diff via `strings -a -n 8 | sort -u | diff` over the
  raw kernelcaches. It still surfaces added/removed log messages and
  hints at behavior changes.
- For Apple Silicon kernel layout (where to find the right
  kernelcache for your SoC), see the
  `apple-vuln-research-apple-silicon-kernel-layout` skill.
- For interpreting IOKit selector tables and external method
  dispatch arrays you'll find in step 5, see the
  `apple-vuln-research-iokit-struct-re-via-objc-encoding` skill.

## References

- The pyimg4 IM4P extractor: https://github.com/m1stadev/PyIMG4
- Blacktop ipsw tool: https://github.com/blacktop/ipsw
- ARM Architecture Reference Manual (instruction encodings):
  https://developer.arm.com/documentation/ddi0487/latest
- VS67 enumeration commits where this technique was developed:
  `findings/os/h16camerainterface-26.5-diff.md`,
  `findings/os/applejpegdriver-26.5-diff.md`,
  `findings/os/appleusbaudio-26.5-diff.md` in the apple-vuln-research
  repo.
