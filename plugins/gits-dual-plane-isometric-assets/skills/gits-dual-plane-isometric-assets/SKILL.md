---
name: gits-dual-plane-isometric-assets
description: >
  Generate isometric sprite sheet images for Ghost-in-the-Shell-inspired dual-plane city simulation.
  Use when creating: physical-plane assets (buildings, bodies, infrastructure), cyber-plane assets
  (network nodes, data flows, security controls), cognitive-plane assets (ghosts, processes, memory shards).
  Triggers on requests for simulation assets, isometric sprite sheets, dual-plane visualizations,
  or GitS-style city simulation graphics. Assets encode FSM states mechanically, not decoratively.
---

# Dual-Plane Isometric Asset Generation

Generate **state-encoding sprite sheets** for city simulation. Every asset maps to ontology entities and FSM states.

## Workflow

1. Identify entity class from user request
2. Run `scripts/generate_prompt.py <entity_class>` to produce canonical prompt
3. Invoke image generation with the prompt
4. Run `scripts/validate_asset_sheet.py <output_path>` to verify compliance
5. Save validated asset to `plane_entitytype_variant_states.png`

## Entity Classes

| Plane | Entities |
|-------|----------|
| Physical | `HumanBody`, `Building` |
| Cyber | `NetworkNode`, `DataFlow`, `SecurityControl` |
| Cognitive | `Ghost`, `CognitiveProcess`, `MemoryShard` |

## Sheet Format (Non-Negotiable)

- **Size**: 2048×2048 pixels, square
- **Background**: Solid `#FF0000`
- **Grid**: 6 rows × 5 columns
- **Columns 1-4**: Isometric views (NW, NE, SE, SW)
- **Column 5**: State/diagnostic view (see `references/column5-state-mapping.md`)
- **Style**: Hyper-realistic, industrial, no shadows, no text

## Scripts

### generate_prompt.py

```bash
python scripts/generate_prompt.py NetworkNode
python scripts/generate_prompt.py Ghost --variant destabilized
python scripts/generate_prompt.py Building --rows "residential,residential,commercial,commercial,industrial,industrial"
```

### validate_asset_sheet.py

```bash
python scripts/validate_asset_sheet.py output.png
python scripts/validate_asset_sheet.py output.png --strict --verbose
```

Requires: `pip install pillow numpy --break-system-packages`

## References

| File | Content |
|------|---------|
| `references/ontology.md` | Entity definitions, properties, constraints |
| `references/fsm.md` | State machines for all entity types |
| `references/event-calculus.md` | Transition rules, guards, tick execution |
| `references/grid-spec.md` | Pixel-level layout specification |
| `references/column5-state-mapping.md` | FSM state → visual encoding |

## Rejection Criteria

Regenerate if any:
- Shadows present
- Inconsistent scale across rows
- Neon/fantasy aesthetics
- Text or UI labels
- Perspective drift between cells
- Background not #FF0000
- Dimensions not 2048×2048
