---
name: windows-recovery
description: >
  Diagnose and recover non-booting Windows machines from a Linux recovery environment
  (e.g., SystemRescue USB). Use this skill whenever a user or agent mentions: a Windows
  machine that won't boot, BSOD loops, NTFS filesystem errors, hibernation/Fast Startup
  issues, GPU driver crashes preventing boot, or needs to back up data from a dead Windows
  drive. Also triggers on: "my laptop won't boot", "Windows is stuck", "ntfsfix", "dirty
  filesystem", "rsync from Windows", "recover data from Windows drive", or any scenario
  involving Linux-based diagnosis of a Windows disk. When in doubt, use this skill — it
  is designed to run safely and will ask the operator before any destructive action.
---

# Windows Recovery Skill

Diagnose and recover non-booting Windows systems using a Linux recovery environment.
Covers: NTFS filesystem repair, hibernation state clearing, GPU driver crash recovery,
data backup via rsync, and BCD/boot configuration repair.

---

## Operator Modes

This skill supports three operators:

- **Human (interactive):** Presents plan, waits for confirmation per the selected interrupt mode.
- **Engineer (autonomous with oversight):** Presents plan, runs with interrupts at dangerous steps.
- **Agent (fully autonomous):** Presents plan and runs end-to-end; logs all actions; flags anomalies.

---

## Step 0: Present Plan and Set Interrupt Mode

**Always do this first.** Before running any commands:

1. State the diagnostic plan in plain language.
2. Identify which steps are **DANGEROUS** (irreversible or data-affecting):
   - `ntfsfix` — clears hibernation state, empties NTFS journal (irreversible)
   - `rsync` with `--delete` — destructive sync (only if used)
   - Any `dd`, `mkfs`, `fdisk`, `gdisk` writes
   - Registry edits via `chntpw`
   - BCD modifications
3. Ask the operator to choose an interrupt mode:

```
Interrupt modes:
  [A] Prompt before every action
  [B] Prompt before dangerous actions only  ← recommended default
  [C] Run fully — log everything, interrupt only on unexpected errors
```

Do not proceed until the operator selects a mode. Default to **[B]** if no response (agent context).

---

## Step 1: Verify Recovery Environment

```bash
lsblk                        # Confirm NVMe/SATA drive is visible
fdisk -l /dev/nvme0n1        # Verify GPT partition table intact
efibootmgr -v                # Read-only: confirm UEFI boot entries
```

**Expected:** NVMe visible, GPT with EFI + NTFS + Recovery partitions.
**If drive not visible:** Check BIOS NVMe mode (RAID vs AHCI). Run `nvme list`. If still missing — possible dead drive. Stop and report.

---

## Step 2: Attempt Mount

```bash
mount -t ntfs-3g -o ro /dev/nvme0n1p4 /mnt/win
mount | grep nvme
```

**Outcomes:**
- Mounts read-only (`fuseblk ro`) → hibernation metadata present. Proceed to Step 3.
- Mounts read-write → filesystem clean. Skip to Step 5.
- Fails with BitLocker error → need recovery key. Stop unless key is available.
- Fails with other error → note exact error, proceed to Step 6 (WinRE).

> ⚠️ **FUSE mount blocks raw device access.** `ntfsinfo`, `ntfsfix`, and similar tools require the volume to be unmounted first.

---

## Step 3: Diagnose

Run all diagnostics before any repairs.

### 3a. Check Hibernation State
```bash
xxd -l 4 /mnt/win/hiberfil.sys
```
- `RSTR` → Fast Startup hibernation (most common boot blocker)
- `hibr`/`HIBR` → Full hibernation
- `wake`/`WAKE` → Already resumed, not the issue
- File missing → Not a hibernation issue

### 3b. Read Registry Hives

> ⚠️ Copy hives to writable location first — chntpw cannot read from read-only FUSE mount.

```bash
mkdir -p /mnt/tmp/diagnostic
cp /mnt/win/Windows/System32/config/SOFTWARE /mnt/tmp/diagnostic/
cp /mnt/win/Windows/System32/config/SYSTEM /mnt/tmp/diagnostic/
chntpw -e /mnt/tmp/diagnostic/SOFTWARE   # Check Windows version/build
chntpw -e /mnt/tmp/diagnostic/SYSTEM    # Check boot state, driver config
```

In SYSTEM hive: `cd Select` → check `Current` (active ControlSet) and `Failed` value.
For driver state: `cd ControlSet001\Services\<drivername>` → `Start` value: 0=boot, 1=system, 2=auto, 3=demand, 4=disabled.

### 3c. Check Crash Dumps
```bash
ls -la /mnt/win/Windows/Minidump/
xxd -s 0x38 -l 4 -e <file>.dmp    # Read bugcheck code
```
GPU crash codes: `0x116` = VIDEO_TDR_FAILURE, `0x119` = VIDEO_SCHEDULER_INTERNAL_ERROR

### 3d. Check Boot Files
```bash
ls -la /mnt/win/Windows/System32/ntoskrnl.exe
ls -la /mnt/win/Windows/System32/winload.efi
```

---

## Step 4: Backup User Data

**Do this before any repair that modifies the volume.**

> ⚠️ DANGEROUS if `--delete` is used. Confirm exclusions with operator before running.
> Note: Gather ALL exclusions before starting. Restarting rsync re-scans the full tree.

```bash
# Identify large directories worth excluding first
du -sh /mnt/win/Users/<username>/*/

# Mount external drive
lsblk   # identify external drive (e.g., /dev/sdb1)
mkdir -p /mnt/backup
mount /dev/sdb1 /mnt/backup

# Run backup
rsync -av --progress \
  --exclude='AppData' \
  --exclude='NTUSER*' \
  --exclude='ntuser*' \
  /mnt/win/Users/<username>/ /mnt/backup/<backup-name>/
```

**Known non-fatal error:** rsync exit code 23 with symlink errors on exFAT target = Windows junction points. Not real user data. Safe to ignore or add `--no-links`.

**I/O errors on specific files** = possible bad NVMe sectors. Note affected files. rsync will skip and continue. Run `chkdsk C: /r` after Windows boots.

---

## Step 5: Repair — Clear Hibernation (ntfsfix)

> ⚠️ DANGEROUS — irreversible. Clears hibernation state and empties NTFS journal.
> Only proceed if hibernation signature is `RSTR` or `hibr` and state is known corrupt.

```bash
umount /mnt/win
ntfsfix /dev/nvme0n1p4
mount -t ntfs-3g /dev/nvme0n1p4 /mnt/win
mount | grep nvme   # Verify now RW
```

If still read-only after first run:
```bash
ntfsfix -d /dev/nvme0n1p4
```

---

## Step 6: Repair — GPU Driver (after ntfsfix succeeds)

If crash dumps show `0x116`/`0x119` and Windows boots after ntfsfix:

```bash
# From Windows elevated CMD after booting Safe Mode:
bcdedit /set {current} safeboot minimal
# Reboot → Safe Mode → uninstall NVIDIA from Device Manager
bcdedit /deletevalue {current} safeboot
# Reboot normally → install fresh driver from nvidia.com
```

Also: **always disable Fast Startup after recovery:**
```bash
powercfg /h off
```

---

## Step 7: Repair — WinRE (if ntfsfix insufficient)

Boot to recovery (F12 → recovery partition, or Shift+Restart from Windows):
```
Troubleshoot → Advanced Options → Command Prompt
bcdedit /set {current} safeboot minimal
powercfg /h off
chkdsk C: /f
```

---

## Step 8: Repair — System Restore (last resort before reinstall)

WinRE → Troubleshoot → Advanced Options → System Restore.
Choose restore point from before crash cascade. If no restore points or restore fails → Windows Reset or clean install. Ensure backup from Step 4 is complete first.

---

## Decision Tree (Quick Reference)

```
Drive visible? → NO → Check BIOS NVMe mode. Stop if still missing.
     ↓ YES
Partition table intact? → NO → Run gdisk, testdisk. Stop if unrecoverable.
     ↓ YES
BitLocker? → YES → Need recovery key. Stop.
     ↓ NO
hiberfil.sys signature?
  RSTR/hibr → Step 5 (ntfsfix) [after Step 4 backup]
  wake/missing → Step 3c crash dumps
     ↓
Crash dumps show 0x116/0x119? → YES → Step 6 (GPU driver)
     ↓ NO
BCD/boot files missing? → YES → Step 7 (WinRE)
     ↓ NO
ntfsfix + WinRE both fail → Step 8 (System Restore / reinstall)
```

---

## Hardware Notes: Razer Blade 15 (RZ09-0409, Mid 2021)

- BIOS: **F1/DEL** to enter setup, **F12** for one-time boot menu
- No option to disable boot logo on this model
- GPU: RTX 3080 Mobile — known TDR instability in thin chassis; thermal paste degrades after 2-3 years
- NVIDIA driver: demand-start (Start=3), loaded from DriverStore — failure alone should not prevent boot
- Fast Startup: enabled by default on all Razer OEM installs — **always disable after recovery**
- Partition layout: p1=Factory Recovery (18.3GB), p2=EFI (100MB), p3=MSR (16MB), p4=Windows (934.5GB), p5=WinRE (1GB)

---

## Post-Recovery Checklist

```
[ ] powercfg /h off                          # Disable Fast Startup permanently
[ ] Uninstall NVIDIA driver (Safe Mode)      # If GPU BSODs were occurring
[ ] Install latest NVIDIA driver             # nvidia.com
[ ] sfc /scannow                             # System file check
[ ] DISM /Online /Cleanup-Image /RestoreHealth
[ ] chkdsk C: /f  (add /r if I/O errors seen)
[ ] Windows Update
[ ] Razer firmware update (support.razer.com, search RZ09-0409)
[ ] Install HWiNFO64, monitor GPU temps under load (>90C sustained = thermal issue)
[ ] Verify backup integrity on external drive
```

---

## Known Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| chntpw on FUSE mount | "Access denied" | Copy hive to writable path first |
| ntfsinfo on mounted volume | "Exclusively opened" | Unmount first |
| ntfsfix on mounted volume | Fails/no-op | Unmount first |
| exFAT rsync symlink errors | Exit code 23, symlink failed | Non-fatal; add `--no-links` |
| I/O errors on specific files | Input/output error (5) | Note files; run chkdsk /r after boot |
| rsync restart rescans tree | Slow restart | Gather all exclusions before first run |
| Razer splash hides POST | Can't see boot errors | Use F12 to interrupt splash |

---

*Runbook derived from live incident 2026-02-28 (Razer Blade 15 RZ09-0409). Generalized for Windows NTFS boot failures diagnosed from Linux.*
