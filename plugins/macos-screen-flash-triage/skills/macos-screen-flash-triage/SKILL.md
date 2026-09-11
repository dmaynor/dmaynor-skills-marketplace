---
name: macos-screen-flash-triage
description: |
  Triage "my screen just flashed like a screenshot" reports on macOS by reading
  WindowServer/SkyLight unified logs. Use when: (1) user reports random screen
  flashes resembling Cmd+Shift+3 with no saved screenshot file, (2) need to
  distinguish screen-capture activity (replayd / SCK / screencapture) from
  benign Spaces/Mission-Control transitions, Stage Manager moves, Notification
  Center slide-ins, or HDR re-mode events, (3) auditing whether a sandboxed
  app is actually capturing the screen vs. just probing TCC permissions.
  Covers macOS 14–26 (Sonoma → 26) on Apple Silicon. Includes the specific
  log markers that prove "this was a swipe gesture, not surveillance."
metadata:
  author: Claude Code
  version: 1.1.0
  date: 2026-04-15
---

# macOS Screen Flash Triage

## Problem

User reports their screen "flashed like a screenshot was taken." Most of the
time **no screenshot was actually taken** — the flash is one of several
benign WindowServer events that look identical to a casual observer. Naive
investigation looks at `screencapture` processes and finds nothing, then
escalates to "is something spying on me?" when the real cause is a 3-finger
trackpad swipe or an HDR display reconfig.

This skill maps each visible-flash class to its log signature so you can
identify the cause from a single `log stream` burst.

## Trigger Conditions

- User says "my screen flashed like a screenshot was taken" or "white flash" or
  "the screen blinked"
- No new file in `~/Desktop` or `defaults read com.apple.screencapture location`
- No `screencapture` / `screencaptureui` in `ps`
- `replayd` may or may not be running (it's launched on demand and stays for a while)

## Solution: Decision Tree from a WindowServer Log Burst

### Phase 1: First, rule out actual capture

```sh
log show --last 30m --predicate 'process == "replayd" OR process == "screencapture" OR process == "screencaptureui"' --style compact
ls -lat ~/Desktop ~/Pictures 2>/dev/null | head
mdfind -onlyin ~ 'kMDItemIsScreenCapture == 1 && kMDItemFSCreationDate >= $time.today(-1)'
```

**Real capture markers (any of these = actual screen recording happened):**
- `screencaptureui` process launched + a new PNG appeared on Desktop
- `replayd ... -[RPConnectionManager processNewConnection:]:197 accepted client connection PID: <N>` followed by `RPRecordingManager` / `SCStream` activity from PID N
- `RPClient hasEntitlementToSkipAlert` is **not** by itself capture — it's just a connection (e.g. ControlCenter for the privacy indicator). Look for an actual `SCStream` start.
- TCC log line containing `function=TCCAccessRequest` (not `preflight=yes`) for `kTCCServiceScreenCapture`

If none of these → it's a UI event, not capture. Continue to Phase 2.

### Phase 2: Read the WindowServer burst

Capture a burst with:

```sh
log stream --predicate 'process == "WindowServer" OR process == "ContinuityCaptureAgent" OR process == "replayd"' --info
```

Then map markers to causes:

| Markers in burst                                                                                                                                                                                                       | Cause                                          | Why it looks like a flash                                                                                       |
|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|
| `AddWindowsToSpacesAndRemoveFromSpaces`, `OrderWindowGroup ... joined space N` then `parted space N`, **preceded by** `HSTouchHIDService ... Dispatching digitizer event with 3 children` (or 4) and `momentum scroll` | **3/4-finger trackpad swipe → Switch Spaces**  | Whole desktop slides sideways; if the other space is dark/empty/fullscreen-different, the transition reads as a flash |
| `FuseBoardServices ... updated window N from "none" to "visible"` for many windows in <100ms                                                                                                                           | **Notification Center / Widgets / Stage Manager** | Sheet slides in from edge, large region repaints                                                              |
| `RBSAssertionDescriptor "AppDrawing" target:<PID-of-WindowManager.app>` followed by `AppVisible target:<some-app-PID>` + `HW/SW cursor switched` + `Cursor disabled: failed set_cursor_surface`, with **2-finger** digitizer events (no Spaces movement) | **Stage Manager strip animation** (auto-reveal, focus swap, or app group rotation) | Strip slides in from left edge, focused window repositions/scales — the cursor surface failure is the visible flash |
| `HW/SW cursor switched` twice + `Cursor disabled: failed set_cursor_surface` + window joining/parting spaces                                                                                                           | **Fullscreen ↔ windowed app transition**       | Mode switch causes momentary black/blank frame                                                                  |
| `NSRemoteView deferKeyboardEventsToParticularWindow` + `viewbridge-key-window` + new `RBSAssertionDescriptor "AppVisible"`                                                                                             | **System sheet/overlay via XPC view-bridge** (TCC prompt, sharing menu, save dialog, Spotlight, Touch ID, login) | Modal pops in over current content                                                  |
| `Display N reconfigured` or `IODisplayWranglerSetDisplayPower` or `AppleMobileApNonceUserClient` events near a brightness change                                                                                       | **HDR re-mode / True Tone / auto-brightness shift** | Display recalibrates; perceptible luminance/color jump                                                       |
| `replayd ... accepted client connection PID: <ControlCenter>` only — no `SCStream` start                                                                                                                              | **Privacy indicator infrastructure check**     | Not a flash by itself; ControlCenter just attaches to replayd to manage the menubar dot                         |
| `ContinuityCaptureAgent ... magic:1 usable:1 ... publish camera` + `ScreenSharing` mention                                                                                                                            | **Continuity Camera coming online**            | Brief overlay pill shown                                                                                        |
| `ContinuityCaptureAgent ... magic:0 usable:0 ... Skip camera publishing due to incomplete onboarding` (any frequency)                                                                                                  | **NOT a flash cause** — agent watching idle paired phone | No UI is rendered while onboarding incomplete                                                          |

### Phase 3: Identify the involved app

Window operations name target PIDs (e.g. `RBSAssertionDescriptor| "AppVisible" target:649`). Resolve them:

```sh
ps -p <PID> -o pid,etime,user,command
```

If the PID belongs to a fullscreen-capable app (browser, IDE, video player) and you see windows moving between two space IDs, the verdict is "user swiped between spaces."

## Verification

Ask the user to **reproduce the flash on demand** while you stream:

```sh
log stream --predicate 'process == "WindowServer"' --info | tee /tmp/ws.log
```

…then the next flash burst will be timestamped in `/tmp/ws.log`. Match the pattern table above.

To confirm the trackpad-swipe hypothesis: have them disable
`System Settings → Trackpad → More Gestures → Swipe between full-screen
applications` and `Mission Control`. If flashes stop, case closed.

## Notes

- **TCC ScreenCapture preflight chatter is noise.** Lines containing
  `preflight=yes, query=1` are apps polling "do I have permission?" — they
  do not capture anything. Only `function=TCCAccessRequest` (without
  `preflight`) is an actual capture attempt.
- **`replayd` running ≠ capture in progress.** It stays alive ~10 min after
  any client disconnects, including ControlCenter probing for the privacy
  indicator. Look at its current XPC connections, not just its presence.
- **`SCAlertPrivateEntitlement` and "control center manager entitlements"**
  on a replayd client = ControlCenter (the menubar app). Confirm with
  `ps -p <PID>` — almost always `/System/Library/CoreServices/ControlCenter.app/...`.
- **`FuseBoard`** is the macOS 26 widget/Stage-Manager compositor. Window
  visibility flipping there is normal during gestures and edge swipes.
- **3-finger swipes can fire from palm contact while typing** — that's the
  most common explanation for "flashes at random intervals" with no other
  evidence. The `digitizer event with 3 children` line is the fingerprint.
- macOS 26 introduced the per-stream "X is recording your screen" pill
  overlay. If a real SCK stream starts/stops, that pill itself flashes.
  Confirm with a `replayd` client that's actively streaming (not just connected).

## Example

User report: "my screen flashes like screenshots, but I stopped that work."

Investigator runs `log stream` for WindowServer and captures a burst at
23:47:24. Burst contains:
- `Dispatching digitizer event with 3 children` followed by `Starting momentum scroll`
- `OrderWindowGroup ... window 201 joined space 16 ... parted space 16 ... joined space 17`
- `FuseBoardServices ... updated window 513 from "none" to "visible"`
- `RBSAssertionDescriptor "AppVisible" target:649`
- `HW/SW cursor switched`

No `replayd` SCStream start. No `screencapture` process. No new screenshot file.

**Verdict:** 3-finger trackpad swipe → Switch Spaces. PID 649 was the app
that became visible on the destination space. User likely brushing the
trackpad while typing.

## References

- Apple Developer: ScreenCaptureKit overview — https://developer.apple.com/documentation/screencapturekit
- Apple Developer: Continuity Camera — https://support.apple.com/guide/mac-help/use-iphone-as-webcam-mchl77879b8a/mac
- macOS unified logging: `man log`, `log help show`
