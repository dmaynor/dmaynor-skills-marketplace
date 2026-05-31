---
name: apple-vuln-research-apple-silicon-kernel-layout
description: |
  Find the correct arm64e kernel and per-SoC kernelcache for a
  research target on Apple Silicon macOS. Use when:
  (1) `/System/Library/Kernels/kernel` reports as `Mach-O 64-bit
  executable x86_64` on an Apple Silicon Mac and you wonder which
  binary the system actually boots; (2) you need the per-SoC arm64e
  kernel for a specific Mac model (t8140 = A18 Pro / MacBook Neo,
  t8103 = M1, t8112 = M2, t6000/t6020/t6030/t6031/t6041/t6050 = M-Pro/
  Max/Ultra families, t8122/t8132 = newer A-series in Mac, t8142 =
  next-gen MacBook Air, vmapple = virtualization); (3) you need the
  monolithic prelinked kernelcache that the BootROM actually loads
  (it's NOT at /System/Library/Kernels and NOT named "kernel" — it's
  at /System/Volumes/Preboot/<UUID>/restore/kernelcache.release.macNg
  where macNg is a board-id, e.g. mac17g for Mac17,5); (4) you took
  a "pre-update kernel snapshot" by copying /System/Library/Kernels/
  kernel and a diff agent told you it's the wrong architecture;
  (5) you need to know whether two Mac models share a kernel build
  (for cross-platform vuln porting). Saves the wrong-arch baseline
  mistake that wastes hours of diff time.
author: Claude Code
version: 1.0.0
date: 2026-05-31
---

# Apple Silicon kernel layout — where the real kernel actually lives

## Problem

On Apple Silicon Macs, the file at `/System/Library/Kernels/kernel` is
**not** the kernel the system boots. It's an x86_64 stub kept for
compatibility / restore tooling. Researchers who naively copy that
file as a "kernel baseline" end up diffing the wrong architecture
across an OS update and waste hours before noticing.

This skill maps the actual layout: where each per-SoC arm64e kernel
lives, where the prelinked kernelcache lives, what each board-id
suffix means, and how to pick the right baseline for your research
target.

This was learned the hard way in the VS67 macOS 26.5 enumeration
work loop — a pre-26.5 "kernel snapshot" turned out to be x86_64
and the kernel-diff agent flagged it immediately.

## Trigger conditions

Use this skill when:

- `file /System/Library/Kernels/kernel` reports `Mach-O 64-bit
  executable x86_64` on an Apple Silicon Mac and you need to know
  what the system actually runs.
- You're capturing a "kernel baseline" before an OS update for diff
  purposes — make sure it's the right arch and the right SoC.
- You need to diff kernels across macOS versions and the kext-diff
  tool reports unrelated symbol changes that look like a different
  architecture.
- You're researching a specific Mac model (e.g. MacBook Neo /
  Mac17,5 / A18 Pro / t8140) and need the kernel + kernelcache that
  model actually boots.
- You want to confirm two Mac models share the exact same kernel
  build (for cross-platform vuln applicability).

## The actual layout

### /System/Library/Kernels/

```
kernel                          Mach-O 64-bit executable x86_64   <-- legacy/compat stub
kernel.release.t8103            Mach-O 64-bit executable arm64e   <-- M1
kernel.release.t8112            Mach-O 64-bit executable arm64e   <-- M2
kernel.release.t8122            Mach-O 64-bit executable arm64e   <-- (A-series in Mac, newer)
kernel.release.t8132            Mach-O 64-bit executable arm64e   <-- (A-series in Mac, newer)
kernel.release.t8140            Mach-O 64-bit executable arm64e   <-- A18 Pro (MacBook Neo Mac17,5)
kernel.release.t8142            Mach-O 64-bit executable arm64e   <-- (next-gen A-series in Mac)
kernel.release.t6000            Mach-O 64-bit executable arm64e   <-- M1 Pro
kernel.release.t6020            Mach-O 64-bit executable arm64e   <-- M2 Pro / M2 Max
kernel.release.t6030            Mach-O 64-bit executable arm64e   <-- M3
kernel.release.t6031            Mach-O 64-bit executable arm64e   <-- M3 Max
kernel.release.t6041            Mach-O 64-bit executable arm64e   <-- M4
kernel.release.t6050            Mach-O 64-bit executable arm64e   <-- (newer M-series)
kernel.release.vmapple          Mach-O 64-bit executable arm64e   <-- virtualized Apple Silicon
```

These are the **raw kernels** — bare Mach-O, no kexts linked in. Use
these for kernel-only diffs (symbols, MIG subsystems, syscall tables,
mach traps).

### /System/Volumes/Preboot/<APFS-UUID>/restore/

This is where the **prelinked kernelcaches** live. Each macNg suffix
is a board-id Apple uses to bind a kernelcache to a specific Mac
model class.

```
/System/Volumes/Preboot/BEDC40F3-...-198BC93BBDED/restore/
  kernelcache.release.mac13g     # 13" MacBook Air M3 (T8112-class)
  kernelcache.release.mac13j     # (variant)
  kernelcache.release.mac14g     # ...
  kernelcache.release.mac15g     # 15" MacBook Air M3
  kernelcache.release.mac15j     # ...
  kernelcache.release.mac15s     # ...
  kernelcache.release.mac16g     # (M3 family)
  kernelcache.release.mac16j     # ...
  kernelcache.release.mac17g     # MacBook Mac17,5 (Neo, A18 Pro, t8140)
  kernelcache.release.vma2       # virtualized M2 Apple Silicon
```

A kernelcache is an IM4P-wrapped LZFSE-compressed Mach-O containing
the kernel + all prelinked kexts. **This is what the BootROM
actually loads.** For any work that touches kext code (e.g. diffing
a specific driver across an OS update), this is the right baseline,
not the bare per-SoC kernel.

The `<APFS-UUID>` in the path is the system snapshot UUID — find it
with:

```sh
ls /System/Volumes/Preboot/
```

There will usually be exactly one UUID-named directory (the active
boot snapshot).

### Board-id → Mac model mapping (incomplete but practical)

Apple doesn't publish a complete mapping. Approximate practical
guide (from observation on macOS 26 + cross-referencing IPSWs):

| Suffix | Model class | SoC |
|---|---|---|
| `mac13g/j` | Mac mini M3 / earlier M3 desktops | t8112-ish |
| `mac14g`  | (TBD) | |
| `mac15g/j/s` | MacBook Air 15" M3 | t6030 |
| `mac16g/j` | MacBook Air M3 + family | t6030 |
| `mac17g`  | **MacBook Neo (Mac17,5, A18 Pro)** | **t8140** |
| `vma2`    | Virtualized M2 (Apple's VM framework) | vmapple |

To identify yours definitively:

```sh
# Get your Mac's identifier
ioreg -l | grep -E 'product-name|model-number|board-id' | head
sysctl hw.model       # e.g. MacBookNeo1,1 or Mac17,5
# Then match against the kernelcache filenames — your Mac will
# typically boot the suffix whose digit matches the major model
# number (Mac17,x -> mac17g)
```

## Solution — picking the right file for your research task

Decision matrix:

| Task | Use this file |
|---|---|
| Kernel-only diff (symbols, MIG, syscalls, mach traps) | `/System/Library/Kernels/kernel.release.<soc>` |
| Kext diff across OS versions | `/System/Volumes/Preboot/<UUID>/restore/kernelcache.release.macNg` (extract with pyimg4 + kmutil splitkc — see `apple-vuln-research-kernelcache-kext-binary-diff`) |
| Live kernel state inspection | `kmutil showloaded`, `ioreg`, `sysctl` against running kernel |
| Cross-platform vuln porting (Mac model A → Mac model B) | Diff both kernelcaches (same OS version, different macNg suffixes) |
| Pre-OS-update baseline snapshot | Copy `kernel.release.<soc>` AND `kernelcache.release.macNg` to a backup location BEFORE running `softwareupdate -i` |

### Pre-update snapshot recipe

Always capture both for any pre-update baseline:

```sh
SOC=t8140      # change to your SoC
BOARD=mac17g   # change to your board suffix
DEST=~/baselines/pre-26.5

mkdir -p "$DEST"
cp /System/Library/Kernels/kernel.release.$SOC "$DEST/kernel-$SOC-arm64e"

PREBOOT=$(ls -d /System/Volumes/Preboot/*/restore | head -1)
cp "$PREBOOT/kernelcache.release.$BOARD" "$DEST/kernelcache-$BOARD.macho"

# Verify both:
file "$DEST"/kernel-* "$DEST"/kernelcache-*.macho
shasum -a 256 "$DEST"/* > "$DEST/HASHES.txt"
```

The `kernel.release.$SOC` should report `Mach-O 64-bit executable
arm64e`. The kernelcache will report as `data` (it's an IM4P, not
a direct Mach-O until you extract it).

## Verification

Sanity-check your selection:

```sh
# Confirm the kernel actually loaded matches the file you snapshotted
uname -v
# e.g. "Darwin Kernel Version 25.5.0: Mon Apr 27 20:41:22 PDT 2026;
#       root:xnu-12377.121.6~2/RELEASE_ARM64_T8140 arm64"
# Note T8140 in the build banner — confirms t8140 kernel was booted.

# Confirm the kernelcache .macho contains your booted version string
strings /System/Volumes/Preboot/*/restore/kernelcache.release.mac17g | \
  grep -i 'xnu-' | head
```

If `uname -v` says `T8140` and you snapshotted `kernel.release.t6020`,
that's the wrong file.

## Notes

- The x86_64 stub at `/System/Library/Kernels/kernel` exists for
  install media / migration / Rosetta-adjacent tooling. It is NEVER
  what the system boots on Apple Silicon. Stop using it.
- Apple sometimes adds new per-SoC kernels mid-OS-version (e.g. a
  point release that introduces support for a new Mac model). Always
  re-`ls /System/Library/Kernels/` after an OS update to see if new
  SoC kernels appeared.
- The Preboot UUID changes per APFS install. Don't hardcode it; use
  `ls -d /System/Volumes/Preboot/*/restore | head -1`.
- For SPTM/TXM firmware on this Mac (separate from kernel), see
  `apple-vuln-research-txm-sptm-firmware-extraction`.
- For the actual kext-diff methodology that USES these files, see
  `apple-vuln-research-kernelcache-kext-binary-diff`.

## References

- xnu source (open-source kernel): https://github.com/apple-oss-distributions/xnu
- Asahi Linux SoC documentation (board-id mapping reference):
  https://github.com/AsahiLinux/docs/wiki
- Apple's IPSW download portal — IPSWs contain matching kernelcaches
  for each model class.
