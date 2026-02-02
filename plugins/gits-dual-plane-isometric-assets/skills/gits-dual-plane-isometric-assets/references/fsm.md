# Dual-Plane State Machines

Global state is product of three concurrent FSMs:
```
GlobalState = PhysicalState × CyberState × CognitiveState
```

---

## Physical Plane FSMs

### HumanBody FSM

```
[Offline] ──power_on──> [Idle]
[Idle] ──move──> [InTransit] ──arrive──> [Idle]
[Idle] ──connect_interface──> [CyberLinked] ──disconnect──> [Idle]

Failure:
[Idle|InTransit] ──injury──> [Degraded] ──fatal──> [Destroyed]
```

**Guards**:
- `connect_interface` requires `cyber_interface_level ≥ threshold`
- `InTransit` blocked if `path.power = 0`

### Building FSM

```
[Powered] ──overload──> [Stressed] ──damage──> [Compromised] ──collapse──> [Destroyed]

Recovery:
[Stressed] ──repair──> [Powered]
[Compromised] ──repair──> [Stressed]
```

**Invariant**: Destroyed building invalidates all hosted NetworkNodes.

---

## Cyber Plane FSMs

### NetworkNode FSM

```
[Offline] ──power_on──> [Online]
[Online] ──compromise──> [Breached] ──isolate──> [Sandboxed] ──restore──> [Online]

Failure:
[Any] ──overload──> [Degraded] ──crash──> [Offline]
```

**Guards**:
- `compromise` probability ∝ `(1 - trust_score)`
- `isolate` adds latency to all resident processes

### DataFlow FSM

```
[Queued] ──transmit──> [InTransit] ──arrive──> [Delivered]

Failure:
[InTransit] ──loss──> [Corrupted] ──retry──> [Queued]
```

---

## Cognitive Plane FSMs

### Ghost FSM (Primary)

```
[Uninstantiated] ──instantiate──> [Stable]
[Stable] ──migrate──> [Migrating] ──arrive──> [Stable]

Fork:
[Stable] ──fork──> [Forking] ──complete──> [Stable + ForkedChild]

Failure:
[Stable] ──attack──> [Destabilized] ──recover──> [Stable]
[Destabilized] ──fragment──> [Fragmented] ──merge──> [Stable]
[Fragmented] ──decay──> [Lost]
```

**State Semantics**:
- `Stable`: coherence ≥ threshold
- `Destabilized`: coherence degrading
- `Fragmented`: identity split across substrates
- `Lost`: unrecoverable identity collapse

### CognitiveProcess FSM

```
[Created] ──schedule──> [Running] ──complete──> [Completed]

Failure:
[Running] ──resource_starve──> [Suspended] ──resume──> [Running]
[Suspended] ──kill──> [Terminated]
```

---

## Cross-Plane Constraints

| Constraint | Rule |
|------------|------|
| C1: Substrate Dependency | `Ghost.Migrating` requires `NetworkNode.Online` OR `HumanBody.CyberLinked` |
| C2: Physical Precedence | `Building.Destroyed` → all `NetworkNode` states = `Offline` |
| C3: Cognitive Conservation | `ForkedGhost.coherence < ParentGhost.coherence` |
| C4: Latency Reality | `MigrationTime ≥ sum(Edge.latency along path)` |

---

## Machine-Readable DSL

```yaml
GhostFSM:
  Stable:
    on:
      fork: Forking
      migrate: Migrating
      attack: Destabilized
  Destabilized:
    on:
      recover: Stable
      fragment: Fragmented
  Fragmented:
    on:
      merge: Stable
      decay: Lost
```
