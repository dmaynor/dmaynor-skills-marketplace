---
name: gits-dual-plane-isometric-assets
description: >
  Generate isometric sprite sheet images for Ghost-in-the-Shell-inspired dual-plane city simulation.
  Use when creating: physical-plane assets (buildings, bodies, infrastructure), cyber-plane assets
  (network nodes, data flows, security controls), cognitive-plane assets (ghosts, processes, memory shards).
  Triggers on requests for simulation assets, isometric sprite sheets, dual-plane visualizations,
  or GitS-style city simulation graphics. Assets encode FSM states mechanically, not decoratively.
author: dmaynor
version: 1.0.0
date: 2026-03-29
---

# Dual-Plane Isometric Asset Generation

## Problem

City simulations with dual-plane (physical/cyber) or triple-plane (physical/cyber/cognitive) layers need large volumes of isometric sprite sheets where each frame encodes a specific FSM state. Manually creating these assets is slow and inconsistent. Hand-prompted image generation produces sheets with wrong dimensions, perspective drift between cells, and states that don't match the simulation ontology. This skill standardizes the pipeline: prompt generation, image creation, and validation — ensuring every sheet is mechanically correct and simulation-ready.

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

## Without Scripts (Manual Fallback)

If `generate_prompt.py` or `validate_asset_sheet.py` are unavailable, use this manual process:

### Manual Prompt Construction

Build the image generation prompt using this template:

```
Isometric sprite sheet, 2048x2048 pixels, solid #FF0000 background, 6 rows by 5 columns grid.
Each row is one FSM state of a [ENTITY_CLASS] ([PLANE] plane).
Columns 1-4: isometric views from NW, NE, SE, SW angles. Column 5: [STATE_DIAGNOSTIC_VIEW].
Style: hyper-realistic, industrial, Ghost in the Shell aesthetic. No shadows, no text, no labels.
Rows top to bottom: [STATE_1], [STATE_2], [STATE_3], [STATE_4], [STATE_5], [STATE_6].
Consistent scale across all rows. No neon or fantasy colors.
```

Fill in bracketed values from `references/ontology.md` and `references/fsm.md`. For example, a `NetworkNode` would use rows: idle, active, overloaded, compromised, patching, offline.

### Manual Validation

Without the validation script, check these by hand:

1. Open the image and confirm dimensions are exactly 2048x2048 (use any image editor or `identify output.png` with ImageMagick)
2. Sample the background color at the corners and between cells — must be `#FF0000` (use color picker)
3. Visually confirm 6 rows and 5 columns with consistent cell sizes (~409x341 per cell)
4. Check that column 5 differs visually from columns 1-4 (state/diagnostic encoding, not another rotation)
5. Verify each row depicts a distinct FSM state with visible differences between them

## Rejection Criteria

Regenerate if any:
- Shadows present
- Inconsistent scale across rows
- Neon/fantasy aesthetics
- Text or UI labels
- Perspective drift between cells
- Background not #FF0000
- Dimensions not 2048x2048

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| **Wrong aspect ratio** | Image generator ignored the 2048x2048 constraint | Add "exactly 2048x2048 pixels, 1:1 aspect ratio, square image" to the prompt. Some generators need the aspect ratio stated explicitly. |
| **Color bleed into background** | Anti-aliasing or soft edges blending with #FF0000 | Add "hard edges, no anti-aliasing on sprite boundaries, crisp pixel borders" to the prompt. The red background is a chroma key — bleed makes extraction impossible. |
| **Missing frames (empty cells)** | Generator collapsed multiple states into fewer rows | Explicitly number the rows in the prompt: "Row 1: idle state. Row 2: active state..." Generators handle numbered lists more reliably than comma-separated lists. |
| **Inconsistent perspective** | NW/NE/SE/SW angles drift between rows | Add "camera angle is fixed for all 30 cells, only the object rotates and changes state." Regenerate the full sheet rather than patching individual cells. |
| **States look identical** | FSM states lack visual distinction | Make state differences more explicit in the prompt: describe specific visual markers (e.g., "compromised state has visible red fracture lines on the housing" rather than just "compromised"). |
| **Fantasy/neon aesthetic** | Generator defaults to stylized look | Prepend "photorealistic industrial render, matte materials, desaturated palette, no glow effects, no neon" and remove any words like "cyber" or "futuristic" that trigger stylization. |
| **Validation script fails with import error** | Missing pillow or numpy | Run `pip install pillow numpy --break-system-packages` or use the manual validation steps above. |

## Verification

After generating and validating a sheet, confirm:

- [ ] Dimensions are exactly 2048x2048 pixels
- [ ] Background is solid #FF0000 with no color bleed at sprite edges
- [ ] Grid is 6 rows by 5 columns with consistent cell sizes
- [ ] Columns 1-4 show NW, NE, SE, SW isometric rotations (verify by checking object orientation flips correctly)
- [ ] Column 5 shows state/diagnostic encoding distinct from the rotation views
- [ ] All 6 rows depict visually distinguishable FSM states
- [ ] No shadows, text, labels, or neon/fantasy styling present
- [ ] Scale is consistent across all rows (same entity should be the same size in every cell)
- [ ] File is saved with correct naming convention: `plane_entitytype_variant_states.png`
