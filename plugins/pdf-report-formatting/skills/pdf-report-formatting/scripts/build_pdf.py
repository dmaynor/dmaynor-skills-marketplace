"""Reusable PDF report builder with pluggable themes.

Encodes the house style for branded PDF reports. Callers populate typed
data structures (Section, *Block) and call build_report; styling is owned
here, not at the call site.

Themes
------
A Theme bundles every visual parameter the builder uses: page background,
text colors, accent colors, table styling, callout tints, heading
behavior, and optional decorations (corner brackets, footer divider).

Two presets ship with the skill:

    LIGHT  - default; black-on-white with light gray rules and tints.
             Suitable for print-first deliverables.
    CYBER  - dark navy background with cyan + magenta dual-accent,
             ALL-CAPS section headings, L-shaped tactical corner
             brackets. Suitable for screen-first technical briefings,
             security analyses, "tactical" or "terminal" aesthetic.

Pass theme="cyber" (or any registered name) or theme=Theme(...) to
build_report. Defaults to "light".

Security
--------
Strings passed into ParaBlock, HeadingBlock, OrderedListBlock,
BulletsBlock, or TableBlock cells flow through reportlab's Paragraph
parser, which interprets HTML markup. Untrusted input must be escaped
via xml.sax.saxutils.escape() before reaching these blocks. The builder
does NOT escape automatically because callers legitimately use markup
like <b>, <sub>, <super>.

Two-pass build
--------------
The document is built with multiBuild() to resolve the table of contents
and Page N of M counters. Side effects in your driver should be
idempotent.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal, Sequence

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Theme:
    """Visual theme for PDF reports.

    All color fields are hex strings (#RRGGBB). The builder converts them
    to reportlab Color objects internally — keep the hex form so themes
    can be serialized / diffed easily.

    Frozen so themes can be shared and reused without accidental mutation.
    """

    name: str

    # Page surface
    background: str = "#FFFFFF"

    # Body text
    text_primary: str = "#1a1a1a"
    text_secondary: str = "#333333"
    text_muted: str = "#555555"

    # Accents
    accent: str = "#1a1a1a"
    accent_secondary: str = "#555555"

    # Title block on cover or first page
    title_color: str = "#1a1a1a"
    subtitle_color: str = "#333333"

    # Section / subsection headings
    heading_color: str = "#1a1a1a"
    subheading_color: str = "#333333"
    caps_headings: bool = False
    heading_underline: bool = False  # cyan thin rule below H1

    # Metadata block
    metadata_label_color: str = "#555555"
    metadata_value_color: str = "#1a1a1a"

    # Tables
    table_header_bg: str = "#f5f5f5"
    table_header_fg: str = "#1a1a1a"
    table_header_rule: str = "#1a1a1a"
    table_body_rule: str = "#cccccc"
    table_emph_bg: str = "#eef4f9"
    table_cell_fg: str = "#1a1a1a"

    # Callouts
    callout_note_bg: str = "#f0f4f8"
    callout_warn_bg: str = "#fdf3e6"
    callout_border_note: str = "#cccccc"
    callout_border_warn: str = "#cccccc"
    callout_text: str = "#1a1a1a"

    # Page chrome
    header_text_color: str = "#555555"
    header_rule_color: str = "#cccccc"
    header_rule: bool = True
    footer_text_color: str = "#555555"
    footer_rule_color: str = "#cccccc"
    footer_rule: bool = False

    # Decorations
    corner_brackets: bool = False
    corner_bracket_color: str = "#1a1a1a"
    corner_bracket_size_in: float = 0.35
    corner_bracket_width_pt: float = 0.6

    # TOC styling
    toc_heading_color: str = "#1a1a1a"
    toc_level1_color: str = "#1a1a1a"
    toc_level2_color: str = "#333333"

    @property
    def is_dark(self) -> bool:
        """Heuristic: background luminance below 0.5 means dark theme."""
        try:
            r = int(self.background[1:3], 16) / 255.0
            g = int(self.background[3:5], 16) / 255.0
            b = int(self.background[5:7], 16) / 255.0
            return (0.299 * r + 0.587 * g + 0.114 * b) < 0.5
        except (ValueError, IndexError):
            return False


LIGHT_THEME = Theme(name="light")


CYBER_THEME = Theme(
    name="cyber",
    # Surface
    background="#0B0B1A",
    # Text
    text_primary="#E8E8E8",
    text_secondary="#B8C5D6",
    text_muted="#7A8A9E",
    # Accents
    accent="#00D4D4",
    accent_secondary="#CC44CC",
    # Title
    title_color="#00D4D4",
    subtitle_color="#CC44CC",
    # Headings
    heading_color="#00D4D4",
    subheading_color="#00D4D4",
    caps_headings=True,
    heading_underline=True,
    # Metadata
    metadata_label_color="#00D4D4",
    metadata_value_color="#E8E8E8",
    # Tables
    table_header_bg="#0B0B1A",
    table_header_fg="#00D4D4",
    table_header_rule="#00D4D4",
    table_body_rule="#1F2D44",
    table_emph_bg="#162338",
    table_cell_fg="#E0E0E0",
    # Callouts
    callout_note_bg="#0F1F36",
    callout_warn_bg="#2A1815",
    callout_border_note="#00D4D4",
    callout_border_warn="#FF6B35",
    callout_text="#E8E8E8",
    # Header / footer
    header_text_color="#7A8A9E",
    header_rule_color="#00D4D4",
    header_rule=True,
    footer_text_color="#7A8A9E",
    footer_rule_color="#00D4D4",
    footer_rule=True,
    # Decorations
    corner_brackets=True,
    corner_bracket_color="#00D4D4",
    corner_bracket_size_in=0.35,
    corner_bracket_width_pt=0.8,
    # TOC
    toc_heading_color="#00D4D4",
    toc_level1_color="#E8E8E8",
    toc_level2_color="#B8C5D6",
)


THEMES: dict[str, Theme] = {
    "default": LIGHT_THEME,
    "light": LIGHT_THEME,
    "cyber": CYBER_THEME,
}


# ---------------------------------------------------------------------------
# Layout presets — bundle structural choices into named options.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Layout:
    """Structural-element preset for a document.

    Pairs orthogonally with Theme: a Theme controls visual style,
    a Layout controls which structural elements (cover page, TOC,
    section numbering) are present.
    """

    name: str
    cover_page: bool = True
    table_of_contents: bool = True
    numbered_sections: bool = True


# Formal: long-form analytical document with proper navigation.
# Cover page, TOC, numbered sections. The default for analytical
# deliverables, audit reports, white papers.
FORMAL_LAYOUT = Layout(
    name="formal",
    cover_page=True,
    table_of_contents=True,
    numbered_sections=True,
)

# Tactical: briefing-style, get-to-the-point. Inline title at the
# top of page 1, no TOC, no auto-numbered sections — section titles
# read as standalone callouts. Pair with the cyber theme for the
# canonical strix-halo "tactical brief" aesthetic.
TACTICAL_LAYOUT = Layout(
    name="tactical",
    cover_page=False,
    table_of_contents=False,
    numbered_sections=False,
)

# Navigable-Tactical: the strix-halo top-of-page title, but with a
# TOC retained because the document is long enough that readers
# benefit from navigation. Use this for cyber-themed analyses
# longer than ~6 pages where structural scannability still matters.
NAVIGABLE_TACTICAL_LAYOUT = Layout(
    name="navigable_tactical",
    cover_page=False,
    table_of_contents=True,
    numbered_sections=False,
)


LAYOUTS: dict[str, Layout] = {
    "default": FORMAL_LAYOUT,
    "formal": FORMAL_LAYOUT,
    "tactical": TACTICAL_LAYOUT,
    "navigable_tactical": NAVIGABLE_TACTICAL_LAYOUT,
}


def _resolve_layout(layout: Layout | str | None) -> Layout:
    """Accept a Layout instance, a registered name, or None (=formal)."""
    if layout is None:
        return FORMAL_LAYOUT
    if isinstance(layout, Layout):
        return layout
    if isinstance(layout, str):
        try:
            return LAYOUTS[layout.lower()]
        except KeyError:
            known = ", ".join(sorted(LAYOUTS.keys()))
            raise ValueError(
                f"Unknown layout {layout!r}. Known layouts: {known}. "
                f"Pass a Layout instance for a custom preset."
            )
    raise TypeError(f"layout must be Layout, str, or None; got {type(layout).__name__}")


# Sentinel for parameters that the user did not explicitly pass.
# Used so an explicit cover_page=True can override layout="tactical".
_UNSET: object = object()


def _resolve_theme(theme: Theme | str | None) -> Theme:
    """Accept a Theme instance, a registered name, or None (=light)."""
    if theme is None:
        return LIGHT_THEME
    if isinstance(theme, Theme):
        return theme
    if isinstance(theme, str):
        try:
            return THEMES[theme.lower()]
        except KeyError:
            known = ", ".join(sorted(THEMES.keys()))
            raise ValueError(
                f"Unknown theme {theme!r}. Known themes: {known}. "
                f"Pass a Theme instance for a custom palette."
            )
    raise TypeError(f"theme must be Theme, str, or None; got {type(theme).__name__}")


# ---------------------------------------------------------------------------
# TocParagraph
# ---------------------------------------------------------------------------


class TocParagraph(Paragraph):
    """A Paragraph subclass that emits a TOC entry when laid out.

    Plain Paragraphs styled as H1/H2 do NOT emit TOC entries — only
    TocParagraph instances do. This lets HeadingBlock(toc=False) opt out
    cleanly without parallel paragraph styles.
    """

    def __init__(self, text: str, style: ParagraphStyle, toc_level: int):
        super().__init__(text, style)
        self._toc_level = toc_level


# ---------------------------------------------------------------------------
# Block types — tagged union via dataclasses.
# ---------------------------------------------------------------------------


@dataclass
class HeadingBlock:
    """A heading rendered above body content. Level 1 emits a TOC entry."""

    text: str
    level: Literal[1, 2] = 2
    toc: bool = True


@dataclass
class ParaBlock:
    """A paragraph of body text. May contain reportlab HTML markup."""

    text: str


@dataclass
class BulletsBlock:
    """A bulleted list. Each item may contain reportlab HTML markup."""

    items: Sequence[str]


@dataclass
class OrderedListBlock:
    """A numbered list. Each item may contain reportlab HTML markup.

    start: first number (default 1).
    """

    items: Sequence[str]
    start: int = 1


@dataclass
class TableBlock:
    """A table with a styled header row.

    col_widths: list of widths in points (use inch * N). If None, reportlab
    distributes width automatically — usually fine for 2-3 columns, ugly for more.

    emphasized_rows: 0-based row indices (body rows, header excluded) to
    render with bold text and a tinted background. Use sparingly — it's
    visual emphasis, not a data attribute.
    """

    header: Sequence[str]
    rows: Sequence[Sequence[str]]
    col_widths: Sequence[float] | None = None
    emphasized_rows: Sequence[int] = ()


@dataclass
class CalloutBlock:
    """A boxed callout. Use sparingly — they break flow.

    keep_with_previous: when True, the callout is rendered KeepTogether
    with the immediately preceding block, preventing it from floating
    alone to the next page.
    """

    text: str
    kind: Literal["note", "warn"] = "note"
    keep_with_previous: bool = False


@dataclass
class PageBreakBlock:
    """Forces a page break."""


Block = (
    HeadingBlock
    | ParaBlock
    | BulletsBlock
    | OrderedListBlock
    | TableBlock
    | CalloutBlock
    | PageBreakBlock
)


@dataclass
class Section:
    """A top-level section. Renders as H1 followed by its blocks."""

    title: str
    blocks: list[Block] = field(default_factory=list)
    starts_on_new_page: bool = False


# ---------------------------------------------------------------------------
# Style construction (theme-driven).
# ---------------------------------------------------------------------------


def _build_styles(theme: Theme) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    out: dict[str, ParagraphStyle] = {}

    out["DocTitle"] = ParagraphStyle(
        name="DocTitle",
        parent=base["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        alignment=TA_CENTER,
        spaceAfter=12,
        textColor=HexColor(theme.title_color),
    )
    out["DocTitleLeft"] = ParagraphStyle(
        name="DocTitleLeft",
        parent=out["DocTitle"],
        alignment=TA_LEFT,
        spaceAfter=4,
    )
    out["DocSubtitle"] = ParagraphStyle(
        name="DocSubtitle",
        parent=base["Heading2"],
        fontName="Helvetica",
        fontSize=12,
        leading=15,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=HexColor(theme.subtitle_color),
    )
    out["DocSubtitleLeft"] = ParagraphStyle(
        name="DocSubtitleLeft",
        parent=out["DocSubtitle"],
        alignment=TA_LEFT,
        spaceAfter=14,
    )
    out["CoverMeta"] = ParagraphStyle(
        name="CoverMeta",
        parent=base["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=HexColor(theme.text_muted),
        spaceAfter=4,
    )
    out["MetaLabel"] = ParagraphStyle(
        name="MetaLabel",
        parent=base["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        alignment=TA_LEFT,
        textColor=HexColor(theme.metadata_label_color),
        spaceAfter=1,
    )
    out["MetaValue"] = ParagraphStyle(
        name="MetaValue",
        parent=base["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        alignment=TA_LEFT,
        textColor=HexColor(theme.metadata_value_color),
        spaceAfter=8,
    )
    out["H1"] = ParagraphStyle(
        name="H1",
        parent=base["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        spaceBefore=18,
        spaceAfter=8,
        textColor=HexColor(theme.heading_color),
    )
    out["H2"] = ParagraphStyle(
        name="H2",
        parent=base["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=15,
        spaceBefore=14,
        spaceAfter=4,
        textColor=HexColor(theme.subheading_color),
    )
    out["Body"] = ParagraphStyle(
        name="Body",
        parent=base["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        spaceAfter=7,
        alignment=TA_LEFT,
        textColor=HexColor(theme.text_primary),
    )
    out["BodySmall"] = ParagraphStyle(
        name="BodySmall",
        parent=base["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        spaceAfter=4,
        alignment=TA_LEFT,
        textColor=HexColor(theme.table_cell_fg),
    )
    out["BodySmallBold"] = ParagraphStyle(
        name="BodySmallBold",
        parent=out["BodySmall"],
        fontName="Helvetica-Bold",
    )
    out["Bullet"] = ParagraphStyle(
        name="Bullet",
        parent=out["Body"],
        leftIndent=18,
        bulletIndent=4,
        spaceAfter=4,
    )
    out["Numbered"] = ParagraphStyle(
        name="Numbered",
        parent=out["Body"],
        leftIndent=22,
        bulletIndent=4,
        spaceAfter=4,
    )
    out["Meta"] = ParagraphStyle(
        name="Meta",
        parent=base["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=HexColor(theme.text_muted),
        spaceAfter=10,
    )
    out["Footer"] = ParagraphStyle(
        name="Footer",
        parent=base["BodyText"],
        fontSize=8,
        leading=10,
        textColor=HexColor(theme.footer_text_color),
        alignment=TA_CENTER,
    )
    out["Callout"] = ParagraphStyle(
        name="Callout",
        parent=base["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        leftIndent=4,
        rightIndent=4,
        spaceBefore=4,
        spaceAfter=4,
        textColor=HexColor(theme.callout_text),
    )
    out["TOCHeading"] = ParagraphStyle(
        name="TOCHeading",
        parent=base["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        spaceAfter=12,
        textColor=HexColor(theme.toc_heading_color),
    )
    out["TOC1"] = ParagraphStyle(
        name="TOC1",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        leftIndent=0,
        firstLineIndent=0,
        textColor=HexColor(theme.toc_level1_color),
    )
    out["TOC2"] = ParagraphStyle(
        name="TOC2",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        leftIndent=18,
        textColor=HexColor(theme.toc_level2_color),
    )
    return out


# ---------------------------------------------------------------------------
# Block-to-flowable rendering.
# ---------------------------------------------------------------------------


def _maybe_caps(text: str, theme: Theme) -> str:
    """Uppercase if theme requests caps headings.

    Note: HTML markup tags inside the text remain functional after upper().
    Tag names like 'b', 'i', 'sub' are case-insensitive in reportlab's
    parser. Attribute values (e.g., color="#ff0000") are NOT recursed
    into, but we don't expect them in heading text.
    """
    return text.upper() if theme.caps_headings else text


def _cell(
    text: str,
    styles: dict[str, ParagraphStyle],
    bold: bool = False,
) -> Paragraph:
    """Wrap a table-cell string so it word-wraps inside its column."""
    return Paragraph(text, styles["BodySmallBold" if bold else "BodySmall"])


def _render_table(
    block: TableBlock,
    styles: dict[str, ParagraphStyle],
    theme: Theme,
) -> Table:
    emph = set(block.emphasized_rows)
    header_row = [_cell(h, styles, bold=True) for h in block.header]
    body_rows = [
        [_cell(c, styles, bold=(i in emph)) for c in row]
        for i, row in enumerate(block.rows)
    ]
    data = [header_row] + body_rows

    tbl = Table(
        data,
        colWidths=list(block.col_widths) if block.col_widths else None,
        repeatRows=1,
    )

    # Override the header-row paragraph color since BodySmallBold uses
    # table_cell_fg (which is body text color, not header text color).
    # We achieve header text color by re-styling the Paragraphs in the
    # header row using a header-specific paragraph style on the fly.
    header_style = ParagraphStyle(
        name="TableHeader",
        parent=styles["BodySmallBold"],
        textColor=HexColor(theme.table_header_fg),
    )
    for i, h in enumerate(block.header):
        data[0][i] = Paragraph(h, header_style)

    style_cmds: list = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), HexColor(theme.table_header_bg)),
        ("LINEBELOW", (0, 0), (-1, 0), 1.0, HexColor(theme.table_header_rule)),
        ("LINEABOVE", (0, 0), (-1, 0), 1.0, HexColor(theme.table_header_rule)),
        # Row separators
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, HexColor(theme.table_body_rule)),
        # Padding
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for idx in emph:
        row = idx + 1
        style_cmds.append(
            ("BACKGROUND", (0, row), (-1, row), HexColor(theme.table_emph_bg))
        )
    tbl.setStyle(TableStyle(style_cmds))
    return tbl


def _render_callout(
    block: CalloutBlock,
    styles: dict[str, ParagraphStyle],
    theme: Theme,
) -> Table:
    if block.kind == "warn":
        bg = HexColor(theme.callout_warn_bg)
        border = HexColor(theme.callout_border_warn)
        prefix = "<b>Warning:</b> "
    else:
        bg = HexColor(theme.callout_note_bg)
        border = HexColor(theme.callout_border_note)
        prefix = "<b>Note:</b> "
    para = Paragraph(prefix + block.text, styles["Callout"])
    tbl = Table([[para]])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.7, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return tbl


def _render_block(
    block: Block,
    styles: dict[str, ParagraphStyle],
    theme: Theme,
) -> list:
    if isinstance(block, HeadingBlock):
        text = _maybe_caps(block.text, theme) if block.level == 1 else block.text
        style = styles["H1"] if block.level == 1 else styles["H2"]
        if block.toc:
            level = 0 if block.level == 1 else 1
            return [TocParagraph(text, style, level)]
        return [Paragraph(text, style)]
    if isinstance(block, ParaBlock):
        return [Paragraph(block.text, styles["Body"])]
    if isinstance(block, BulletsBlock):
        return [
            Paragraph(item, styles["Bullet"], bulletText="•")
            for item in block.items
        ]
    if isinstance(block, OrderedListBlock):
        return [
            Paragraph(item, styles["Numbered"], bulletText=f"{n}.")
            for n, item in enumerate(block.items, start=block.start)
        ]
    if isinstance(block, TableBlock):
        return [_render_table(block, styles, theme), Spacer(1, 6)]
    if isinstance(block, CalloutBlock):
        return [_render_callout(block, styles, theme), Spacer(1, 4)]
    if isinstance(block, PageBreakBlock):
        return [PageBreak()]
    raise TypeError(f"Unknown block type: {type(block).__name__}")


# ---------------------------------------------------------------------------
# Doc template with theme-aware chrome.
# ---------------------------------------------------------------------------


class _ReportDocTemplate(BaseDocTemplate):
    """Custom doc template: paints background, draws decorations, notifies
    TOC on opted-in headings, tracks total pages."""

    def __init__(
        self,
        *args,
        doc_title: str = "",
        show_header: bool = True,
        theme: Theme = LIGHT_THEME,
        starts_with_cover: bool = True,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._doc_title = doc_title
        self._show_header = show_header
        self._theme = theme
        self._total_pages = 0

        page_w, page_h = self.pagesize
        margin = 0.6 * inch
        frame_top_offset = 0.3 * inch if show_header else 0.0
        body_frame = Frame(
            margin,
            margin,
            page_w - 2 * margin,
            page_h - 2 * margin - frame_top_offset,
            id="body",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        cover_frame = Frame(
            margin,
            margin,
            page_w - 2 * margin,
            page_h - 2 * margin,
            id="cover",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )

        cover_template = PageTemplate(
            id="cover", frames=[cover_frame], onPage=self._draw_cover_chrome
        )
        body_template = PageTemplate(
            id="body", frames=[body_frame], onPage=self._draw_body_chrome
        )
        # Reportlab uses pageTemplates[0] for page 1. Order accordingly so
        # the chrome on page 1 matches the document's actual first page.
        if starts_with_cover:
            self.addPageTemplates([cover_template, body_template])
        else:
            self.addPageTemplates([body_template, cover_template])

    def afterFlowable(self, flowable):
        if isinstance(flowable, TocParagraph):
            level = flowable._toc_level
            text = flowable.getPlainText()
            self.notify("TOCEntry", (level, text, self.page))

    # -- chrome helpers ----------------------------------------------------

    def _paint_background(self, canvas) -> None:
        page_w, page_h = self.pagesize
        canvas.setFillColor(HexColor(self._theme.background))
        canvas.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    def _draw_corner_brackets(self, canvas) -> None:
        if not self._theme.corner_brackets:
            return
        page_w, page_h = self.pagesize
        size = self._theme.corner_bracket_size_in * inch
        inset = 0.3 * inch
        canvas.setStrokeColor(HexColor(self._theme.corner_bracket_color))
        canvas.setLineWidth(self._theme.corner_bracket_width_pt)
        # Top-left: vertical going down + horizontal going right
        x0, y0 = inset, page_h - inset
        canvas.line(x0, y0, x0, y0 - size)            # vertical down
        canvas.line(x0, y0, x0 + size, y0)            # horizontal right
        # Bottom-right: vertical going up + horizontal going left
        x1, y1 = page_w - inset, inset
        canvas.line(x1, y1, x1, y1 + size)            # vertical up
        canvas.line(x1, y1, x1 - size, y1)            # horizontal left

    def _draw_cover_chrome(self, canvas, doc) -> None:
        canvas.saveState()
        self._paint_background(canvas)
        self._draw_corner_brackets(canvas)
        canvas.restoreState()

    def _draw_body_chrome(self, canvas, doc) -> None:
        canvas.saveState()
        self._paint_background(canvas)
        self._draw_corner_brackets(canvas)
        page_w, page_h = self.pagesize
        # Header
        if self._show_header and self._doc_title:
            canvas.setFont("Helvetica", 8.5)
            canvas.setFillColor(HexColor(self._theme.header_text_color))
            header_text = (
                self._doc_title.upper()
                if self._theme.caps_headings
                else self._doc_title
            )
            canvas.drawString(0.6 * inch, page_h - 0.42 * inch, header_text)
            if self._theme.header_rule:
                canvas.setStrokeColor(HexColor(self._theme.header_rule_color))
                canvas.setLineWidth(0.4)
                canvas.line(
                    0.6 * inch, page_h - 0.5 * inch,
                    page_w - 0.6 * inch, page_h - 0.5 * inch,
                )
        # Footer
        if self._theme.footer_rule:
            canvas.setStrokeColor(HexColor(self._theme.footer_rule_color))
            canvas.setLineWidth(0.4)
            canvas.line(
                0.6 * inch, 0.55 * inch,
                page_w - 0.6 * inch, 0.55 * inch,
            )
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(HexColor(self._theme.footer_text_color))
        if self._total_pages:
            footer = f"Page {doc.page} of {self._total_pages}"
        else:
            footer = f"Page {doc.page}"
        canvas.drawCentredString(page_w / 2, 0.35 * inch, footer)
        canvas.restoreState()


# ---------------------------------------------------------------------------
# Cover and TOC builders.
# ---------------------------------------------------------------------------


def _build_metadata_block(
    metadata: dict[str, str],
    styles: dict[str, ParagraphStyle],
    theme: Theme,
    align: Literal["center", "left"] = "center",
) -> list:
    """Render metadata as a stacked LABEL / value block.

    Both layouts use the same color treatment — LABELS in
    metadata_label_color (often the theme accent), values in
    metadata_value_color — so the cover and inline-title look
    visually consistent. The only difference is alignment:
    'center' for cover pages, 'left' for inline title blocks.
    """
    if not metadata:
        return []
    label_align = TA_CENTER if align == "center" else TA_LEFT
    label_style = ParagraphStyle(
        name=f"MetaLabel{align.title()}",
        parent=styles["MetaLabel"],
        alignment=label_align,
    )
    value_style = ParagraphStyle(
        name=f"MetaValue{align.title()}",
        parent=styles["MetaValue"],
        alignment=label_align,
    )
    flowables = []
    for k, v in metadata.items():
        label = k.upper()
        flowables.append(Paragraph(label, label_style))
        flowables.append(Paragraph(v, value_style))
    return flowables


def _build_cover(
    title: str,
    subtitle: str | None,
    metadata: dict[str, str],
    styles: dict[str, ParagraphStyle],
    theme: Theme,
) -> list:
    out: list = []
    out.append(Spacer(1, 2.5 * inch))
    out.append(Paragraph(_maybe_caps(title, theme), styles["DocTitle"]))
    if subtitle:
        out.append(Paragraph(subtitle, styles["DocSubtitle"]))
    out.extend(_build_metadata_block(metadata, styles, theme, align="center"))
    out.append(NextPageTemplate("body"))
    out.append(PageBreak())
    return out


def _build_inline_title(
    title: str,
    subtitle: str | None,
    metadata: dict[str, str],
    styles: dict[str, ParagraphStyle],
    theme: Theme,
) -> list:
    """Title block at the top of page 1 (cover_page=False).

    Rendered left-aligned with a stacked LABEL/value metadata layout —
    matches the strix-halo aesthetic when paired with the cyber theme.
    """
    out: list = []
    out.append(NextPageTemplate("body"))
    out.append(Paragraph(_maybe_caps(title, theme), styles["DocTitleLeft"]))
    if subtitle:
        out.append(Paragraph(subtitle, styles["DocSubtitleLeft"]))
    out.extend(_build_metadata_block(metadata, styles, theme, align="left"))
    out.append(Spacer(1, 12))
    return out


def _build_toc(styles: dict[str, ParagraphStyle], theme: Theme) -> list:
    out: list = []
    heading_text = "CONTENTS" if theme.caps_headings else "Contents"
    out.append(Paragraph(heading_text, styles["TOCHeading"]))
    toc = TableOfContents()
    toc.levelStyles = [styles["TOC1"], styles["TOC2"]]
    out.append(toc)
    out.append(PageBreak())
    return out


# ---------------------------------------------------------------------------
# Section validation and assembly.
# ---------------------------------------------------------------------------


def _validate_section(section: Section, idx: int) -> None:
    if not section.blocks:
        return
    first = section.blocks[0]
    if isinstance(first, PageBreakBlock):
        raise ValueError(
            f"Section {idx} ({section.title!r}): a PageBreakBlock as the "
            "first child causes the section title to render alone on the "
            "previous page. Use Section(starts_on_new_page=True) instead."
        )
    if isinstance(first, HeadingBlock) and first.level == 1:
        if first.text.strip().lower().endswith(section.title.strip().lower()):
            raise ValueError(
                f"Section {idx}: first block is an H1 that duplicates the "
                "section title. Section titles render automatically; remove "
                "the redundant HeadingBlock."
            )


def _assemble_section(
    section: Section,
    section_index: int,
    styles: dict[str, ParagraphStyle],
    numbered: bool,
    theme: Theme,
) -> list:
    _validate_section(section, section_index)

    if numbered:
        title_text = f"{section_index}. {section.title}"
    else:
        title_text = section.title
    title_text = _maybe_caps(title_text, theme)
    title_para = TocParagraph(title_text, styles["H1"], toc_level=0)

    out: list = []
    if section.starts_on_new_page and section_index > 1:
        out.append(PageBreak())

    current_group: list = [title_para]

    def flush() -> None:
        nonlocal current_group
        if not current_group:
            return
        if len(current_group) == 1:
            out.append(current_group[0])
        else:
            out.append(KeepTogether(current_group))
        current_group = []

    for i, block in enumerate(section.blocks):
        if isinstance(block, PageBreakBlock):
            flush()
            out.append(PageBreak())
            continue

        rendered = _render_block(block, styles, theme)

        if i == 0:
            current_group.extend(rendered)
        elif isinstance(block, CalloutBlock) and block.keep_with_previous:
            if not current_group:
                current_group = list(rendered)
            else:
                current_group.extend(rendered)
        else:
            flush()
            current_group = list(rendered)

    flush()
    return out


# ---------------------------------------------------------------------------
# Layout heuristics: section packing.
# ---------------------------------------------------------------------------


def _body_dimensions(
    page_size: tuple[float, float], show_header: bool
) -> tuple[float, float]:
    page_w, page_h = page_size
    margin = 0.6 * inch
    header_band = 0.3 * inch if show_header else 0.0
    body_w = page_w - 2 * margin
    body_h = page_h - 2 * margin - header_band
    return body_w, body_h


def _measure_natural_height(flowables: list, avail_width: float) -> float:
    total = 0.0
    for f in flowables:
        if isinstance(f, (PageBreak, CondPageBreak)):
            continue
        if isinstance(f, KeepTogether):
            inner = getattr(f, "_content", None) or []
            total += _measure_natural_height(inner, avail_width)
            continue
        try:
            _, h = f.wrap(avail_width, 1_000_000)
            total += h
        except Exception:
            pass
    return total


def _section_break_threshold(
    section_flowables: list,
    avail_width: float,
    body_h: float,
    half_body_h: float,
) -> float:
    predicted = _measure_natural_height(section_flowables, avail_width)
    return min(body_h, max(half_body_h, predicted))


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------


def build_report(
    output_path: str,
    title: str,
    subtitle: str | None = None,
    metadata: dict[str, str] | None = None,
    sections: Sequence[Section] | None = None,
    page_size: tuple[float, float] = letter,
    cover_page: bool | object = _UNSET,
    table_of_contents: bool | object = _UNSET,
    show_header: bool = True,
    numbered_sections: bool | object = _UNSET,
    pack_sections: bool = True,
    theme: Theme | str | None = "default",
    layout: Layout | str | None = None,
) -> None:
    """Build a branded PDF report and write it to output_path.

    Args:
        output_path: Absolute path for the output PDF.
        title: Document title (cover and running header).
        subtitle: Optional second line on the cover or under the title.
        metadata: Optional dict of label->value rendered as a meta block.
        sections: Ordered sections rendered after the cover/TOC.
        page_size: reportlab page-size tuple.
        cover_page: When True, title and metadata get their own page with
            vertical centering. When False, the title runs inline at the
            top of the first content page. If unset, falls back to the
            layout's default.
        table_of_contents: When True, TOC on page after cover. Falls back
            to the layout's default when unset.
        show_header: When True (default), running header on body pages.
        numbered_sections: When True, titles auto-prefixed with index.
            Falls back to the layout's default when unset.
        pack_sections: When True (default), CondPageBreak heuristic
            inserted between sections to avoid cramped transitions.
        theme: Visual theme. Pass a registered name ("light", "cyber") or
            a Theme instance for full control. Default "light".
        layout: Structural-element preset bundling cover_page,
            table_of_contents, and numbered_sections into a single
            named option. Registered presets:

            - "formal" (default): cover + TOC + numbered sections.
              For analytical deliverables, audit reports, white papers.
            - "tactical": no cover, no TOC, no numbering. Inline title
              at top of page 1, section titles read as standalone
              callouts. Pair with theme="cyber" for the strix-halo
              tactical-briefing aesthetic.
            - "navigable_tactical": tactical look but TOC retained for
              navigation. Use for cyber-themed analyses > 6 pages.

            Pass a Layout instance for a custom preset. Individual
            parameters (cover_page, table_of_contents, numbered_sections)
            override the layout's defaults if explicitly set, so you can
            mix layout="tactical" with table_of_contents=True etc.

    Raises:
        ValueError: a section is malformed, theme/layout name is unknown.
        TypeError: a block is of an unrecognised type.
        OSError: output_path is not writable.
    """
    sections = list(sections or [])
    metadata = metadata or {}
    resolved_theme = _resolve_theme(theme)
    resolved_layout = _resolve_layout(layout)
    # Layout defaults; explicit kwargs override.
    if cover_page is _UNSET:
        cover_page = resolved_layout.cover_page
    if table_of_contents is _UNSET:
        table_of_contents = resolved_layout.table_of_contents
    if numbered_sections is _UNSET:
        numbered_sections = resolved_layout.numbered_sections
    styles = _build_styles(resolved_theme)

    def make_doc() -> _ReportDocTemplate:
        return _ReportDocTemplate(
            output_path,
            pagesize=page_size,
            title=title,
            author=metadata.get("Author", ""),
            doc_title=title,
            show_header=show_header,
            theme=resolved_theme,
            starts_with_cover=cover_page,
            leftMargin=0.6 * inch,
            rightMargin=0.6 * inch,
            topMargin=0.6 * inch,
            bottomMargin=0.6 * inch,
        )

    def build_story() -> list:
        story: list = []
        if cover_page:
            story.extend(
                _build_cover(title, subtitle, metadata, styles, resolved_theme)
            )
        else:
            story.extend(
                _build_inline_title(
                    title, subtitle, metadata, styles, resolved_theme
                )
            )
        if table_of_contents:
            story.extend(_build_toc(styles, resolved_theme))

        body_w, body_h = _body_dimensions(page_size, show_header)
        half_body_h = 0.5 * body_h
        for idx, section in enumerate(sections, start=1):
            section_flowables = _assemble_section(
                section, idx, styles, numbered_sections, resolved_theme
            )
            if pack_sections and idx > 1 and not section.starts_on_new_page:
                threshold = _section_break_threshold(
                    section_flowables, body_w, body_h, half_body_h
                )
                story.append(CondPageBreak(threshold))
            story.extend(section_flowables)
        return story

    # First pass: discover total pages.
    doc1 = make_doc()
    doc1.multiBuild(build_story())
    total_pages = doc1.page

    # Second pass: render with total known.
    doc2 = make_doc()
    doc2._total_pages = total_pages
    doc2.multiBuild(build_story())


__all__ = [
    "build_report",
    "Section",
    "HeadingBlock",
    "ParaBlock",
    "BulletsBlock",
    "OrderedListBlock",
    "TableBlock",
    "CalloutBlock",
    "PageBreakBlock",
    "Theme",
    "LIGHT_THEME",
    "CYBER_THEME",
    "THEMES",
    "Layout",
    "FORMAL_LAYOUT",
    "TACTICAL_LAYOUT",
    "NAVIGABLE_TACTICAL_LAYOUT",
    "LAYOUTS",
]
