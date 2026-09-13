---
name: apple-vuln-research-nsxpc-listener-enum
description: >-
  Enumerate an Apple daemon's server-side NSXPC surface using runtime
  reflection and controlled connection fingerprinting. Use to map Mach service
  listeners, Obj-C protocol methods, entitlement gates, and schema behavior
  without first extracting shared-cache frameworks. Revalidate on each OS build.
metadata:
  author: David Maynor / Claude Code
  version: 1.0.0
  date: 2026-04-21
  lifecycle: experimental
---

# Apple NSXPC Listener Attack-Surface Enumeration

## Problem

You target an Apple daemon that publishes multiple mach services (rapportd
exposes 11, sharingd ~10, nearbyd ~8). You want to answer four questions
without touching a debugger, dyld_shared_cache extractor, or IDA/Ghidra:

1. Which mach endpoints does the daemon actually listen on, and which
   Obj-C / Swift class serves each one?
2. What are the full method signatures of each NSXPC server-side
   protocol? (i.e. what can an entitled client call?)
3. Which endpoints reject unentitled callers at
   `-listener:shouldAcceptNewConnection:` time?
4. Which endpoints accept any connection but reject unknown selectors
   at NSXPC schema-validation time, vs. silently drop, vs. have no
   active listener?

The private framework binaries that host the listener classes (CoreUtils,
Rapport, CoreDuet, Sharing, *NearField*) live only in the dyld shared
cache on macOS 13+ — there is no on-disk Mach-O file for `nm`, `otool`,
`class-dump`, or `jtool` to open. But the daemon runs, the symbols are
loaded, and `objc_getClass()` / `objc_getProtocol()` still work.

## Context / Trigger Conditions

Invoke this skill when any of the following apply:

- Starting an audit of a new Apple LaunchAgent/LaunchDaemon (sharingd,
  nearbyd, homed, coreduetd, bluetoothd, wifip2pd, findmydeviced,
  rapportd, cloudpaird).
- `launchctl print gui/$UID/<label>` shows multiple `MachServices` and
  you need to know which ones are gated.
- You need NSXPC protocol method signatures for a CU*Daemon /
  RP*Daemon / CS*Daemon class, not just the daemon binary's own symbols.
- `ls /System/Library/PrivateFrameworks/<name>.framework/<name>` returns
  "No such file or directory" because the binary is shared-cache-only,
  yet `dlopen` on that path still succeeds at runtime.
- You already have the daemon's on-disk binary mapped (via
  `otool -oV`) and saw references to `_OBJC_CLASS_$_CU<name>Daemon`
  resolved from another framework — those imported class symbols are
  the server-side classes whose interfaces you want.

## Solution

### Step 1 — Enumerate the daemon's mach endpoints and listener classes

First, get the launchd-advertised endpoint list:

```bash
launchctl print gui/$UID/<label> | awk '/endpoints = \{/,/^\t\}/'
# Example (rapportd):
#   "com.apple.rapport.RPPairing"     = { port = 0x44927, active = 1 }
#   "com.apple.PairingManager"        = { port = 0x44b03, active = 1 }
#   ... 9 more ...
```

Then identify the ObjC listener delegate classes by scanning the daemon
binary for `-[<Class> listener:shouldAcceptNewConnection:]` selectors:

```bash
strings -a /usr/libexec/<daemon> | \
    grep -E '\-\[[A-Z][A-Za-z]+ listener:shouldAcceptNewConnection:\]'
# Example (rapportd):
#   -[RPCompanionLinkDaemon listener:shouldAcceptNewConnection:]
#   -[RPDaemon listener:shouldAcceptNewConnection:]
#   -[RPPairingDaemon listener:shouldAcceptNewConnection:]
#   ... one per gated endpoint ...
```

For classes with `_OBJC_CLASS_$_<Class>` appearing as **undefined symbol**
(`nm -a <daemon> | grep " U _OBJC_CLASS_"`), the class is defined in a
private framework — the daemon imports it at runtime from the shared
cache. Those are the classes this skill enumerates.

### Step 2 — dlopen the shared-cache-only framework(s)

Even though the on-disk binary is missing, `dlopen` on the canonical path
still resolves through the shared cache. This works on macOS 11+.

```c
#include <dlfcn.h>

void *h = dlopen(
    "/System/Library/PrivateFrameworks/CoreUtils.framework/CoreUtils",
    RTLD_NOW);
// h is non-NULL; all Obj-C classes in CoreUtils are now registered
// with the Obj-C runtime and reachable via objc_getClass().
```

Do this for every private framework the daemon imports server-side
classes from. Common combos:

| Daemon       | dlopen this                                                                         |
|--------------|-------------------------------------------------------------------------------------|
| rapportd     | CoreUtils, CoreUtilsSwift, Rapport                                                  |
| sharingd     | CoreUtils, Sharing, SharingXPCHelper                                                |
| nearbyd      | CoreUtils, NearField, ProximityServices                                             |
| homed        | CoreUtils, HomeKitDaemon, HAP                                                       |
| coreduetd    | CoreUtils, CoreDuet, CoreDuetDaemonProtocol                                         |
| bluetoothd   | CoreUtils, CoreBluetooth (daemon side classes), bluetoothd-private                  |
| findmydeviced| CoreUtils, FindMyServices, FMServicesInternal                                       |

### Step 3 — Reflect classes and protocols at runtime

```objc
#import <objc/runtime.h>

// --- CLASS method enumeration ---
Class cls = objc_getClass("CUPairingDaemon");
unsigned n = 0;
Method *m = class_copyMethodList(cls, &n);
for (unsigned i = 0; i < n; i++) {
    printf("  - [%s %s]   %s\n",
           class_getName(cls),
           sel_getName(method_getName(m[i])),
           method_getTypeEncoding(m[i]));
}
free(m);

// --- Adopted-protocol list ---
Protocol * __unsafe_unretained *p = class_copyProtocolList(cls, &n);
for (unsigned i = 0; i < n; i++)
    printf("    <%s>\n", protocol_getName(p[i]));
free((void *)p);

// --- PROTOCOL method-description enumeration (the NSXPC interface!) ---
Protocol *iface = objc_getProtocol("CUPairingDaemonXPCInterface");
struct objc_method_description *md =
    protocol_copyMethodDescriptionList(iface,
                                       YES,  // isRequiredMethod
                                       YES,  // isInstanceMethod
                                       &n);
for (unsigned i = 0; i < n; i++)
    printf("  - %s   %s\n", sel_getName(md[i].name), md[i].types);
free(md);
```

**Swift-bridged classes** use the mangled C name. Format:
`_TtC<module-len><module><class-len><class>`. Example:
`_TtC7Rapport27RPPairingReceiverController` means "class
`RPPairingReceiverController` in module `Rapport`". `objc_getClass` takes
the mangled name directly. Swift protocols bridged to ObjC are named
`<module>.<protocol>` (e.g. `Rapport.RPPairingDaemonXPCInterface`).

**Discovering names you don't know** — use `objc_copyClassList()` and
`objc_copyProtocolList()` and filter by substring (`airing`, `PAKE`,
`XPCServer`, `XPCDaemon`, etc.).

Selector type encodings follow the ObjC runtime grammar:

- `v` void, `@` object, `B` BOOL, `i` int32, `q` int64, `Q` uint64
- `^@` object pointer-out, `^i` int pointer-out
- `@?` block
- Everything after the return type is frame size and each arg's type
  prefixed by stack offset (ignore offsets when reading signatures).

So `v32@0:8Q16@?24` = `-(void)XXX:(uint64)Q withCompletion:(^)`.

### Step 4 — Classify each mach endpoint with a two-pass NSXPC fingerprint

Single-pass probes are ambiguous: "connection invalidated" could mean
listener rejection **or** schema rejection. Solve this with a two-pass
probe per service.

**Pass A — locally-handled selector (no wire message):**

```swift
let conn = NSXPCConnection(machServiceName: name, options: [])
conn.remoteObjectInterface = NSXPCInterface(with: NSObjectProtocol.self)
conn.invalidationHandler = { /* record: invalidated_on_connect = true */ }
conn.resume()
let proxy = conn.remoteObjectProxyWithErrorHandler { _ in }
// .description is handled by NSXPCConnection locally — no bytes cross
// the mach boundary.
_ = (proxy as? NSObjectProtocol)?.description
// Wait ~800ms for invalidation to fire.
```

If invalidation fires in this pass, the listener actively rejected us
at `-listener:shouldAcceptNewConnection:` time. That is an
**entitlement-gated** endpoint.

**Pass B — unknown-selector wire message:**

```swift
@objc protocol MyUnknownProto: NSObjectProtocol {
    func rpProbePleaseIgnore(_ d: Data, reply: @escaping (Bool, Error?) -> Void)
}
// (Same NSXPCConnection setup, but with MyUnknownProto.)
proxy.rpProbePleaseIgnore(Data()) { _, err in /* record err */ }
```

Result decoding:

| Behaviour                                               | Classification                                       |
|---------------------------------------------------------|------------------------------------------------------|
| Pass A invalidates < 100 ms                             | **Listener-gated** (entitlement check fires early)   |
| Pass A completes, Pass B `proxyErr = "Couldn't communicate with a helper application"` | **Open listener, schema-validated** (any caller can connect; unknown methods rejected) |
| Pass A completes, Pass B times out (no reply, no error) | **Silent drop** (listener accepts but ignores unknown methods) |
| Pass A completes, Pass B immediate interruption        | **Listener crashed on our message** — a potential finding |
| Either pass errors "no such service" / Code 4099        | Service not registered / inactive                    |

The NSXPC error text is identical across many failure modes — hence the
need for both passes to disambiguate.

### Step 5 — Record entitlement gate details

When Pass A flags a listener-gated endpoint and you need the exact
entitlement string the gate checks:

```bash
# Find call sites of SecTaskCopyValueForEntitlement in the daemon:
strings -a /usr/libexec/<daemon> | grep -E '^[a-z][-.a-z0-9]*\.[a-z]+'
nm -a /usr/libexec/<daemon> | grep -i SecTaskCopy
# Then read the daemon's own entitlements — the ones it CONSUMES
# (via RPNWUtils-style checkPid:hasEntitlement:) will be referenced
# as CFStringRef constants near the check.
codesign -d --entitlements - /usr/libexec/<daemon>
```

Common gating entitlements on rapportd-family daemons:

- `com.apple.rapport.Client`
- `com.apple.PairingManager.Read` / `.Write` / `.HomeKit`
- `com.apple.sharing.Client`
- `com.apple.nearbyd.xpc`

## Verification

After applying this skill you should have:

- A table: mach-service → listener class → gated? → entitlement.
- A list of NSXPC protocol method signatures per gated service.
- A small reproducible probe binary (~200 LoC Objective-C + ~100 LoC
  Swift) that reruns the whole enumeration in < 1 second.

Sanity checks:

- Method counts from `class_copyMethodList` should match
  `strings -a <daemon> | grep -cE "^-\[<Class> "` plus imported
  framework contributions.
- Selector names from Obj-C runtime should appear as C-strings in the
  relevant private framework when dumped via
  `dyld_info -section __TEXT __objc_methname`.
- The two-pass classifier should agree with `log show --info --debug`
  entries from the target daemon (look for
  `### %#{pid} missing entitlement '%@'` at the target PID around your
  probe timestamp — only visible at debug log level, but a strong
  confirmation when it fires).

## Example — rapportd (macOS 26.4.1, A18 Pro)

```
$ /tmp/reflect_cupairingdaemon
[OK] dlopen /System/Library/PrivateFrameworks/CoreUtils.framework/CoreUtils
[OK] dlopen /System/Library/PrivateFrameworks/CoreUtilsSwift.framework/CoreUtilsSwift
[OK] dlopen /System/Library/PrivateFrameworks/Rapport.framework/Rapport

=== CLASS CUPairingDaemon  (super=NSObject)
  -- 44 instance methods --
    ...
    - [CUPairingDaemon listener:shouldAcceptNewConnection:]   B32@0:8@16@24
    - [CUPairingDaemon testListenerEndpoint]                  @16@0:8
    - [CUPairingDaemon setTestMode:]                          v20@0:8B16
  -- 1 class methods --
    + [CUPairingDaemon sharedPairingDaemon]                   @16@0:8
  -- 1 protocols --
    <NSXPCListenerDelegate>

=== PROTOCOL CUPairingDaemonXPCInterface
  -- 8 required instance methods --
    - getPairingIdentityWithOptions:completion:   v32@0:8Q16@?24
    - savePairedPeer:options:completion:          v40@0:8@16Q24@?32
    - removePairedPeer:options:completion:        v40@0:8@16Q24@?32
    - deletePairingIdentityWithOptions:completion: v32@0:8Q16@?24
    ...
```

Paired with the two-pass probe:

```
=== com.apple.rapport.RPPairing        LISTENER-GATED  (elapsedMs=5)
=== com.apple.PairingManager           open listener, schema-validated
=== com.apple.CompanionLink            open listener, schema-validated
=== com.apple.rapport.remote-text-input  silent drop (inactive)
```

Time cost: under 1 minute for the full 11-service daemon, vs. hours to
extract CoreUtils from the dyld shared cache and `class-dump` it.

## Notes

- `dlopen` succeeds even on SIP-protected shared-cache paths without any
  entitlements. The path must be canonical (symlinks resolved).
- This reflection enumerates what the server **accepts**, not how clients
  actually call it. For a working client that survives the
  NSXPCInterface allowlist check, use
  `apple-vuln-research-private-framework-xpc-probing` — that skill's
  "use the wrapper class" pattern is the complement to this skill's
  "know what the wrapper calls".
- For a static/offline equivalent that does not require the daemon to
  be running and the frameworks to be load-able (e.g. when researching
  a locked IPSW's iOS rapportd), use `macos-dyld-shared-cache-analysis`
  and `dyld_info -section __TEXT __objc_methname`.
  That path cannot easily recover NSXPC protocol method-description
  lists — it only gives you selector strings — which is why this
  live-runtime reflection approach is preferred when the target is the
  running system.
- **Swift distributed actors** (`prePairingActorSystem`,
  `RPPairingDistributedActor`) are **not** dumped by
  `protocol_copyMethodDescriptionList` — Swift's distributed-actor
  system uses a custom codec not bridged to the Obj-C protocol runtime.
  You get the hosting Obj-C wrapper protocol (e.g. 2 methods on
  `Rapport.RPPairingDaemonXPCInterface`) but the actor-dispatch method
  catalog requires separate reversing of the `ActorSystem.remoteCall`
  implementation.
- The probe process's own entitlements are what rapportd sees via
  `SecTaskCopyValueForEntitlement`. If the probe is codesigned with
  `--force --sign - --entitlements <plist>` you can test intermediate
  entitlement levels — but note that Apple-private entitlements
  (`com.apple.rapport.Client`, `com.apple.PairingManager.*`) require
  Apple-issued provisioning profiles, which you will not have on a
  personal-development machine. They only take effect with a
  platform-binary flag or a privileged provisioning profile on the
  target host.
- For Swift classes hosted in a framework module, the Obj-C class-name
  mangling is `_TtC<Nm><Mod><Nc><Class>`. Practical tip: use
  `objc_copyClassList` and substring-match to discover what's loaded,
  rather than guessing mangled names.

## See Also

- `apple-vuln-research-private-framework-xpc-probing` — once you know
  what methods exist, this skill shows how to successfully call them
  as a client (framework wrapper pattern, Code 4097 bypass).
- `macos-dyld-shared-cache-analysis` — `dyld_info` for fully-static,
  offline analysis when the target is an IPSW / AOT cache, not a
  running daemon.
- `apple-vuln-research-peer-to-peer-daemon-audit` — complementary
  pre-trust recon workflow that pairs well with NSXPC-listener
  enumeration for daemons that advertise Bonjour services.
- `apple-vuln-research-iokit-struct-re-via-objc-encoding` — same ObjC
  type-encoding grammar (`@24@0:8@16` etc.) used to decode method
  signatures here.
