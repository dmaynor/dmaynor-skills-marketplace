---
name: apple-vuln-research-txm-sptm-firmware-extraction
description: |
  Extract and analyze Apple Silicon TXM (Trusted Execution Monitor) and SPTM
  (Secure Page Table Monitor) firmware binaries from IM4P containers on macOS.
  Use when: (1) need to reverse-engineer TXM panic codes, (2) analyzing
  SPTM/TXM trust boundary behavior, (3) extracting firmware from
  /System/Volumes/Preboot for static analysis, (4) mapping panic strings
  to error codes in Apple's secure monitor. Covers: IM4P container format,
  pyimg4 extraction, LZFSE decompression, Mach-O arm64e analysis.
author: Claude Code
version: 1.1.0
date: 2026-03-14
---

# TXM/SPTM Firmware Extraction and Analysis

## Problem
Apple's TXM (Trusted Execution Monitor) and SPTM (Secure Page Table Monitor) run at
higher privilege than the kernel (GL0 and GL2 respectively). When they panic, the error
codes are opaque (e.g., "TXM [Panic]: [code: 0x0000001A | 1]"). Understanding what
triggered the panic requires extracting and reversing the firmware binary.

## Context / Trigger Conditions
- A kernel panic log shows "TXM [Panic]" or "SPTM [Panic]" with a code
- You need to map the panic code to a specific assertion/check
- You want to understand TXM's boot state machine or code signing logic
- Static analysis of the secure monitor is needed (no runtime debugging possible)

## Solution

### Step 1: Locate the Firmware

```bash
# TXM firmware (universal, same on all Apple Silicon with TXM)
find /System/Volumes/Preboot -name "txm.macosx.release.im4p" 2>/dev/null

# SPTM firmware (chip-specific)
find /System/Volumes/Preboot -name "sptm.macosx.release.im4p" 2>/dev/null

# Both are in the restore firmware directory:
# /System/Volumes/Preboot/<UUID>/restore/Firmware/
```

### Step 2: Install Extraction Tool

```bash
pip3 install --break-system-packages pyimg4
```

pyimg4 handles Apple's IM4P container format (ASN.1 DER wrapper + LZFSE compression).

### Step 3: Extract the Mach-O Binary

```bash
# Extract TXM
pyimg4 im4p extract -i txm.macosx.release.im4p -o txm.raw

# Extract SPTM
pyimg4 im4p extract -i sptm.macosx.release.im4p -o sptm.raw
```

Output: decompressed Mach-O arm64e binary.

Typical sizes:
- TXM: ~170KB compressed → ~490KB decompressed
- SPTM: ~185KB compressed → ~550KB decompressed

### Step 4: Verify Extraction

```bash
file txm.raw
# Expected: Mach-O 64-bit executable arm64e

strings txm.raw | head -5
# Should show TXM version string and panic messages
```

### Step 5: Find Panic Strings

```bash
# List all panic conditions
strings txm.raw | grep "panic:"

# Find specific panic code context
strings txm.raw | grep -i "invalid\|boot.*state\|security.*mode"

# Get version info
strings txm.raw | grep "Version"
```

### Step 6: Map Panic Code to String

From TXM panic logs, you get: `TXM [Panic]: [code: 0xNN | M]`

The code maps to a specific `panic()` call in the binary. Common patterns:
- Boot state assertions: `panic: invalid secure boot state: %#x`
- Memory assertions: `panic: attempt to destroy already destroyed buffer`
- Crypto assertions: `panic: bogus digest length: %lu`
- Logic assertions: `panic: should never be called`

### Step 7: Deeper Analysis (Optional)

```bash
# Disassemble with objdump
objdump -d txm.raw > txm_disasm.txt

# Or load into Ghidra/IDA for full RE
# Base address from panic log: TXM load address field
# e.g., "TXM load address: 0xfffffe004031c000"
```

## Verification
- `file txm.raw` returns "Mach-O 64-bit executable arm64e"
- `strings txm.raw | grep -c panic` returns 20+ panic strings
- Version string matches panic log's TXM UUID

## Example

From panic log:
```
panic(cpu 2 caller 0xfffffe0055140010): TXM [Panic]: [code: 0x0000001A | 1]
TXM UUID: FC4B4161-29AA-3A66-8A86-5211332F59FB
```

After extraction:
```bash
$ strings txm.raw | grep "invalid secure boot"
panic: invalid secure boot state: %#x
```

→ Code 0x1A = "invalid secure boot state" assertion in TXM's boot state machine.

## Notes
- TXM binary is **universal** — same binary on A17/M3/A18/M5 (not chip-specific)
- SPTM binary is **chip-specific** — different per SoC family
- The IM4P container tag is `trxm` for TXM, `sptm` for SPTM
- Firmware is LZFSE compressed inside the IM4P (pyimg4 handles this automatically)
- Apple does NOT strip symbols from TXM/SPTM — panic strings are present in production
- The firmware is loaded at the address shown in panic logs ("TXM load address" field)
- TXM runs at GXF GL0, SPTM at GL2 — both above kernel privilege level
- No runtime debugging is possible — static analysis only

## References
- pyimg4: https://github.com/m1stadev/PyIMG4
- Apple Image4 format: https://www.theiphonewiki.com/wiki/IMG4_File_Format
