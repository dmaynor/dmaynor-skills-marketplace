# Event Calculus & Rule Engine

Discrete-time event calculus with explicit guards. All transitions occur at integer ticks.

---

## Core Predicates

```
Happens(Event, t)           # Event occurs at tick t
HoldsAt(Fluent, t)          # State holds at tick t
Initiates(Event, Fluent, t) # Event starts fluent
Terminates(Event, Fluent, t)# Event ends fluent
Blocked(Event, t)           # Event cannot occur
```

---

## Fluents (State Variables)

Fluents map 1:1 to FSM states:

```
Physical:
  BodyState(body, state)
  BuildingState(building, state)

Cyber:
  NodeState(node, state)
  FlowState(flow, state)

Cognitive:
  GhostState(ghost, state)
  ProcessState(proc, state)
```

---

## Events

### Physical Events
- `MoveBody(body, from_tile, to_tile)`
- `DamageBuilding(building, amount)`
- `PowerLoss(tile)`

### Cyber Events
- `PowerOnNode(node)`
- `CompromiseNode(node, attacker)`
- `IsolateNode(node)`
- `Transmit(flow)`

### Cognitive Events
- `InstantiateGhost(ghost, substrate)`
- `MigrateGhost(ghost, from, to)`
- `ForkGhost(parent, child)`
- `AttackGhost(ghost)`
- `MergeGhost(ghosts[])`

---

## Example Rules

### Ghost Migration

```prolog
Initiates(MigrateGhost(G, From, To), GhostState(G, Migrating), t).
Terminates(MigrateGhost(G, From, To), GhostState(G, Stable), t).

% Arrival delayed by latency
Happens(ArriveGhost(G, To), t + PathLatency(From, To)).

Initiates(ArriveGhost(G, To), GhostState(G, Stable), t).
Terminates(ArriveGhost(G, To), GhostState(G, Migrating), t).
```

### Node Compromise

```prolog
Initiates(CompromiseNode(N, A), NodeState(N, Breached), t).
Terminates(CompromiseNode(N, A), NodeState(N, Online), t).
```

---

## Guards & Blocking

### Substrate Guard

```prolog
Blocked(MigrateGhost(G, From, To), t) :-
  not (
    HoldsAt(NodeState(To, Online), t)
    or
    (HoldsAt(BodyState(B, CyberLinked), t) and Hosts(B, G))
  ).
```

### Physical Precedence

```prolog
Happens(PowerLoss(Tile), t) →
  ∀N HostedOn(Tile): Happens(NodeCrash(N), t).

Initiates(NodeCrash(N), NodeState(N, Offline), t).
```

### Transit Vulnerability

```prolog
Happens(IsolateNode(N), t)
∧ HoldsAt(GhostState(G, Migrating), t)
∧ TransitVia(G, N)
→ Happens(AttackGhost(G), t).
```

### Identity Conservation

```prolog
Happens(ForkGhost(P, C), t) → Coherence(C) < Coherence(P).
% Violation blocks event
```

---

## Tick Execution Order

```python
for t in ticks:
    candidates = propose_events(t)
    allowed = [e for e in candidates if not blocked(e, t)]
    for e in allowed:
        apply_terminations(e, t)
        apply_initiations(e, t)
        schedule_delayed(e, t)
```

No recursion. No magic. Deterministic and replayable.
