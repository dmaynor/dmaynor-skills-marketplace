# Runbook: Windows Boot Failure Recovery — NVIDIA GPU + Fast Startup Hibernation

---

## 1. METADATA

| Field | Value |
|-------|-------|
| **Date** | 2026-02-28 |
| **Hardware** | Razer Blade 15 Advanced Mid 2021 (RZ09-0409) |
| **OS** | Windows 10 Home 22H2 Build 19045.3570 |
| **Drive** | NVMe CA6-8D1024 (953.87 GiB), GPT, UEFI boot |
| **Symptoms** | Machine powers on but Windows never loads. No BSOD visible — appears to hang or restart during boot. NTFS volume has hibernation metadata forcing read-only mount from Linux. |
| **Root Cause** | Corrupt Fast Startup hibernation state (`RSTR` signature in 32 GB `hiberfil.sys`) containing an unstable NVIDIA GPU driver session that was actively BSODing prior to shutdown. NTFS journal dirty from crash cycle. |
| **Outcome** | Hibernation metadata cleared via `ntfsfix`. User data (19 GB / 37,304 files) backed up to external drive. Machine ready for cold boot. |
| **Recovery Environment** | SystemRescue Linux (USB boot) |
| **Time to Resolution** | ~4 hours (diagnosis + repair + backup) |

---

## 2. DECISION TREE

Follow this numbered flowchart from the top. Each step includes the condition to check, the action to take, and what to do if the action fails.

```
1. CAN YOU BOOT TO LINUX FROM USB?
   ├─ YES → Go to 2
   └─ NO  → Use a different machine to create a SystemRescue USB
            (https://www.system-rescue.org/). Boot from USB via F12 boot menu.

2. IS THE NVME DRIVE VISIBLE?
   Run: lsblk
   ├─ YES (nvme0n1 or similar appears) → Go to 3
   └─ NO  → Check BIOS for NVMe mode (RAID vs AHCI).
            Try: nvme list
            If still nothing → possible dead drive or firmware issue. Stop.

3. IS THE PARTITION TABLE INTACT?
   Run: fdisk -l /dev/nvme0n1
   ├─ YES (GPT with EFI + NTFS partitions visible) → Go to 4
   └─ NO  → If GPT header damaged, try: gdisk -l /dev/nvme0n1
            If no partitions at all → drive may need data recovery tools (testdisk).

4. CAN YOU MOUNT THE WINDOWS PARTITION?
   Run: mount -t ntfs-3g -o ro /dev/nvme0n1p4 /mnt/win
   ├─ YES (mounts, even if read-only) → Go to 5
   └─ FAILS with "unclean filesystem" → Go to 9 (ntfsfix first)
   └─ FAILS with BitLocker error → Need BitLocker recovery key. Stop unless key available.

5. IS THE VOLUME BITLOCKER ENCRYPTED?
   Run: xxd -l 16 /dev/nvme0n1p4 | grep "FVE-FS"
   ├─ NO (shows "NTFS" OEM ID) → Go to 6
   └─ YES → Need BitLocker recovery key before proceeding. Check Microsoft account.

6. DIAGNOSE: READ REGISTRY HIVES
   Copy hives to writable location first (FUSE mount blocks in-place reads by some tools):
     cp /mnt/win/Windows/System32/config/SOFTWARE /mnt/tmp/diagnostic/
     cp /mnt/win/Windows/System32/config/SYSTEM /mnt/tmp/diagnostic/
   Read with chntpw:
     chntpw -e /mnt/tmp/diagnostic/SOFTWARE → check Windows version, build
     chntpw -e /mnt/tmp/diagnostic/SYSTEM   → check Select\Current, boot state, driver config
   ├─ Registry readable → Go to 7
   └─ Registry corrupt → Go to 12 (System Restore)

7. DIAGNOSE: CHECK FOR HIBERNATION STATE
   Run: xxd -l 4 /mnt/win/hiberfil.sys
   ├─ Signature is "RSTR" (Fast Startup) → This is likely the boot blocker. Go to 9.
   ├─ Signature is "hibr"/"HIBR" (full hibernation) → Go to 9.
   ├─ Signature is "wake"/"WAKE" (already resumed) → Not hibernation issue. Go to 8.
   └─ No hiberfil.sys → Not hibernation issue. Go to 8.

8. DIAGNOSE: CHECK CRASH DUMPS AND BCD
   Check minidumps: ls -la /mnt/win/Windows/Minidump/
   Check BCD: copy /mnt/efi/EFI/Microsoft/Boot/BCD to writable location, read with chntpw
   Check boot files exist: ls -la /mnt/win/Windows/System32/ntoskrnl.exe winload.efi
   ├─ Crash dumps show GPU errors (0x116, 0x119) → GPU driver issue. Go to 10.
   ├─ Crash dumps show disk errors (0x7A, 0x77) → Disk issue. Run chkdsk from WinRE.
   ├─ BCD missing/corrupt → Rebuild BCD from WinRE. Go to 11.
   ├─ Boot files missing → Run sfc/DISM from WinRE. Go to 11.
   └─ Everything looks fine → Try ntfsfix anyway (Go to 9), then WinRE Startup Repair (Go to 11).

9. FIX: CLEAR HIBERNATION WITH ntfsfix
   umount /mnt/win
   ntfsfix /dev/nvme0n1p4
   ├─ SUCCESS ("processed successfully") → Remount and verify: mount -t ntfs-3g /dev/nvme0n1p4 /mnt/win
   │   ├─ Mounts read-write → Hibernation cleared. Go to 13 (backup then reboot).
   │   └─ Still read-only → Run ntfsfix again with: ntfsfix -d /dev/nvme0n1p4
   └─ FAILS → Go to 11 (WinRE recovery)

10. FIX: GPU DRIVER ISSUE
    If you can boot (after ntfsfix):
    a. Boot Windows into Safe Mode via WinRE:
       bcdedit /set {current} safeboot minimal
    b. Uninstall NVIDIA driver from Device Manager
    c. Remove safeboot: bcdedit /deletevalue {current} safeboot
    d. Reboot normally, install fresh NVIDIA drivers
    ├─ If Windows won't boot even after ntfsfix → Go to 11
    └─ If Safe Mode also crashes → Go to 12

11. FIX: WINRE RECOVERY
    Boot to recovery (F12 → recovery partition, or Shift+restart):
    Troubleshoot → Advanced Options → Command Prompt
    Run:
      bcdedit /set {current} safeboot minimal
      powercfg /h off
      chkdsk C: /f
    Exit, select "Continue" to boot.
    ├─ Boots to Safe Mode → Go to 10 (fix GPU driver)
    └─ Still fails → Go to 12

12. FIX: SYSTEM RESTORE
    Boot to WinRE → Troubleshoot → Advanced Options → System Restore
    Choose a restore point from before the crash cascade began.
    ├─ Restore succeeds → Boot normally, update drivers immediately
    └─ No restore points / restore fails → Consider Windows Reset or clean install
       (user data should already be backed up from step 13)

13. BACKUP USER DATA BEFORE RISKY OPERATIONS
    Always back up before attempting fixes that modify the volume.
    Mount external drive, rsync critical directories:
      rsync -av --progress --exclude='AppData' --exclude='NTUSER*' \
        /mnt/win/Users/<username>/ /mnt/backup/<backup-name>/
    See Commands Reference for full exclusion list.
    → After backup, proceed with the appropriate fix step above.
```

---

## 3. COMMANDS REFERENCE

### System Reconnaissance

| Command | What It Does | How to Interpret |
|---------|-------------|-----------------|
| `lsblk` | Lists all block devices and partitions | Look for `nvme0n1` (NVMe) or `sda` (SATA). Partitions show as children. |
| `fdisk -l /dev/nvme0n1` | Shows partition table with types and sizes | Expect: EFI (100M), Microsoft reserved (16M), NTFS data (large), Recovery (1+ partitions) |
| `mount \| grep nvme` | Shows current mount status of NVMe partitions | `fuseblk (ro,...)` = read-only FUSE mount. Likely hibernation metadata blocking RW. |
| `lsusb` | Lists USB devices | Useful for identifying external drives, boot media |
| `efibootmgr -v` | Lists UEFI boot entries with device paths | Shows boot order. `Boot0000` is typically Windows Boot Manager. Read-only command. |

### Registry Reading (from Linux)

| Command | What It Does | How to Interpret |
|---------|-------------|-----------------|
| `cp /mnt/win/Windows/System32/config/SOFTWARE /mnt/tmp/diagnostic/` | Copies registry hive to writable location | **Required** — chntpw cannot read from read-only FUSE mount |
| `chntpw -e /mnt/tmp/diagnostic/SOFTWARE` | Interactive registry editor (read mode) | Navigate with `cd`, list with `ls`, show values with `cat`. Type `q` to quit. |
| `cd Microsoft\Windows NT\CurrentVersion` then `cat ProductName` | Gets Windows version from SOFTWARE hive | Shows edition (Home/Pro), build number, registered owner |
| `cd Select` (in SYSTEM hive) | Shows boot control set selection | `Current=1` means ControlSet001 is active. `Failed=0` means no recorded boot failure. |
| `cd ControlSet001\Services\<drivername>` | Shows driver registration | `Start`: 0=boot, 1=system, 2=auto, 3=demand, 4=disabled. `ErrorControl`: 0=ignore, 1=normal, 3=critical. |

### Crash Dump Analysis

| Command | What It Does | How to Interpret |
|---------|-------------|-----------------|
| `ls -la /mnt/win/Windows/Minidump/` | Lists blue screen crash dumps | Each `.dmp` file = one BSOD. Dates show when crashes occurred. |
| `xxd -s 0x38 -l 4 -e <file>.dmp` | Reads bugcheck code from minidump header | Common GPU codes: `0x116` = VIDEO_TDR_FAILURE, `0x119` = VIDEO_SCHEDULER_INTERNAL_ERROR |
| `xxd -s 0x40 -l 32 -e <file>.dmp` | Reads bugcheck parameters (4 x 8-byte values) | Param interpretation varies by bugcheck code. See MSDN for specifics. |
| `xxd -l 8 /mnt/win/Windows/MEMORY.DMP` | Checks full memory dump signature | `PAGEDU64` = valid 64-bit kernel dump. Large file (often 10-30 GB). |

### Hibernation Analysis

| Command | What It Does | How to Interpret |
|---------|-------------|-----------------|
| `xxd -l 4 /mnt/win/hiberfil.sys` | Reads hibernation file signature | `RSTR` = Fast Startup state. `hibr`/`HIBR` = full hibernation. `wake` = already resumed. |
| `ls -lh /mnt/win/hiberfil.sys` | Shows hibernation file size | Typically 40-75% of RAM. 32 GB file on 32 GB RAM system is normal for Fast Startup. |

### Boot Configuration

| Command | What It Does | How to Interpret |
|---------|-------------|-----------------|
| `cp /mnt/efi/EFI/Microsoft/Boot/BCD /mnt/tmp/diagnostic/BCD_UEFI` | Copies UEFI BCD for reading | The primary BCD on UEFI systems |
| `chntpw -e /mnt/tmp/diagnostic/BCD_UEFI` | Reads BCD as registry hive | Navigate to `Objects\{guid}\Elements` — look for `12000004` (Description) and `22000002` (SystemRoot) |
| `xxd -s 0x3 -l 4 /dev/nvme0n1p4` | Reads NTFS OEM ID from boot sector | Should show `NTFS`. If `FVE-FS` → BitLocker encrypted. |

### Boot File Verification

| Command | What It Does | How to Interpret |
|---------|-------------|-----------------|
| `ls -la /mnt/win/Windows/System32/ntoskrnl.exe` | Checks kernel exists | ~10 MB, should have recent date matching last Windows Update |
| `ls -la /mnt/win/Windows/System32/winload.efi` | Checks UEFI boot loader | ~1.8 MB. This is what BCD points to. |
| `ls -la /mnt/win/Windows/System32/drivers/ntfs.sys` | Checks NTFS driver | ~2.8 MB. Critical for reading the OS partition. |
| `ls -la /mnt/win/Windows/System32/drivers/{disk,volmgr,pci}.sys` | Checks storage stack drivers | All must be present for disk access during boot. |

### Repair Commands

| Command | What It Does | How to Interpret |
|---------|-------------|-----------------|
| `umount /mnt/win` | Unmounts Windows volume | **Must** unmount before running ntfsfix |
| `ntfsfix /dev/nvme0n1p4` | Clears hibernation metadata and NTFS journal | Success: "$MFT and $MFTMirr OK", "journal emptied", "processed successfully". Clears the dirty flag so Windows does a cold boot. |
| `ntfsfix -d /dev/nvme0n1p4` | Clears dirty flag only (less aggressive) | Use if standard ntfsfix doesn't resolve the issue |
| `mount -t ntfs-3g /dev/nvme0n1p4 /mnt/win` | Remounts after ntfsfix | If it mounts RW (no `ro` in mount output), hibernation metadata is cleared. |

### WinRE Commands (run from Windows Recovery Command Prompt)

| Command | What It Does |
|---------|-------------|
| `bcdedit /set {current} safeboot minimal` | Sets Windows to boot into Safe Mode on next restart |
| `bcdedit /deletevalue {current} safeboot` | Removes Safe Mode flag (run after fixing the issue) |
| `powercfg /h off` | Disables hibernation and Fast Startup, deletes hiberfil.sys |
| `chkdsk C: /f` | Fixes filesystem errors on the Windows volume |
| `sfc /scannow` | Scans and repairs protected system files |
| `DISM /Online /Cleanup-Image /RestoreHealth` | Repairs the Windows component store |

### Data Backup

| Command | What It Does |
|---------|-------------|
| `lsblk` | Identify external backup drive (look for new device after plugging in) |
| `mount /dev/sdX2 /mnt/backup` | Mount external drive (adjust device as needed) |
| `rsync -av --progress --exclude=... <src> <dst>` | Backup with progress, preserving attributes |
| `du -sh /mnt/win/Users/<user>/*/` | Size breakdown of user profile subdirectories |

#### Recommended rsync Exclusions for Windows User Profile Backup

```bash
rsync -av --progress \
  --exclude='AppData' \
  --exclude='NTUSER*' \
  --exclude='ntuser*' \
  --exclude='.vscode' \
  --exclude='.stm32cubemx' \
  --exclude='.stmcufinder' \
  --exclude='.openjfx' \
  --exclude='.ghidra' \
  --exclude='STM32Cube' \
  --exclude='STM32CubeIDE' \
  --exclude='Saved Games' \
  --exclude='gpt4all' \
  --exclude='Apple' \
  --exclude='*.rep' \
  /mnt/win/Users/<username>/ /mnt/backup/<backup-name>/
```

**Notes:**
- `AppData` is the largest directory (often 50-150 GB) and contains mostly caches, not user data
- `NTUSER*` are registry hive files — not useful outside Windows and can cause permission errors
- Always run `du -sh` on subdirectories first to identify large directories worth excluding
- If backing up to exFAT: NTFS symlinks/junctions will produce non-fatal errors (expected, safe to ignore)

---

## 4. KNOWN PITFALLS

### Pitfall 1: chntpw Cannot Open Hives on Read-Only FUSE Mount

**Symptom:**
```
openHive(/mnt/win/Windows/System32/config/SOFTWARE) failed: Read-only file system
chntpw: Unable to open/read a hive, exiting..
```

**Cause:** `chntpw` attempts to open files read-write by default, even in editor (`-e`) mode. When the NTFS volume is mounted read-only via FUSE (due to hibernation metadata), this fails.

**Workaround:** Copy the hive files to a writable location before reading:
```bash
mkdir -p /mnt/tmp/diagnostic
cp /mnt/win/Windows/System32/config/SOFTWARE /mnt/tmp/diagnostic/
cp /mnt/win/Windows/System32/config/SYSTEM /mnt/tmp/diagnostic/
chntpw -e /mnt/tmp/diagnostic/SOFTWARE
```

---

### Pitfall 2: NTFS Volume Mounts Read-Only Due to Hibernation

**Symptom:** `mount` shows `(ro,...)` or mounting fails with "Windows is hibernated, refused to mount".

**Cause:** When Windows shuts down with Fast Startup enabled, it writes a kernel hibernation state. The NTFS driver sets a metadata flag that prevents other operating systems from mounting the volume read-write (to protect the hibernated state).

**Workaround:**
```bash
umount /mnt/win
ntfsfix /dev/nvme0n1p4    # Clears hibernation flag and empties journal
mount -t ntfs-3g /dev/nvme0n1p4 /mnt/win   # Should now mount RW
```

**Warning:** This discards the Fast Startup hibernation state. This is acceptable when the hibernated state is known to be corrupt.

---

### Pitfall 3: ntfsinfo Fails While Volume Is FUSE-Mounted

**Symptom:**
```
Access is denied because the NTFS volume is already exclusively opened.
```

**Cause:** `ntfsinfo` opens the raw block device, which conflicts with the active FUSE mount.

**Workaround:** Unmount the volume first, or skip `ntfsinfo` and use other diagnostic methods (mount flags, `xxd` on boot sector, registry reading).

---

### Pitfall 4: rsync Symlink Errors on exFAT Target

**Symptom:**
```
rsync: [sender] symlink "/mnt/backup/razer_2021/Application Data" -> ...  failed: Function not implemented (38)
```

**Cause:** NTFS stores Windows compatibility junctions (Application Data, My Documents, Cookies, etc.) as reparse points. rsync tries to recreate them as symlinks, but exFAT doesn't support symlinks.

**Workaround:** These errors are non-fatal (rsync exit code 23). The junctions are not real user data — they're legacy compatibility pointers. Safe to ignore. Add `--no-links` to suppress if the warnings are distracting.

---

### Pitfall 5: I/O Errors on Specific Files (Bad NVMe Sectors)

**Symptom:**
```
rsync: [sender] read errors mapping ".../3b35f52bff2742ece7471b5c2448b58e.zip": Input/output error (5)
```

**Cause:** Physical bad sector or firmware-level read error on the NVMe drive. May indicate early drive failure.

**Workaround:** Note the affected files. rsync will skip them and continue. After booting Windows, run `chkdsk C: /r` (the `/r` flag locates bad sectors and recovers readable data). Monitor drive health with `smartctl -a /dev/nvme0n1` from Linux or CrystalDiskInfo from Windows.

---

### Pitfall 6: rsync Restarts Re-Scan Already-Transferred Files

**Symptom:** Killing and restarting rsync causes it to walk the entire directory tree again, even for files already transferred.

**Cause:** rsync without `--partial` or a previous `--log-file` doesn't know what was already sent (though it does skip files that match on the destination).

**Workaround:** Gather ALL exclusions and special requirements BEFORE starting rsync. Run `du -sh` on subdirectories first to identify large items worth excluding. Present the full command for review before execution.

---

### Pitfall 7: Razer BIOS Has No Option to Disable Splash Screen

**Symptom:** User wants to see POST/boot messages but Razer splash screen obscures them.

**Cause:** Razer firmware on RZ09-0409 does not expose a "Boot Logo" or "Full Screen Logo" toggle in the BIOS setup menu.

**Workaround:** Use **F12** during boot to access the one-time boot device menu. This interrupts the splash screen and shows available boot entries. There is no way to permanently disable the Razer logo on this model.

---

## 5. HARDWARE-SPECIFIC NOTES: Razer Blade 15 Advanced (RZ09-0409, Mid 2021)

### GPU: NVIDIA GeForce RTX 3080 Mobile

- **Driver instability is a known pattern on this model.** The combination of high TDP GPU in a thin chassis leads to thermal throttling and TDR (Timeout Detection and Recovery) failures.
- The NVIDIA display driver (`nvlddmkm.sys`) is **demand-start (Start=3)** and loaded from `DriverStore`, NOT from `System32\drivers\`. Its failure should not prevent Windows from booting — but it can crash the desktop session (DWM, explorer.exe) after boot.
- BSODs `0x116` (VIDEO_TDR_FAILURE) and `0x119` (VIDEO_SCHEDULER_INTERNAL_ERROR) are the hallmark codes for this issue.
- **Driver file location:** `\SystemRoot\System32\DriverStore\FileRepository\nvrzi.inf_amd64_<hash>\nvlddmkm.sys` (~57 MB)
- **Recovery approach:** Boot Safe Mode → uninstall NVIDIA adapter from Device Manager → reboot → install latest driver from nvidia.com.

### Thermal Considerations

- If GPU BSODs recur after driver update, the GPU may be thermally throttling or the thermal paste may need replacement.
- Razer Blade 15 Advanced models are known for thermal compound degradation after 2-3 years.
- Monitor temps with HWiNFO64 or GPU-Z after recovery. Sustained temps above 90C under load indicate thermal maintenance needed.

### Fast Startup (Hybrid Shutdown)

- Fast Startup is **enabled by default** on all Razer Blade laptops (and most OEM Windows 10/11 installs).
- When combined with a crashing GPU driver, it creates a boot loop: shutdown hibernates the crash state → resume restores the crash state → crash → repeat.
- **Always disable Fast Startup after recovery:** `powercfg /h off` (from elevated CMD or PowerShell).

### BIOS/Firmware

- Access BIOS setup: **F1** or **DEL** during boot (before Razer splash completes).
- One-time boot menu: **F12** during boot.
- No option to disable boot logo on this model.
- Check for firmware updates at https://support.razer.com/ (search for RZ09-0409).
- BIOS may have options for Thunderbolt security, NVMe mode — generally leave defaults unless troubleshooting specific issues.

### Partition Layout (Factory Default)

| Partition | Size | Purpose |
|-----------|------|---------|
| p1 | 18.3 GB | Factory recovery image (contains full Windows install + Razer drivers) |
| p2 | 100 MB | EFI System Partition |
| p3 | 16 MB | Microsoft Reserved |
| p4 | 934.5 GB | Windows OS + User Data (NTFS) |
| p5 | 1 GB | Windows Recovery Environment (WinRE backup, updated by Windows Update) |

### EFI Boot Entries

| Entry | Description |
|-------|-------------|
| Boot0000 | Windows Boot Manager (default) |
| Boot0001+ | USB devices (if any are plugged in) |

The factory recovery on p1 includes `Winre.wim` (414 MB, dated to factory build). The p5 recovery partition has a newer `Winre.wim` updated by Windows Update. WinRE is accessed via F12 boot menu or by selecting the recovery entry from the Windows Boot Manager.

---

## Post-Recovery Checklist

After Windows boots successfully:

- [ ] Run `powercfg /h off` to disable Fast Startup permanently
- [ ] Open Device Manager → Display Adapters → uninstall NVIDIA driver if BSODs were occurring
- [ ] Download and install latest NVIDIA driver from https://www.nvidia.com/drivers/
- [ ] Run `sfc /scannow` from elevated Command Prompt
- [ ] Run `DISM /Online /Cleanup-Image /RestoreHealth`
- [ ] Run `chkdsk C: /f` (and `/r` if I/O errors were seen)
- [ ] Check Windows Update for pending updates
- [ ] Check Razer firmware updates at https://support.razer.com/
- [ ] Install HWiNFO64 and monitor GPU temps under load
- [ ] Verify backed-up data is intact on external drive

---

*Generated from diagnostic session 2026-02-28. This runbook can be followed autonomously by another engineer or Claude agent for similar boot failures involving NVIDIA GPU crashes + Windows Fast Startup hibernation on Razer Blade laptops.*
