# Dual-Plane City Ontology

## Planes

```
Plane
 ├─ PhysicalPlane
 ├─ CyberPlane
 └─ CognitivePlane
```

Every entity exists in at least one plane. Cross-plane effects must be explicitly causal.

---

## Spatial Substrate

### Tile
```yaml
Tile:
  id: string
  coordinates: {x: int, y: int, z: int}
  physical_components: list[Entity]
  cyber_components: list[Entity]
  jurisdiction: string
```

### Edge
```yaml
Edge:
  source_tile: Tile
  target_tile: Tile
  medium: [fiber, copper, wireless, optical, airgap]
  latency: float
  bandwidth: float
  loss_rate: float
  surveillance_probability: float
```

---

## PhysicalPlane Entities

### Building
```yaml
Building:
  structural_integrity: float  # 0.0–1.0
  power_capacity: int
  heat_budget: float
  occupants: list[HumanBody]
  hosted_nodes: list[NetworkNode]
```

**Failure modes**: Power loss, physical damage, over-occupancy

### HumanBody
```yaml
HumanBody:
  biological_state: float  # 0.0–1.0
  cyber_interface_level: int
  location_tile: Tile
  linked_ghost: Ghost | null
```

---

## CyberPlane Entities

### NetworkNode
```yaml
NetworkNode:
  compute_capacity: int
  storage_capacity: int
  bandwidth_cap: int
  trust_score: float  # 0.0–1.0
  owner: string
  resident_processes: list[CognitiveProcess]
```

### DataFlow
```yaml
DataFlow:
  source_node: NetworkNode
  destination_node: NetworkNode
  size: int
  sensitivity: int
  encryption_level: int
  integrity: float  # 0.0–1.0
```

### SecurityControl
```yaml
SecurityControl:
  type: [firewall, ids, sandbox, airgap]
  effectiveness: float
  latency_cost: float
  failure_probability: float
```

---

## CognitivePlane Entities

### Ghost
```yaml
Ghost:
  ghost_id: string
  coherence_level: float  # 0.0–1.0, identity stability
  memory_integrity: float
  agency_level: int
  residency: [body, node, distributed]
  permissions: list[string]
  fork_lineage: list[Ghost]
```

**Failure modes**: Drift (coherence loss), fragmentation, hostile overwrite, silent corruption

### CognitiveProcess
```yaml
CognitiveProcess:
  owning_ghost: Ghost
  task_type: string
  compute_demand: int
  autonomy: int
  risk_profile: float
```

### MemoryShard
```yaml
MemoryShard:
  content_hash: string
  fidelity: float
  encryption: int
  storage_node: NetworkNode
  decay_rate: float
```

---

## Cross-Plane Relationships

```
HumanBody ──hosts──> Ghost
Ghost ──resides_on──> NetworkNode
NetworkNode ──located_at──> Tile
Tile ──powered_by──> PhysicalInfrastructure
```

**Invariant**: No Ghost can execute without either a Body or a Node.

---

## Global Constraints

1. **Energy Conservation**: `total_compute ≤ total_power × efficiency`
2. **Identity Conservation**: `forked_ghost.coherence ≤ parent.coherence`
3. **Latency Reality**: `cyber_action_time ≥ physical_path_latency`
4. **Jurisdictional Boundaries**: `action_legality = tile.jurisdiction ∩ ghost.permissions`
