---
name: apple-vuln-research-daemon-enum-recovery
description: |
  Recover a complete message-type / frame-type / command-type enum and its
  dispatch table from a stripped Apple daemon binary (arm64e/x86_64, Mach-O)
  via static disassembly. Use when: (1) probing an Apple daemon (rapportd,
  sharingd, nearbyd, bluetoothd, sociald, identityservicesd, etc.) has
  surfaced integer message/frame types whose names and handlers are
  unknown, (2) you need to map which numeric types are reachable pre-trust
  vs. which are silently filtered (e.g. NoOp/keepalive), (3) you want to
  prove a handler is benign without running live probes, (4) you see
  `"### Ignoring unhandled frame 0x%02X (%s)"` or similar log strings and
  need the full valid-type table. Covers: adjacent-string enum detection
  in `__cstring`, ADRP literal-pool pivoting to find all name-lookup
  sites, reconstructing ARM64 jump tables from the
  `adr x17,#0; add x16, x17, ldrsw[tbl, idx, lsl #2]; br x16` pattern
  (where jump offsets show as `udf #N` pseudo-instructions in `otool -tV`),
  decoding chained-fixup pointers in `__DATA_CONST`, and detecting
  deliberate silent-case branches in default/unhandled paths.
author: dmaynor
version: 1.1.0
date: 2026-04-21
---

# Apple Daemon Enum & Jump-Table Recovery

## Problem

You've found a numeric message-type, frame-type, or command-type that an
Apple daemon accepts from the network or XPC, but the daemon is stripped
and the names/handlers aren't in any public header. You need:

1. The complete enum (all valid types, their names, and "holes" / reserved slots).
2. Which types dispatch to real handlers vs which are silent no-ops.
3. The exact VA of each handler, so you can continue reversing downstream.

Live probing gives you *behavior* (does type N log anything? does it
mutate state?) but not the *intent* embedded in the binary (is type N
deliberately silenced as a keep-alive, or silently dropped because it's
out-of-range?). Those two answers lead to different security verdicts.

## Context / Trigger Conditions

Use this skill when any of these hold:

- You observe `"### Ignoring unhandled frame 0x%02X (%s), ... bytes"` or a
  similar format string during live probing.
- You have a `cmp wN, #0xMM` / jump-table pattern visible in the daemon's
  disassembly and want to enumerate every case label.
- You need to confirm a handler is benign (no parser reach, no state
  change) *without* sending more probes to a production system.
- The enum name strings are clearly visible in `strings -a` output but
  their integer indexes are not — and the obvious guess (alphabetical
  order, source order, etc.) doesn't hold.

## Solution (4 phases)

### Phase A — Find the adjacent-string enum in `__cstring`

Apple daemons compile enum-to-name lookups as a packed string pool in
`__cstring`, with one ADRP+ADD literal-pool reference per case in the
corresponding switch statement. Step 1 is to find that pool.

```sh
# Target binary
BIN=/usr/libexec/rapportd          # or any stripped daemon
SLICE=/tmp/target.arm64e
lipo -thin arm64e "$BIN" -output "$SLICE" 2>/dev/null || cp "$BIN" "$SLICE"

# Find likely enum names by printing all strings with file offsets and
# looking for clusters of adjacent short strings
strings -a -t x "$SLICE" | awk '{print NR, $1, $0}' | less

# Once you spot a cluster (e.g. "Invalid\0NoOp\0PS_Start\0PS_Next\0..."),
# record each string's file offset and compute its VA:
#   VA = __cstring.vmaddr + (file_off - __cstring.fileoff)
# from otool -arch arm64e -l output
```

Signs you've found an enum pool:
- 6+ short (<30 byte) strings packed adjacent with no padding
- A leading `"Invalid"` or `"Unknown"` or `"None"` entry (common for enum[0])
- Names follow a taxonomic pattern (verbs, camelCase, short prefixes)

### Phase B — Pivot off the literal-pool ADRP base to find the switch

Every case in the corresponding C `switch(x)` compiles to an `adrp` + `add`
pair that points to the matching name-string. Since all the strings share
one 4K page, every case ADRP targets the *same* page. That makes the
switch body trivially locatable:

```sh
# Dump full disassembly once, re-grep forever
otool -arch arm64e -tV "$BIN" > /tmp/disasm.txt

# Compute the 4K page VA of your __cstring cluster, e.g. 0x10017d000
PAGE_VA=0x10017d000

# Find every ADRP to that page
grep -n "adrp.*0x${PAGE_VA##0x10017}" /tmp/disasm.txt  # may need fuzzy regex
grep -nE "adrp[[:space:]]+x[0-9]+,[[:space:]]+[0-9]+[[:space:]]+;[[:space:]]+${PAGE_VA}" /tmp/disasm.txt
```

Every hit is a case label. Otool annotates the subsequent `add` with the
literal-pool comment (e.g. `; literal pool for: "NoOp"`), which directly
resolves the enum → name mapping *per case label VA*. You now have the
unordered name set; Phase C gives you the ordering.

### Phase C — Reconstruct the jump table

If the switch is dense (contiguous 0..N range), the compiler emits a
jump table. The canonical ARM64 compiled-switch prologue is:

```
cmp     wINPUT, #MAX_CASE         ; bounds check
b.hi    DEFAULT_LABEL
adr     xANCHOR, #0               ; PC-relative anchor (THIS instruction's VA)
add     xTBL, xTBL, #TBL_OFFSET   ; table base (usually near the function epilogue)
ldrsw   x16, [xTBL, xINDEX, lsl #2]   ; load signed 32-bit offset
add     x16, xANCHOR, x16         ; case_VA = anchor + offset
br      x16
```

In `otool -tV` output the table data is disassembled as a run of `udf #N`
pseudo-instructions (each `udf` is a 4-byte jump-offset). The case target
for index `i` is:

```
case_VA(i) = ANCHOR_VA + udf_value_at_table[i]
```

Decode each `udf` entry, add the anchor VA, and cross-reference against
the case labels you found in Phase B. That gives you the
*index-to-handler* mapping (and by extension, *index-to-name*).

**Examples of what "default" jumps tell you:**
- A single default target reused across many indices = reserved slots
  (e.g. ftype 0x02, 0x0C-0x0F, 0x13-0x1F in rapportd).
- The default target typically points at code that prints "?" or logs an
  "ignoring unhandled" warning.

### Phase D — Detect deliberate silent-case branches

After the jump-table name-lookup runs, many dispatchers have a separate
*action* switch (which usually only covers a subset of types). Handlers
for "no-op" / "keep-alive" messages are often implemented NOT as
jump-table entries, but as a `cmp + b.eq` guard in the default path that
skips the "unhandled" warning and returns early.

Grep the default path for early-exit branches:

```
DEFAULT_VA=0x10000a374
# Read the 8-16 instructions at DEFAULT_VA in your disasm
# Look for:
#   cmp wN, #KNOWN_TYPE
#   b.eq FUNCTION_EPILOGUE_VA
# If the target is the function's `ldp x29,x30 ... ret`, that's a
# deliberate silent-return for the tested type.
```

If you find such a branch, the matching `KNOWN_TYPE` is a deliberately
silenced case — typically a keep-alive, heartbeat, or NoOp. It reaches
no parser, no handler, no log.

## Verification

Three cross-checks that your enum recovery is complete and correct:

1. **Index × name cross-consistency:** every case label the compiler
   emits in the switch body must have a matching jump-table `udf` entry,
   and vice versa. Mismatches indicate you missed a reserved-slot
   collapse or miscounted the table length.

2. **Multi-function agreement:** large daemons often have 2–3 *different*
   frame-name-lookup functions (e.g. rapportd has 3: the IDS dispatcher,
   a standalone `frame_name(int)`, and an
   `RPPeopleDaemon _bufferCloudMessage` version). All must agree on
   `index → name`. If one disagrees, it's usually a cloned function that
   predates a recent enum addition — worth noting.

3. **Empirical check on 1–2 types:** pick two types (one handled, one
   reserved) and trigger them live. The handled one should log its name
   and take the expected action; the reserved one should log "ignoring
   unhandled" with the "?" placeholder. Mismatch = your jump-table
   reconstruction is off by one.

## Example — rapportd frame type 0x01 (NoOp)

Applied to rapportd v715.2 (macOS 26.4.1):

- **Phase A:** strings cluster at file offset `0x17d100` with packed
  names `Invalid\0NoOp\0PS_Start\0PS_Next\0PV_Start\0PV_Next\0U_OPACK\0...`
  in `__cstring`.
- **Phase B:** 40+ `adrp x8, ... ; 0x10017d000` hits in one contiguous
  region starting at `0x10000a100`. Each `add` carries a literal-pool
  comment naming a frame type. Unordered name set recovered.
- **Phase C:** jump table at `0x10000a3ec`, anchor `adr` at
  `0x10000a120`. Decoded `udf` offsets → full index-to-handler table
  for types `0x00–0x22` (plus sparse table for `0x30, 0x31, 0x40–0x42`).
- **Phase D:** default path at `0x10000a374` contains
  `cmp w27, #0x1; b.eq 0x10000a3e0` — silent-return branch for ftype
  `0x01`. Confirms `0x01 = NoOp` is deliberately silenced
  (keep-alive / heartbeat).

Full walk-through:
`findings/os/rapport/rapportd-phase9-ftype-0x01-noop-handler.md` in
`~/code/apple-vuln-research`.

## Scripts

This skill ships with two helpers:

- `scripts/find_enum_strings.sh` — dump strings with offsets, flag
  adjacent-short-string clusters as enum candidates.
- `scripts/decode_jumptable.py` — given the anchor VA and the table
  range, print `index → case_VA → name` rows from an `otool -tV` dump.

## Notes

- Works identically on x86_64 (same literal-pool pivot; different
  jump-table prologue: `leaq + movslq` in place of `adr + ldrsw`).
- Chained-fixup pointer decoding (rebase target = bits[35:0],
  next = bits[62:51], bind = bit[63]) is only needed when the
  dispatch uses a `__DATA_CONST` pointer array instead of a jump
  table. That pattern is rarer for frame-type enums but common for
  selector registries and ObjC method lists.
- For frameworks that live only in the dyld shared cache
  (`CoreUtils.framework`, etc.), the technique still works but you
  need to extract the dylib first. Xcode's
  `dsc_extractor.bundle` (XROS/macOS variant) is the simplest
  route, though it sometimes fails on macOS 26 Cryptex caches. See
  the `macos-dyld-shared-cache-analysis` skill.
- Daemons sometimes have *three* dispatch axes: an outer frame-type
  switch, an inner payload-type switch (e.g. TLV8 type in HAP), and
  a state-machine switch (session state). Recovering one enum doesn't
  recover the others — apply the same method to each.
- This skill does NOT cover recovering the handler bodies themselves.
  That's a downstream task once you know the VAs. Reserved slots
  and silent-case branches are the *primary* security-relevant
  findings from the enum itself.

## References

- Mach-O __cstring section: `otool -arch <arch> -l <binary>`
- Chained-fixup pointer format: `<mach-o/fixup-chains.h>` from
  Apple's dyld source
- ARM64 switch codegen patterns: ARM Architecture Reference Manual,
  "Tables and branches" (C6.2.241, `BR`)
- rapportd Phase 9 finding (this skill's motivating example):
  `findings/os/rapport/rapportd-phase9-ftype-0x01-noop-handler.md`
