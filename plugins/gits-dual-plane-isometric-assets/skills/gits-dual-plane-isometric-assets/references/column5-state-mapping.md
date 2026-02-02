# Column 5 State Mapping

Column 5 encodes FSM state or cross-plane interaction. Visual encoding uses **structural variation**, not color dependency.

---

## Physical Plane Assets

### HumanBody
| FSM State | Column 5 Visualization |
|-----------|----------------------|
| Offline | Body with no interface glow, closed posture |
| Idle | Neutral stance, interface ports visible but inactive |
| InTransit | Motion blur suggestion, directional lean |
| CyberLinked | **Active interface cables/ports, data stream suggestion** |
| Degraded | Structural damage indicators, asymmetry |
| Destroyed | Collapsed form, fragmented |

**Primary Column 5 view**: CyberLinked (interface active)

### Building
| FSM State | Column 5 Visualization |
|-----------|----------------------|
| Powered | Internal structure visible, even load distribution |
| Stressed | Visible strain lines, heat distortion |
| Compromised | **Structural cracks, exposed infrastructure** |
| Destroyed | Collapsed, debris field |

**Primary Column 5 view**: Stressed/Compromised (structural stress)

---

## Cyber Plane Assets

### NetworkNode
| FSM State | Column 5 Visualization |
|-----------|----------------------|
| Offline | Dark core, no activity indicators |
| Online | Active routing core, balanced data paths |
| Breached | **Compromised sectors visible, irregular flow patterns** |
| Sandboxed | Isolation barriers visible, restricted paths |
| Degraded | Partial core activity, stuttered patterns |

**Primary Column 5 view**: Breached or Sandboxed (compromise state)

### DataFlow
| FSM State | Column 5 Visualization |
|-----------|----------------------|
| Queued | Packet cluster, stationary |
| InTransit | **Packet stream mid-path, integrity indicators** |
| Delivered | Dispersed pattern at destination |
| Corrupted | Fragmented packets, irregular spacing |

**Primary Column 5 view**: InTransit with integrity visualization

### SecurityControl
| FSM State | Column 5 Visualization |
|-----------|----------------------|
| Inactive | Dormant hardware, no field indicators |
| Active | Field boundaries visible, monitoring state |
| Engaged | **Active interception, barrier visualization** |
| Failed | Broken field, hardware damage |

**Primary Column 5 view**: Engaged state

---

## Cognitive Plane Assets

### Ghost
| FSM State | Column 5 Visualization |
|-----------|----------------------|
| Uninstantiated | Potential form, undefined boundaries |
| Stable | Coherent form, clear boundaries, single anchor |
| Migrating | Stretched form between two points |
| Forking | Splitting form, two emerging shapes |
| Destabilized | **Flickering boundaries, coherence loss visible** |
| Fragmented | Multiple disconnected shards |
| Lost | Dissipating particles, no coherent form |

**Residency sub-states**:
- `body`: Form anchored to humanoid silhouette
- `node`: Form tethered to geometric substrate
- `distributed`: Form with multiple faint tethers

**Primary Column 5 view**: Residency + stability composite

### CognitiveProcess
| FSM State | Column 5 Visualization |
|-----------|----------------------|
| Created | Nascent form, initialization pattern |
| Running | **Active computation visualization, resource flow** |
| Completed | Collapsed/resolved form |
| Suspended | Frozen mid-computation |
| Terminated | Fragmented, terminated pattern |

**Primary Column 5 view**: Running with resource consumption

### MemoryShard
| FSM State | Column 5 Visualization |
|-----------|----------------------|
| Intact | Clean geometric form, high fidelity |
| Decaying | **Edge erosion, fidelity loss visible** |
| Corrupted | Fragmented, irregular geometry |

**Primary Column 5 view**: Decay rate visualization

---

## Visual Encoding Principles

1. **No color dependency** — States must be distinguishable in grayscale
2. **Structural variation** — Form/shape changes encode state, not just hue
3. **Consistent metaphors** — Fragmentation = instability across all entities
4. **Scale preservation** — State changes don't alter entity footprint
