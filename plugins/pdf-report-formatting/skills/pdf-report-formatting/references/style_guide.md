# Style Guide

Loaded only when the caller needs more than the SKILL.md summary — e.g.,
extending the builder with new blocks, adjusting palette for a sub-brand,
or troubleshooting font/glyph issues.

## Color palette (full)

| Token | Hex | Use |
|------|-----|-----|
| `COLOR_TEXT_PRIMARY` | `#1a1a1a` | Document title, H1 |
| `COLOR_TEXT_SECONDARY` | `#333333` | H2, subtitles |
| `COLOR_TEXT_MUTED` | `#555555` | Metadata line, footer |
| `COLOR_GRID` | `#999999` | Table borders, separators |
| `COLOR_HEADER_BG` | `#e6e6e6` | Table header row |
| `COLOR_CALLOUT_NOTE_BG` | `#f0f4f8` | Note callouts |
| `COLOR_CALLOUT_WARN_BG` | `#fdf3e6` | Warning callouts |
| `COLOR_CALLOUT_BORDER` | `#cccccc` | Callout box border |

Print-safety: all foreground/background pairs meet WCAG AA contrast at
9.5pt. If you change a callout background, re-check contrast against the
9.5pt body color (`#000000`).

## Typography rationale

- **Helvetica family** for headings and body. Trade-offs: ubiquitous in
  PDFs (no embedding required), but lacks a true italic glyph in some
  reportlab builds. If italics matter, embed an open-license alternative
  (e.g., DejaVu Sans).
- **Body 9.5/13** is intentionally smaller than typical web body text.
  Print is read closer to the eye than a screen, and 9.5pt density helps
  technical reports stay under typical email-size limits without becoming
  multi-volume.
- **Table cells at 8.5pt** to fit more columns. Below 8pt, readability
  drops noticeably under typical office printing.

## Adding a new block type

1. Add a `@dataclass` to `scripts/build_pdf.py` and include it in the
   `Block` union.
2. Add an `_render_<name>` helper or extend `_render_block` with another
   `isinstance` branch.
3. Document the block in SKILL.md's "Building blocks" table.
4. Add a representative usage to the example driver in SKILL.md.

Resist adding blocks that are one-off styling. If a CalloutBlock with a
new color is needed twice, extend `kind` instead of inventing
`PrettyBlueBoxBlock`.

## Embedding a custom font

```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont("InterRegular", "assets/Inter-Regular.ttf"))
pdfmetrics.registerFont(TTFont("InterBold", "assets/Inter-Bold.ttf"))
pdfmetrics.registerFontFamily("Inter", normal="InterRegular", bold="InterBold")
```

Then change the style construction in `_build_styles` to use `"Inter"`
instead of the default. File size grows ~200 KB per face; acceptable
for distribution but bloats archive storage.

## Common reportlab errors and what they mean

| Error | Cause | Fix |
|-------|-------|-----|
| `LayoutError: Flowable ... too large on page` | Single row/paragraph taller than the page minus margins | Break the content; reduce font size; widen margins |
| `xml.parsers.expat.ExpatError: not well-formed` | Unescaped `<`/`&` in Paragraph text | Escape via `xml.sax.saxutils.escape()` |
| Boxes (`□`) in output | Using glyphs not in the embedded font | Use `<sub>`/`<super>` instead of Unicode subscripts; embed a font that has the glyph |
| Header repeats but rows don't paginate | Forgot `repeatRows=1` or used a wrapper that breaks repeat | Set `repeatRows=1` on the `Table` directly |
| Image squished | Aspect ratio not preserved | Pre-compute height from width using PIL |

## PDF/A and accessibility

Vanilla reportlab output is not PDF/A or PDF/UA compliant:

- No tagged structure (screen readers can't navigate sections).
- Fonts are subsetted but not always fully embedded.
- No XMP metadata block.

For compliant output, post-process with `veraPDF` (verification) and
`pdfa` library or LibreOffice (conversion). Document this gap in any
deliverable destined for legal, medical, or government use.

## Test fixtures

Useful smoke-test inputs:

1. A doc with one section containing every block type — visual
   regression.
2. A doc with a 50-row table — confirms `repeatRows=1` and paginating
   header.
3. A doc with text containing `< > & — – "smart quotes" H₂O x²` — confirms
   escaping and Unicode handling.
4. A doc with a section title that lands at the bottom of a page —
   confirms `KeepTogether` prevents orphaned headings.
