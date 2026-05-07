---
name: wireless-driver-control-frame-audit
description: |
  Systematic audit methodology for wireless driver control-frame and Information Element (IE)
  parsing in Linux kernel drivers (and equivalents — Windows, macOS, BSD).
  Use when: (1) auditing a vendor's WLAN driver for memory-safety bugs in beacon/probe-resp/
  assoc-frame parsing, (2) hunting for cross-vendor bug-class propagation (idioms copy-pasted
  across drivers), (3) mapping coverage gaps in helper-vs-raw-walk discipline, (4) pivoting
  from finding a single bug to finding its peers tree-wide.
  Covers: per-driver fingerprint construction, per-EID handler matrix, bug-class taxonomy
  (TLV underflow, vendor-IE deref-before-bound, edge-byte OOB, per-EID typed-pointer cast,
  cross-driver propagation, file-level inconsistency-within-driver), MLE/MBSSID/RNR
  Wi-Fi 6/7 surface analysis, and cross-OS protocol-parser-surface mapping.
author: David Maynor + Claude
version: 1.0.0
date: 2026-05-06
---

# Wireless Driver Control-Frame & IE-Parser Audit

## Problem

Wireless driver authors re-implement IE parsing per-driver, per-frame-type, per-file. The
same bugs (length-byte mishandling, vendor-IE OUI-prefix matching without bound checks,
typed struct pointer cast at `ptr+2` without verifying `ie_len >= sizeof(struct)`)
propagate across vendors and survive across decades because:

1. **Per-frame-type files written by different engineers** — `tdls.c` and `scan.c` in the
   same driver tree often have inconsistent length-check discipline for the same EID.
2. **C language has no type-system enforcement** — `(struct ieee80211_ht_operation *)(ptr + 2)`
   compiles fine when `ie_len < sizeof(struct ieee80211_ht_operation)`.
3. **Vendors fix instances, not classes** — when a CVE drops, the patch covers one EID; the
   class regenerates next time someone adds a new EID handler.

Maynor (2006 Apple Wi-Fi driver bugs) identified this class. WiFiTaco (CVE-2022-42719/720/721/722)
proved it survives in mac80211. This skill is the systematic methodology for finding
present-day instances.

## Context / Trigger Conditions

- Auditing a Linux/BSD/Windows wireless driver tree for memory-safety bugs
- Found one IE-parser bug; want to find its peers
- Building a tree-wide bug-class assessment (one finding → multi-driver disclosure)
- Checking if a known historical bug class (Maynor 2006, WiFiTaco 2022) regenerated in newer code
- Mapping cross-OS impact (Linux source → Windows/macOS closed-binary equivalents)

## Solution

### Phase 1: Map the protocol surface

Before auditing any driver, build (or reference) the canonical 802.11 vocabulary so you
know what you're looking at and what's missing.

**Vocabulary inventory** (extract from `include/linux/ieee80211.h` and modular headers):

| Category | Count (approx) | Source |
|---|---:|---|
| `WLAN_EID_*` (legacy IEs) | 228 | `ieee80211.h` enum |
| `WLAN_EID_EXT_*` (Wi-Fi 6/7) | 50+ | `ieee80211-eht.h`, `ieee80211-he.h` |
| `WLAN_CATEGORY_*` (action frame) | 25 | `ieee80211.h` enum |
| `WLAN_TDLS_*` (TDLS subtypes) | 11 | `ieee80211.h` |
| `WLAN_PUB_ACTION_*` (public action) | 30+ | `ieee80211.h` |
| `IEEE80211_FTYPE_*` / `STYPE_*` | 30+ | `ieee80211.h` |

```bash
grep "^\s*WLAN_EID_[A-Z]" include/linux/ieee80211.h | wc -l
grep "^\s*WLAN_EID_EXT_[A-Z]" include/linux/ieee80211*.h | wc -l
grep "^\s*WLAN_CATEGORY_[A-Z]" include/linux/ieee80211.h
```

**High-attack-value EIDs to focus on (legacy):**
SSID, SUPP_RATES, EXT_SUPP_RATES, DS_PARAMS, TIM, CHALLENGE, COUNTRY, ERP_INFO,
CHANNEL_SWITCH, EXT_CHANSWITCH_ANN, MEASURE_REPORT, HT_CAPABILITY, HT_OPERATION,
VHT_CAPABILITY, VHT_OPERATION, EXT_CAPABILITY, BSS_COEX_2040, OPMODE_NOTIF,
RSN, RSNX, MMIE, FAST_BSS_TRANSITION, MULTIPLE_BSSID, NON_TX_BSSID_CAP,
MOBILITY_DOMAIN, NEIGHBOR_REPORT, INTERWORKING, ROAMING_CONSORTIUM,
MESH_CONFIG/ID/PEER_MGMT, LINK_ID, **VENDOR_SPECIFIC (id 221)**.

**Wi-Fi 6/7 (often centralized in mac80211):**
HE_CAPABILITY, HE_OPERATION, HE_MU_EDCA, HE_SPR, HE_6GHZ_CAPA,
EHT_CAPABILITY, EHT_OPERATION, **EHT_MULTI_LINK (the MLE)**,
TID_TO_LINK_MAPPING, BANDWIDTH_INDICATION,
NON_INHERITANCE, KNOWN_BSSID, SHORT_SSID_LIST,
FILS_*, DH_PARAMETER.

### Phase 2: Per-driver fingerprint

For each driver in `drivers/net/wireless/`, count:

```bash
for d in $(find drivers/net/wireless/ -maxdepth 3 -mindepth 2 -type d); do
  c_count=$(find "$d" -maxdepth 1 -name "*.c" 2>/dev/null | wc -l)
  [ "$c_count" = "0" ] && continue

  eids=$(rg -c "WLAN_EID_" "$d" --type c 2>/dev/null | awk -F: '{s+=$2} END{print s+0}')
  rawwalk=$(rg -c -e "pos\[1\]" -e "ies\[1\]" -e "ie\[1\]" "$d" --type c | awk -F: '{s+=$2} END{print s+0}')
  helper=$(rg -c -e "cfg80211_find_ie" -e "cfg80211_find_elem" -e "for_each_element" "$d" --type c | awk -F: '{s+=$2} END{print s+0}')
  actfr=$(rg -c -e "WLAN_CATEGORY_" -e "ieee80211_is_action" "$d" --type c | awk -F: '{s+=$2} END{print s+0}')

  printf "%-50s %5d %5d %5d %5d\n" "$d" "$eids" "$rawwalk" "$helper" "$actfr"
done
```

**Tier classification:**
- **Tier 1** — High raw-walk count + many EIDs handled. Likely audit hot zone. (mwifiex, rtlwifi, ath6kl, iwlwifi/mvm, iwlwifi/mld)
- **Tier 2** — Mixed helper/raw walks. Worth checking. (mt76 family, ath11k/12k, rtw89, ipw2x00 legacy)
- **Tier 3** — Helper-dominated, FW-offloaded, or trivial. Lower priority. (brcmfmac, wcn36xx, wilc1000, qtnfmac, ti/wlcore)

**Heuristic:** raw-walk count alone doesn't predict bugs. ath6kl has 23 raw walks but they're well-defended. **Discipline** matters more than count. Use the matrix to identify candidates, then verify each site.

### Phase 3: Per-driver per-EID handler matrix

For each Tier 1/2 driver, count `WLAN_EID_<X>` references by high-value EIDs:

```bash
for eid in SSID SUPP_RATES DS_PARAMS TIM RSN RSNX VENDOR_SPECIFIC HT_CAPABILITY HT_OPERATION VHT_CAPABILITY VHT_OPERATION EXT_CAPABILITY BSS_COEX_2040 OPMODE_NOTIF FAST_BSS_TRANSITION MULTIPLE_BSSID; do
  n=$(rg -c "WLAN_EID_$eid\b" "$d" --type c 2>/dev/null | awk -F: '{s+=$2} END{print s+0}')
  printf '  %-22s %4d\n' "$eid" "$n"
done
```

A driver with double-digit handlers for HT/VHT/RSN/VENDOR_SPECIFIC has a lot of attack
surface. Use the matrix to direct deep audits.

### Phase 4: Bug-class taxonomy & tree-wide sweeps

For each known bug class, sweep tree-wide. The classes documented from prior audits:

#### Class A — Vendor-IE deref before bound check
```c
while (pos < end) {                     // pos can be end-1
    if (pos[0] == 221) {                 // pos[0] safe
        vendor_ie.length = pos[1];       // pos[1] OOB if pos == end-1
        vendor_ie.octet = &pos[2];
        memcmp(octet, oui, 3);            // 3 OOB bytes
    }
    if (pos + 2 + pos[1] > end) ...      // bound check AFTER use
}
```

**Sweep:**
```bash
rg -B1 -A6 "case WLAN_EID_VENDOR_SPECIFIC:|pos\[0\] == 221" drivers/net/wireless/ --type c
```

Then verify each site reads `pos[1]` / `pos[2..N]` BEFORE the bound check.

#### Class B — Edge-byte OOB on `while (pos < end)` walks
```c
while (pos < end) {                     // pos in [0, end-1]
    if (pos + 2 + pos[1] > end) break;  // pos[1] read; OOB if pos == end-1
    pos += 2 + pos[1];
}
```

**Sweep:**
```bash
rg -B1 -A4 "while \(.*pos < end\)" drivers/net/wireless/ --type c
```

The bound check itself reads `pos[1]` which is OOB by 1 byte when `pos == end-1`.
Functionally bounded (the OOB byte gets compared to a value), but technically UB and a
1-byte OOB read.

#### Class C — Per-EID typed-pointer cast without length check (WiFiTaco class)
```c
case WLAN_EID_HT_OPERATION:
    bss->bcn_ht_oper = (struct ieee80211_ht_operation *)(ptr + 2);
    // No check that ie_len >= sizeof(struct ieee80211_ht_operation)
    break;
```

**Sweep:**
```bash
rg -n "= \(struct ieee80211_(ht|vht|he|eht)_(operation|cap|capability)" drivers/net/wireless/ --type c
```

For each match, find the surrounding `case WLAN_EID_X:` and check whether the IE length
is validated against `sizeof(struct ieee80211_X_*)` BEFORE the cast.

#### Class D — TLV underflow class (`len -= ALIGN/roundup(...)` after raw bound check)
```c
while (len >= sizeof(*tlv)) {
    tlv_len = le32_to_cpu(tlv->length);
    if (len < tlv_len) return -EINVAL;       // bound: raw tlv_len
    len -= ALIGN(tlv_len, 4);                 // decrement: aligned (can underflow)
    data += sizeof(*tlv) + ALIGN(tlv_len, 4);
}
```

**Sweep:**
```bash
rg -B5 "len -= ALIGN\(|len -= roundup\(" drivers/ --type c | grep -B3 "if.*len <"
```

If the bound check uses raw `tlv_len` and the decrement uses `ALIGN(tlv_len, 4)`, the loop
counter underflows when `len ∈ [tlv_len, ALIGN(tlv_len,4)-1]`.

#### Class E — Cross-driver propagation (Atheros lineage)
The FreeBSD Atheros codebase → ath5k → ath9k → ath10k → ath11k → ath12k lineage carries
patterns forward across 20 years. Same idiom errors appear in multiple drivers because of
shared heritage. When you find a bug in one ath* driver, sweep its descendants.

#### Class F — File-level inconsistency-within-driver (the strongest signal)
Different files in the same driver have different length-check discipline for the same EID.
Canonical example: mwifiex `tdls.c` (correct: `if (ie_len != sizeof(struct ieee80211_X)) return;`)
vs `scan.c` (buggy: stores typed pointer without check) for `WLAN_EID_HT_OPERATION`.

**Heuristic:** when one file in a vendor's tree has correct length checks for EID X, other
files in the same driver handling X without that check are 70%+ likely to be missing it.

**Sweep methodology:**
```bash
# Find files in same driver handling the same EID
rg -l "WLAN_EID_HT_OPERATION" drivers/net/wireless/<vendor>/ --type c
# Diff their length-check discipline
for f in $(rg -l "case WLAN_EID_HT_OPERATION:" drivers/net/wireless/<vendor>/ --type c); do
  echo "=== $f ==="
  rg -B1 -A5 "case WLAN_EID_HT_OPERATION:" "$f"
done
```

### Phase 5: Wi-Fi 6/7 / MLE / RNR / FILS observation

Drivers don't directly parse `WLAN_EID_EXT_*` IEs — that's centralized in
`net/mac80211/parse.c` and `net/wireless/scan.c`. Drivers consume parsed structures via
mac80211 callbacks. **Modern HE/EHT/MLE bug class lives in mac80211, not drivers.**

**Audit `mac80211/parse.c` discipline:** Each per-EID case should call a dynamic size helper:
- `ieee80211_he_capa_size_ok`, `ieee80211_he_oper_size_ok` (HE)
- `ieee80211_eht_capa_size_ok`, `ieee80211_eht_oper_size_ok` (EHT)
- `ieee80211_mle_size_ok`, `ieee80211_mle_basic_sta_prof_size_ok` (MLE)
- `ieee80211_bandwidth_indication_size_ok`, `ieee80211_tid_to_link_map_size_ok`
- `ieee80211_uhr_oper_size_ok`, `ieee80211_uhr_capa_size_ok` (UHR / Wi-Fi 7+)

**Discipline pattern (good):**
```c
case WLAN_EID_EXT_HE_OPERATION:
    if (params->mode < IEEE80211_CONN_MODE_HE) break;
    if (len >= sizeof(*elems->he_operation) &&
        len >= ieee80211_he_oper_size(data) - 1)
        elems->he_operation = data;
    break;
```

Both `sizeof(struct)` minimum AND dynamic per-element size helper. Verify every per-EID
case follows this pattern.

**MLE-specific subtle bug (Class A.1):** `ieee80211_mle_common_size` returns
`sizeof(*mle) + mle->variable[0]`. For RECONF / PRIO_ACCESS types where the validator
does not enforce `mle->variable[0] >= common`, an attacker can supply `len = sizeof(*mle)`,
causing `mle->variable[0]` to be read 1 byte past the buffer end. Defended downstream by
`for_each_element`'s signed pointer arithmetic, but the OOB read itself is real.

**MBSSID nontransmitted profile** (`net/wireless/scan.c` `cfg80211_gen_new_ie`,
`cfg80211_merge_profile`, `cfg80211_is_element_inherited`) — post-CVE-2022-42719
hardened. Worth re-auditing if Wi-Fi spec adds new sub-element types.

### Phase 6: Cross-OS protocol-parser-surface mapping

Linux source acts as Rosetta Stone for closed Windows/macOS implementations of the same
hardware (inverse of the 2006 Maynor methodology, where FreeBSD Atheros source informed
RE of closed Windows/macOS drivers).

**Per finding, classify:**
1. **Host-side (OS-specific):** Linux iwlwifi has it; Windows iwlwifi-driver and macOS
   AirPort/Wi-Fi-driver may have analogous code re-implemented per OS.
2. **Firmware-protocol-side (cross-OS shared):** Same firmware blob shipped to all OSes;
   parsing bugs are in the host driver but the protocol attack-surface is identical.

**Disclosure scope expands accordingly:**
- Mainline-affecting Linux bugs → security@kernel.org + distros
- Host-driver bugs in Intel/Atheros/Marvell with closed counterparts → vendor security
  contacts on a multi-OS basis
- Pure firmware bugs → hardware vendor security

### Phase 7: Reporting

For each finding, document:
- **Site** (file:line)
- **Bug class** (A/B/C/D/E/F)
- **Reach** (network-attacker-OTA / FW-trust / supply-chain / privileged-local)
- **Compose-with** (which other findings chain to extend impact)
- **Cross-OS** (which other OS implementations likely affected)
- **Fix sketch** (which size_ok helper or pattern would close it)

Maintain a per-audit `wireless-ie-parser-map.md` document with:
- Per-driver fingerprint matrix
- Per-driver per-EID handler matrix
- Bug-class taxonomy with confirmed sites
- Outstanding sweep targets
- Coverage status checklist

This is **persistent across audit sessions** — designed to be updated incrementally rather
than rewritten.

## Anti-patterns / What NOT to do

- **Don't sweep "WLAN_EID_*" generically and stop.** The token count is a fingerprint, not
  a finding. Each candidate site needs human verification.
- **Don't trust raw-walk count as bug predictor.** ath6kl has high raw-walk count and
  excellent discipline; rtlwifi has low raw-walk count and a real OTA OOB bug.
- **Don't assume mac80211 is the bug zone in modern drivers.** Mac80211 post-WiFiTaco is
  well-disciplined; bugs persist in driver code that bypasses mac80211 helpers.
- **Don't skip the inconsistency-within-driver heuristic.** Tree-wide grep can't see the
  pattern; you need to compare files in the same driver.
- **Don't widen Coccinelle/grep patterns beyond what you can verify.** A pattern that flags
  500 false positives is worse than one that flags 5 confirmed bugs.
- **Don't allowlist `rtk proxy *`, `python3 *`, or other interpreter wildcards** in your
  Claude permission list — they are arbitrary code execution.

## References

- IEEE 802.11 spec — frame types, IE structure, action frame categories
- `include/linux/ieee80211.h` + modular headers (`ieee80211-he.h`, `ieee80211-eht.h`,
  `ieee80211-mesh.h`, `ieee80211-uhr.h`, etc.) — canonical kernel vocabulary
- `net/mac80211/parse.c` — gold-standard per-EID handler discipline reference
- `net/wireless/scan.c` — MBSSID profile reconstruction, post-CVE-2022-42719 patterns
- CVE-2022-42719 / 42720 / 42721 / 42722 (WiFiTaco) — mac80211 IE parsing class
- Maynor & Cache, BlackHat USA 2006 — original Apple Wi-Fi driver bug class

## Worked example

A previous audit produced `/home/dmaynor/raptor-research-log/wireless-ie-parser-map.md`
covering 35 driver subdirs, 228 EIDs, 4+1 bug classes with confirmed sites. That document
is the worked example of this methodology applied to a single source tree.
