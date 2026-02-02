# Asset Sheet Grid Specification

## Dimensions (Non-Negotiable)

| Property | Value |
|----------|-------|
| Size | 2048×2048 pixels (square) |
| Background | Solid `#FF0000` (exact) |
| Grid | 6 rows × 5 columns (30 cells) |
| Cell size | ~341×341 pixels |

---

## Grid Layout

Each **row = one logical entity** (same ontology object, different views/states).

| Column | View |
|--------|------|
| 1 | Isometric **North-West** |
| 2 | Isometric **North-East** |
| 3 | Isometric **South-East** |
| 4 | Isometric **South-West** |
| 5 | **State / Diagnostic View** |

---

## Projection Requirements

- True isometric projection (consistent angle across all cells)
- Flat, neutral lighting
- **NO SHADOWS**
- Centered in each cell
- Consistent scale across all rows

---

## Style Requirements

- Hyper-realistic, restrained, industrial
- No neon fantasy aesthetics
- No text, labels, or UI elements
- No holographic overlays
- No visible people (except HumanBody assets)

---

## Cell Boundaries

```
Row 0: pixels 0-340
Row 1: pixels 341-681
Row 2: pixels 682-1022
Row 3: pixels 1023-1363
Row 4: pixels 1364-1704
Row 5: pixels 1705-2047

Col 0: pixels 0-408
Col 1: pixels 409-817
Col 2: pixels 818-1226
Col 3: pixels 1227-1635
Col 4: pixels 1636-2047
```

Note: Slight variance acceptable due to rounding; validation uses ±5px tolerance.
