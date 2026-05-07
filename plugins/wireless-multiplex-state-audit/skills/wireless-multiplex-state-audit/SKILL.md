---
name: wireless-multiplex-state-audit
description: |
  Cross-driver audit methodology for protocol-multiplex state machines in wireless
  drivers — the layer where one radio is time-multiplexed across multiple links,
  bands, or protocols (Wi-Fi 7 EMLSR/MLSR, Wi-Fi Direct, NAN, TDLS, FTM, the
  AWDL-class architectural pattern).
  Use when: (1) auditing modern Wi-Fi drivers (iwlwifi/mld, mt7925, rtw89, mt7996,
  brcmfmac, mwifiex) for state-machine bugs, (2) hunting cross-vendor multiplex
  bugs that share architecture but differ in vendor terminology (Intel "EMLSR"
  vs Realtek "DBCC" vs Mediatek "set_active_links_async"), (3) investigating
  chip-firmware-vs-host-driver state divergence in any time-multiplexed radio
  (cellular modems, Bluetooth coex, NIC offload).
  Companion to wireless-driver-control-frame-audit (different lens — that one
  covers wire-format/IE parsing; this one covers state-machine transitions).
author: David Maynor + Claude
version: 1.1.0
date: 2026-05-06
---

# Wireless multiplex-state-machine audit

## Problem

Modern wireless drivers run **multiple protocols on the same radio**, time-multiplexed
by chip firmware with host-driver state mirroring. This is the architectural pattern
behind Apple's AWDL (AWDL signaling and normal Wi-Fi alternated on one radio),
Wi-Fi 7 MLO/EMLSR (multiple links rotated through one RF chain), Wi-Fi Direct + STA
concurrent, NAN service discovery alongside STA, TDLS peer connections bypassing
AP — all common in Linux drivers today.

The bug class is **uniformly state divergence between chip/firmware and host driver**:
the host's view of "what's the radio currently doing" disagrees with the chip's view,
during transition windows. This produces:

- Frames routed to the wrong link/vif
- Action frames intended for one protocol processed by another's handler
- FW commands executed against wrong link state
- Driver continues to drive a configuration the FW has already changed
- Host transmits on a link FW has demoted

Beer's 2020 iOS zero-click (CVE-2020-3843, AWDL state-machine memory corruption) is
the canonical instance of this bug class at Apple-scale. Linux drivers are not
immune; they have the same architectural shape.

## Context / Trigger Conditions

- Auditing an iwlwifi/mld, mt7925, mt7996, rtw89, brcmfmac, mwifiex (or similar)
  Wi-Fi driver tree
- Investigating Wi-Fi 7 MLO state-machine bugs
- Looking at NAN+STA+P2P concurrent vif modes and their interaction
- Hunting AWDL-class bugs in equivalent Linux drivers
- Reviewing FW-notification handlers that drive host-side state transitions
- Questioning whether host and chip can disagree about "what's the radio doing right now"

## Solution

### Phase 1: Identify the vendor's multiplex primitive

Each vendor names the same architectural pattern differently. Find which name applies:

| Vendor | Multiplex primitive name(s) | File hints |
|---|---|---|
| Intel iwlwifi/mld | **EMLSR** + 8 `IWL_MLD_EMLSR_BLOCKED_*` block-reasons | `mld/mlo.c`, `mld/iface.h` |
| Realtek rtw89 | **DBCC** (Dual Band Concurrent) + **MLSR/EMLSR** mode pair | `core.h`, `core.c` (`rtw89_core_mlsr_switch`) |
| Mediatek mt7925 | **set_active_links_async** + ROC coordination | `mt7925/main.c` (`mt7925_mac_set_links`, `mt7925_set_mlo_roc`) |
| Mediatek mt7996 | Multi-BSSID-per-radio (AP-side multiplex) | `mt7996/main.c` (`mt7996_vif_link_add`) |
| Broadcom brcmfmac | P2P + STA concurrent via vif role flag | older but same shape |
| Marvell mwifiex | TDLS + STA concurrent | `mwifiex/tdls.c`, heavy code base |

Search hints:
```bash
# State-machine entry points
rg -n "set_active_links\|change_vif_links\|change_sta_links" drivers/net/wireless/<vendor>/

# Vendor-specific multiplex names
rg -l "emlsr\|dbcc\|mlsr\|mlo_mode\|MLO_MODE" drivers/net/wireless/<vendor>/ --type c

# FW notification handlers (the chip-to-host state-transition surface)
rg -n "handle.*mode.*notif\|handle.*emlsr\|handle.*link.*switch\|handle_esr" drivers/net/wireless/<vendor>/
```

### Phase 2: Enumerate transition surfaces

For each vendor, build the list of:

**State sources** — what causes a transition:
- User action (link change request, P2P start, NAN start, TDLS setup)
- FW notification (ESR_RECOMMEND_LEAVE, ESR_FORCE_LEAVE, link switch failed, BT coex demand)
- Internal heuristic (TPT below threshold, channel load high, beacon missed)
- Timer (PREVENTION cooldown, EMLSR_BLOCKED_TMP_NON_BSS timeout)

**State destinations** — what state changes:
- Bitmap of active/usable/blocked-reasons
- Per-link state (active, sleeping, off-channel)
- FW commands sent (link config, channel switch)
- Per-vif state (mlo_mode, primary_link, deflink_id)

**Async-resolution windows** — gaps where chip and host see different state:
- `ieee80211_set_active_links_async()` returns immediately; resolution happens later
- FW command sent → driver assumes commit; actual commit happens at FW response
- Work-queue items deferred from interrupt context

### Phase 3: Hunt the AWDL-class state-divergence pattern

Concrete shapes to flag:

**Pattern M1 — FW notification action enum incompletely handled.**
A switch on FW-supplied action code where one branch falls through to default-warn
when it should drive a state transition.

```c
// BUG SHAPE: ESR_FORCE_LEAVE in iwlwifi/mld/mlo.c:362
switch (action) {
case ESR_RECOMMEND_LEAVE:
    iwl_mld_exit_emlsr(...);            // correct
    break;
case ESR_FORCE_LEAVE:
    IWL_DEBUG_EHT("force leave...");
    fallthrough;                         // <-- silent fall through
case ESR_RECOMMEND_ENTER:
default:
    IWL_WARN("Unexpected EMLSR notification: %d");  // <-- driver stays in EMLSR
}
```

Driver stays in old state while FW transitions. Sweep:
```bash
rg -B2 -A10 "switch.*action\|switch.*recommendation\|switch.*notif" \
   drivers/net/wireless/<vendor>/ --type c \
   | grep -B2 -A3 "fallthrough\|default:" \
   | grep -B5 "WARN\|warn"
```

**Pattern M2 — failure-revert path leaves intermediate state un-reverted.**
A multi-step state transition where one step fails midway; the revert handles
some steps but not others.

```c
// CONCERN SHAPE: rtw89_core_mlsr_switch in core.c:6480
rtw89_leave_lps(rtwdev);                    // step 1
ieee80211_stop_queues(rtwdev->hw);           // step 2
flush_work(&rtwdev->txq_work);               // step 3
ret = ieee80211_set_active_links(vif, ...);  // step 4
if (ret) goto wake_queue;
target = rtwvif->links[link_id];
if (unlikely(!target)) {
    ieee80211_set_active_links(vif, active_links);  // reverts step 4 ONLY
    ret = -EFAULT;
    goto wake_queue;
    // steps 1-3 NOT reverted — vif left in {LPS-exited, queues-stopped, work-flushed}
}
```

Sweep:
```bash
rg -B5 -A15 "ieee80211_set_active_links.*BIT\|set_active_links_async" \
   drivers/net/wireless/<vendor>/ --type c
```

For each match, trace the surrounding multi-step transition and verify all steps
have a revert path on failure.

**Pattern M3 — async resolution gap with conditional gate.**
Async link change is dispatched but pre-conditions (ROC reset, channel context
update) only run for a subset of cases.

```c
// SUBTLE GAP SHAPE: mt7925_mac_set_links in main.c:1095
if (band == NL80211_BAND_2GHZ ||
    (band == NL80211_BAND_5GHZ && secondary_band == NL80211_BAND_6GHZ)) {
    mt7925_abort_roc(...);
    mt7925_set_mlo_roc(...);
}
ieee80211_set_active_links_async(vif, sel_links);  // ALWAYS happens
// Other band combinations: link change without ROC reset
```

Sweep:
```bash
rg -B2 -A10 "set_active_links_async\|set_active_links\b" \
   drivers/net/wireless/<vendor>/ --type c
```

**Pattern M4 — refcount/bitmap update ordering.**
Multiple block-reasons added/removed by independent callers. If two callers
race on add/remove, the bitmap can transiently show "no blocks" when both
intended to maintain a block.

Search for block/unblock pairs that are not atomic:
```bash
rg -B1 -A5 "block_emlsr\|unblock_emlsr\|emlsr.blocked" \
   drivers/net/wireless/intel/iwlwifi/mld/ --type c
```

For each call site, check whether the read-modify-write of the bitmap is locked
or atomic. RCU-protected bitmaps with lockless updates are particularly
suspicious.

**Pattern M5 — FW link_id from notification used as array index.**
FW supplies a link ID in a notification; driver maps it to host-side link state
via array indexing.

```c
u32 fw_link_id = le32_to_cpu(notif->link_id);
struct ieee80211_bss_conf *bss_conf =
    iwl_mld_fw_id_to_link_conf(mld, fw_link_id);
```

Sweep:
```bash
rg -B1 -A5 "fw_id_to_link\|fw_link_id\|le32_to_cpu.*link_id" \
   drivers/net/wireless/<vendor>/ --type c
```

For each, verify the lookup function bound-checks `fw_link_id` against the
allocated table size. iwlwifi mld does (see TRACE-018 family) — but vendors
implementing similar lookups for the first time may not.

**Pattern M6 — sister-vif MAC-address aliasing.**
`addresses[i].addr[5]++` generates per-vif MAC by incrementing the last byte.
If frame routing does memcmp on first 5 bytes for any reason, sister vifs
collide.

Sweep:
```bash
rg "addr\[5\]\s*\+\+\|addr\[5\] =.*\+ 1" drivers/net/wireless/ --type c
```

For each match, find all comparisons of MAC addresses in the same driver and
verify they use full ETH_ALEN comparison.

### Phase 4: Cross-vendor pattern propagation

Once you've identified bug shapes in one vendor, check other vendors for the same
shapes. The architectural pattern is convergent — each vendor's state machine
has the same conceptual structure, so the bug shapes propagate.

| Bug class found in | Check in |
|---|---|
| iwlwifi/mld FW-notif fallthrough | rtw89 FW notif handlers, mt7925 mcu notif handlers, mwifiex FW event dispatch |
| rtw89 multi-step revert | iwlwifi/mld block_emlsr_sync revert, mt7925 set_mlo_roc revert |
| mt7925 band-pair gate | iwlwifi/mld phy_ctxt allocation gate, rtw89 channel switch gate |

### Phase 5: Map to FW-trust composition

Most state-machine bugs in this layer are **FW-trust gated** — they require the FW
to send a notification with specific contents. That makes them defense-in-depth on
their own, but they compose with FW-compromise findings (TLV underflow, testmode
SRAM-write) to form chains:

1. Compromise FW via TLV underflow (e.g., `wireless-driver-control-frame-audit`
   Class D) or testmode SRAM-write
2. Compromised FW sends crafted state-transition notifications
3. Host driver enters wrong state
4. Subsequent legitimate frames mis-routed / mis-encoded / dropped

Document each finding's compose-with relationship.

### Phase 6: Cross-OS implication

Apple AWDL was the first famous instance of this bug class. Beer's 2020 zero-click
exploited a state-machine memory-corruption in AWDL action-frame processing.

Linux Wi-Fi 7 drivers (iwlwifi/mld, mt7925, rtw89) have analogous primitives now.
The bug class is portable: same hardware, same firmware, different OS. Linux-side
findings inform what the closed Windows iwlwifi-driver and macOS Wi-Fi-driver
likely also have. Cross-OS disclosure scope.

### Phase 7: Reporting

For each finding, capture:
- **Vendor + driver path** (e.g., `intel/iwlwifi/mld`, `realtek/rtw89`)
- **Multiplex primitive name** (EMLSR / DBCC / set_active_links_async)
- **Bug pattern** (M1-M6 from Phase 3)
- **Trigger** (FW notification with specific content, race during multi-step
  transition, async-resolve window, etc.)
- **Reachability** (FW-trust + chain, network-attacker, race-condition, etc.)
- **Compose-with** (which FW-compromise primitives chain to it)
- **Cross-OS** (Windows / macOS implementations of same hardware)

## Anti-patterns

- **Don't audit only one driver.** The bug class is convergent. One driver's
  finding informs all other vendors with the same architectural pattern.
- **Don't trust grep alone.** State-machine bugs require reading the surrounding
  code to verify what the transition is supposed to do vs what it actually does.
- **Don't dismiss FW-trust bugs as low severity.** They compose with FW-compromise
  primitives. The chain matters.
- **Don't skip the FW-supplied-link_id lookups.** Even when FW is "trusted",
  bound-check the indices that come from FW. The validator should be there.
- **Don't expand "FW notification handler audit" to include parser bugs.**
  Wire-format parsing is a different lens (`wireless-driver-control-frame-audit`).
  Stay in the state-machine layer.

## References

- Apple AWDL: Beer, "An iOS zero-click radio proximity exploit odyssey", Project
  Zero 2020 — canonical instance of this bug class
- Linux Wi-Fi 7 EMLSR: `iwlwifi/mld/mlo.c`, `iwlwifi/mld/iface.h`
- Realtek DBCC: `rtw89/core.h`, `rtw89/core.c` (rtw89_core_mlsr_switch)
- Mediatek MLO: `mt7925/main.c` (mt7925_mac_set_links)
- IEEE 802.11be (Wi-Fi 7) MLO spec — multi-link operation primitives
- Companion skill: `wireless-driver-control-frame-audit` (wire-format parsing lens)

## Worked example

A previous audit (2026-05-06) applied this methodology to four Wi-Fi 7 drivers and
produced:

| Driver | Multiplex primitive | Finding | Pattern |
|---|---|---|---|
| iwlwifi/mld | EMLSR + 8 block-reasons | `ESR_FORCE_LEAVE` silently dropped at mlo.c:362-379 | M1 (FW-notif fallthrough) |
| rtw89 | DBCC + MLSR/EMLSR | Failure-revert leaves LPS/queues inconsistent at core.c:6480 | M2 (multi-step revert) |
| mt7925 | set_active_links_async + ROC | Band-pair gate skips ROC reset for some combinations at main.c:1095 | M3 (async-gate) |
| mt7996 | Multi-BSSID per radio | Clean | — |

Plus the cross-vendor pattern observation: convergent architecture, divergent
naming, common bug class. Worked example doc:
`~/raptor-research-log/2026-05-06-wireless-multiplex-state-findings.md`.
