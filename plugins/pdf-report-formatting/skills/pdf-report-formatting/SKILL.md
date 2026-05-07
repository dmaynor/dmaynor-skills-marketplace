---
name: pdf-report-formatting
description: Produce branded, professionally formatted PDF reports with cover page, table of contents, running header, page-N-of-M footer, consistent typography, modern tables, callouts, and ordered/unordered lists. Use whenever the user asks for a PDF report, briefing, white paper, audit deliverable, technical memo, or wants existing markdown/text/HTML content turned into a polished PDF — even if they don't explicitly say "PDF formatting". Also use when the user asks to convert a long structured response into a PDF, or mentions ".pdf" output for any document longer than one page. Prefer this skill over generic PDF tools when output style/branding matters.
---

# PDF Report Formatting

Produce consistent, professional PDF reports. Styling lives in `scripts/build_pdf.py`; per-invocation work is content, not layout.

## When to use

Branded reports, audit deliverables, technical memos, briefings, white papers, structured analyses converted to PDF. For raw PDF manipulation (merge, split, extract, OCR), use the generic `pdf` skill instead.

## Workflow

1. Decide the document shape: title, subtitle, optional cover metadata, ordered list of `Section` objects, each with typed `Block` children.
2. Read `scripts/build_pdf.py` once to confirm the API (or rely on the example below).
3. Construct the data structures in a small driver script that imports `build_report` from `scripts/build_pdf.py`.
4. Run it. The builder runs a two-pass `multiBuild` to resolve TOC + page count.
5. Verify visually: cover page renders, TOC page numbers match, no orphaned headings, no Unicode boxes.

The styling lives in the builder. Resist the urge to inline custom `Paragraph` styles or bespoke `TableStyle` per call — extend the builder if a new pattern is genuinely reusable.

## Tooling

`reportlab` Platypus is the default. Two-pass `multiBuild` for TOC + page-N-of-M. Install with `pip install reportlab --break-system-packages`.

## What the builder produces by default

| Element | Default | Override parameter |
|---------|---------|--------------------|
| Cover page | Vertically centered title + subtitle + metadata, no header/footer | `cover_page=False` |
| Table of contents | Auto-generated from H1/H2 headings, on page 2 | `table_of_contents=False` |
| Running header | Document title at top of every body page, with thin underline rule | `show_header=False` |
| Footer | "Page N of M" centered | always on |
| Section numbering | "1.", "2.", ... auto-prefixed to section titles | `numbered_sections=False` |
| Section packing | Two rules combine into one threshold per section: (a) if the previous section consumed more than half a page, the next section starts on a fresh page; (b) if the next section's natural height exceeds the remaining space, it starts on a fresh page. Threshold is `min(body_height, max(half_body, predicted_next_height))`. Each upcoming section's height is pre-measured via `flowable.wrap()` to compute the threshold. | `pack_sections=False` |

## Page geometry

- Page size: `letter` (US). Pass `page_size=A4` for non-US audiences.
- Margins: 0.6 inch on all sides.
- Header band: 0.3 inch above the body frame on body pages.
- Footer: 0.35 inch from bottom.

## Typography contract

| Element | Font | Size / Leading | Color |
|---------|------|----------------|-------|
| Cover title | Helvetica-Bold | 22 / 26 (centered) | `#1a1a1a` |
| Cover subtitle | Helvetica-Bold | 14 / 18 (centered) | `#333333` |
| H1 (section) | Helvetica-Bold | 15 / 19 | `#1a1a1a` |
| H2 (subsection) | Helvetica-Bold | 11.5 / 15 | `#333333` |
| Body | Helvetica | 10 / 14 | black |
| Body small (table cells) | Helvetica | 9 / 12 | black |
| TOC level-1 | Helvetica | 10.5 / 15 | black |
| TOC level-2 | Helvetica | 9.5 / 13 | `#333333` |
| Header / footer | Helvetica | 8 / 8.5 | `#555555` |

Stick with Helvetica/Times/Courier built-ins unless you embed TTFs via `pdfmetrics.registerFont(TTFont(...))`. Embedded fonts add ~200 KB per face and have licensing implications.

## Tables

Modern style: horizontal rules only, no vertical grid lines. Header row gets a tinted fill (`#f5f5f5`), bold text, and 1pt rules above/below; body rows get 0.25pt separators. `repeatRows=1` so the header reappears across page breaks.

Cells are auto-wrapped in `Paragraph` so they word-wrap inside their column. Pass `col_widths` to lock dimensions for important tables.

For row emphasis (e.g., a recommended option in a decision matrix), use the `emphasized_rows` parameter — this triggers both bold text and a tinted background, applied as table style rather than markup so the data stays clean.

```python
TableBlock(
    header=["Option", "F", "A", "I", "Total", "Notes"],
    rows=[
        ["A. Do nothing", "5", "1", "1", "7", "Cheap, brittle."],
        ["B + D parallel", "4", "5", "4", "13–14", "Recommended."],
    ],
    col_widths=[1.6*inch, 0.4*inch, 0.4*inch, 0.5*inch, 0.7*inch, 3.3*inch],
    emphasized_rows=[1],  # second row (0-based, body rows only)
)
```

## Building blocks

| Type | Renders as |
|------|-----------|
| `HeadingBlock(text, level=1\|2, toc=True)` | H1 or H2 paragraph; level-1 emits a TOC entry |
| `ParaBlock(text)` | Body paragraph (HTML markup allowed) |
| `BulletsBlock(items)` | Unordered list with proper bullets and hanging indent |
| `OrderedListBlock(items, start=1)` | Numbered list with hanging indent |
| `TableBlock(header, rows, col_widths=None, emphasized_rows=())` | Modern horizontal-rule table |
| `CalloutBlock(text, kind="note"\|"warn", keep_with_previous=False)` | Tinted box with bold prefix |
| `PageBreakBlock()` | Forces a page break (between sections — see below) |

## Section semantics

A `Section(title, blocks, starts_on_new_page=False)` is the top-level container. The builder auto-renders the title (with optional numbering) and applies `KeepTogether` to the title + first block to prevent orphaned headings.

**Two driver mistakes the builder will refuse:**

1. `PageBreakBlock` as the first child of a section — caused the v2 PDF's empty page 4. Use `Section(starts_on_new_page=True)` instead.
2. An `H1 HeadingBlock` whose text matches the section title — caused the v2 PDF's duplicate "5. MPCoA / MDCoA Table". Section titles render automatically; remove the redundant heading.

Both raise `ValueError` with a clear message at build time.

## Callouts and `keep_with_previous`

Callouts that qualify a preceding table or paragraph should set `keep_with_previous=True`. The builder wraps the callout and its anchor in `KeepTogether`, preventing the callout from floating to the next page alone (the v2 PDF's page-3 orphan). Without this hint, callouts can break across page boundaries.

## Gotchas (read before generating)

1. **HTML escaping**: any user content with `&`, `<`, `>` flowing into `Paragraph` must be escaped — `from xml.sax.saxutils import escape; escape(s)`. Reportlab raises a parse error or silently drops content otherwise.
2. **Em/en dashes**: prefer `&mdash;` and `&ndash;` entities inside `Paragraph` markup.
3. **Long table rows**: a single row taller than a page raises `LayoutError`. Break the row content.
4. **Image scaling**: `Image(path, width=w, height=h)` does not preserve aspect ratio — compute one dimension from the other.
5. **Metadata leakage**: `title=` and `author=` embed in the file. For sensitive content, set explicitly.
6. **No browser storage / no external resources**: embed everything; PDFs render offline.
7. **Two-pass build is slow** for very large docs — ~2x baseline. Disable TOC if you don't need it.

## Security notes

- Treat any user-supplied string flowing into `Paragraph` HTML as untrusted. Escape it.
- If the input is markdown, run it through a markdown→reportlab converter or a sanitizer before passing as Paragraph markup.
- If embedding fonts from `assets/`, verify the font license permits PDF embedding.
- Vanilla reportlab output is **not** PDF/A or PDF/UA compliant. For legal/government/accessibility deliverables, post-process with `veraPDF` + a converter; document this gap to the user.

## Verification (run after every build)

1. Confirm `pypdf.PdfReader(path).pages` yields the expected page count.
2. `pdftotext` the file and confirm no `□` (white square) or `�` (replacement) characters.
3. Confirm the TOC page numbers match actual section locations.
4. For multi-page tables, confirm the header row repeats on continuation pages.
5. Render page 1 to PNG and confirm the cover layout looks right (title centered, no orphaned content).

## References

- `scripts/build_pdf.py` — the canonical builder.
- `references/style_guide.md` — palette rationale, additional patterns, error catalogue.

## Example driver

```python
from scripts.build_pdf import (
    build_report, Section, HeadingBlock, ParaBlock,
    BulletsBlock, OrderedListBlock, TableBlock, CalloutBlock,
)
from reportlab.lib.units import inch

build_report(
    output_path="/abs/path/out.pdf",
    title="Quarterly Risk Review",
    subtitle="Q1 2026",
    metadata={"Author": "Risk Office", "Classification": "Internal", "Date": "2026-05-07"},
    sections=[
        Section(title="Executive Summary", blocks=[
            ParaBlock("Three open issues, two trending green, one trending red."),
            CalloutBlock(
                "Issue R-12 requires steering-committee decision by 2026-05-30.",
                kind="warn",
                keep_with_previous=True,
            ),
        ]),
        Section(title="Findings", starts_on_new_page=True, blocks=[
            TableBlock(
                header=["ID", "Severity", "Status"],
                rows=[
                    ["R-10", "High", "Mitigated"],
                    ["R-11", "Medium", "In progress"],
                    ["R-12", "Critical", "Open"],
                ],
                emphasized_rows=[2],
            ),
        ]),
        Section(title="Recommendations", blocks=[
            OrderedListBlock([
                "Resolve R-12 before 2026-05-30.",
                "Schedule re-test for R-11 on next sprint boundary.",
                "Close R-10 in the risk register.",
            ]),
        ]),
    ],
)
```
