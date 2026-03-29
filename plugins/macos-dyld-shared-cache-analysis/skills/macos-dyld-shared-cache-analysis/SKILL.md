---
name: macos-dyld-shared-cache-analysis
description: |
  Analyze macOS framework binaries that live in the dyld shared cache.
  Use when: (1) otool/nm/strings/codesign fail on framework binaries with
  "No such file or directory", (2) framework binary is a broken symlink,
  (3) need to extract strings/symbols/linked-libs from shared-cache
  residents. Key tool: dyld_info (in /usr/bin/ on macOS 13+).
author: David Maynor / Claude Code
version: 1.0.0
date: 2026-03-29
---

# macOS dyld Shared Cache Binary Analysis

## Problem

On modern macOS (13+), nearly all system framework binaries live in the
dyld shared cache (`/System/Library/dyld/`), not as standalone files.
Framework paths like `/System/Library/Frameworks/CoreBluetooth.framework/CoreBluetooth`
exist as broken symlinks. Standard tools fail:

- `otool -L` → "No such file or directory"
- `nm` → "No such file or directory"
- `strings` → empty or error
- `codesign -dvvv` → "No such file or directory"
- `file` → "cannot open"

## Context / Trigger Conditions

- Framework binary path exists as symlink but `os.path.isfile()` returns False
- `otool`, `nm`, `strings` fail on a `/System/Library/Frameworks/` path
- Need to extract symbols, strings, linked libraries from system frameworks
- Building tools that analyze macOS framework binaries at scale

## Solution

Use `dyld_info` — Apple's tool for querying the shared cache directly.

### Detect if binary is in shared cache

```python
import os, subprocess

def is_in_shared_cache(path):
    if os.path.isfile(path):
        return False  # Real file on disk
    # Check if dyld_info knows about it
    res = subprocess.run(["dyld_info", "-platform", path],
                         capture_output=True, text=True, timeout=5)
    return res.returncode == 0 and res.stdout.strip() != ""
```

### Extract data from shared-cache binaries

| Need | Disk Binary | Shared Cache |
|------|-------------|-------------|
| Linked libraries | `otool -L` | `dyld_info -linked_dylibs` |
| Architecture | `file` / `lipo -info` | `dyld_info -platform` |
| Exported symbols | `nm -U` | `dyld_info -exports` |
| C strings | `strings` | `dyld_info -section __TEXT __cstring` |
| ObjC selectors | `strings` (mixed) | `dyld_info -section __TEXT __objc_methname` |
| ObjC classes | `strings` (mixed) | `dyld_info -section __TEXT __objc_classname` |
| Segment sizes | `otool -l` | `dyld_info -segments` |
| UUID | `otool -l` | `dyld_info -uuid` |
| Code signing | `codesign -dvvv` | Not available (use `-uuid` only) |

### Parse dyld_info output formats

```python
# Linked libraries — skip header lines
# Format: "    weak-link    /path/to/lib" or "               /path/to/lib"
stdout, _, _ = run_cmd(["dyld_info", "-linked_dylibs", binary_path])
in_section = False
for line in stdout.splitlines():
    stripped = line.strip()
    if "-linked_dylibs:" in stripped:
        in_section = True; continue
    if stripped.startswith("attributes"):
        continue  # header row
    if not in_section:
        continue
    if stripped.startswith("/"):
        libs.append(stripped)
    elif stripped.startswith("weak-link"):
        libs.append(stripped.split(None, 1)[1].strip())

# Exports — format: "0xADDRESS  _SymbolName"
stdout, _, _ = run_cmd(["dyld_info", "-exports", binary_path])
for line in stdout.splitlines():
    m = re.match(r"\s*0x[0-9a-fA-F]+\s+(.*)", line)
    if m and m.group(1).strip():
        symbols.append(m.group(1).strip())

# C strings — format: "0xADDRESS  string content here"
# IMPORTANT: use errors="replace" when decoding — binary data mixed in
stdout, _, _ = run_cmd(["dyld_info", "-section", "__TEXT", "__cstring", path])
for line in stdout.splitlines():
    m = re.match(r"\s*0x[0-9a-fA-F]+\s+(.*)", line)
    if m:
        strings_list.append(m.group(1))

# Segment sizes — format: "0x199A0F000    __TEXT    1064KB    r.x/r.x"
for line in stdout.splitlines():
    m = re.search(r"(\d+)KB\s+\S+/\S+", line)
    if m:
        total_size += int(m.group(1)) * 1024
```

### Handle subprocess encoding errors

dyld_info output may contain binary data mixed with text. Always use
`errors="replace"`:

```python
r = subprocess.run(cmd, capture_output=True, timeout=timeout)
stdout = r.stdout.decode("utf-8", errors="replace")
```

## Verification

```bash
# Verify a framework is in shared cache
dyld_info -platform /System/Library/Frameworks/CoreBluetooth.framework/CoreBluetooth
# Should output: "[arm64e]: platform macOS 26.4"

# Verify strings extraction
dyld_info -section __TEXT __cstring /System/Library/Frameworks/Security.framework/Security | head -5
```

## Notes

- ~97% of system frameworks are in the shared cache on macOS 26
- On-disk binaries (e.g., `/usr/sbin/networksetup`, `/usr/bin/python3`) work normally with traditional tools
- `dyld_info` is fast (~9ms per framework) — suitable for batch analysis
- The shared cache path is `/System/Library/dyld/dyld_shared_cache_arm64e` on Apple Silicon
- `codesign` does NOT work on shared-cache binaries — use `dyld_info -uuid` for identification
- Some framework binaries are universal (x86_64 + arm64e) on disk but arm64e-only in shared cache
