"""Reusable PDF report builder.

Encodes the house style for branded PDF reports. Callers populate typed
data structures (Section, *Block) and call build_report; styling is owned
here, not at the call site.

Security: any string passed into ParaBlock, HeadingBlock, OrderedListBlock,
BulletsBlock, or TableBlock cells flows through reportlab's Paragraph
parser, which interprets HTML markup. Untrusted input must be escaped via
xml.sax.saxutils.escape() before reaching these blocks. The builder does
NOT escape automatically because callers legitimately use markup like
<b>, <sub>, <super>.

Two-pass build: the document is built with multiBuild() to resolve the
table of contents and Page N of M counters. Side effects in your driver
should be idempotent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Sequence

from reportlab.lib import colors
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


class TocParagraph(Paragraph):
    """A Paragraph subclass that emits a TOC entry when it is laid out.

    Plain Paragraphs styled as H1/H2 do NOT emit TOC entries — only
    TocParagraph instances do. This lets HeadingBlock(toc=False) opt out
    cleanly without parallel paragraph styles.
    """

    def __init__(self, text: str, style: ParagraphStyle, toc_level: int):
        super().__init__(text, style)
        self._toc_level = toc_level


# ---------------------------------------------------------------------------
# Color tokens — fixed palette. Do not parameterize per call.
# ---------------------------------------------------------------------------

COLOR_TEXT_PRIMARY = colors.HexColor("#1a1a1a")
COLOR_TEXT_SECONDARY = colors.HexColor("#333333")
COLOR_TEXT_MUTED = colors.HexColor("#555555")
COLOR_HEADER_RULE = colors.HexColor("#1a1a1a")
COLOR_BODY_RULE = colors.HexColor("#cccccc")
COLOR_HEADER_BG = colors.HexColor("#f5f5f5")
COLOR_EMPH_BG = colors.HexColor("#eef4f9")
COLOR_CALLOUT_NOTE_BG = colors.HexColor("#f0f4f8")
COLOR_CALLOUT_WARN_BG = colors.HexColor("#fdf3e6")
COLOR_CALLOUT_BORDER = colors.HexColor("#cccccc")


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
    """A top-level section. Renders as H1 followed by its blocks.

    numbered: when True (default for build_report), the section index is
    auto-prefixed onto the title (e.g., "1. Introduction"). The driver
    should NOT include numbers in section.title — they will be added by
    the builder.
    """

    title: str
    blocks: list[Block] = field(default_factory=list)
    starts_on_new_page: bool = False


# ---------------------------------------------------------------------------
# Style construction.
# ---------------------------------------------------------------------------


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    out: dict[str, ParagraphStyle] = {}

    out["DocTitle"] = ParagraphStyle(
        name="DocTitle",
        parent=base["Title"],
        fontSize=22,
        leading=26,
        alignment=TA_CENTER,
        spaceAfter=12,
        textColor=COLOR_TEXT_PRIMARY,
    )
    out["DocSubtitle"] = ParagraphStyle(
        name="DocSubtitle",
        parent=base["Heading2"],
        fontSize=14,
        leading=18,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=COLOR_TEXT_SECONDARY,
    )
    out["CoverMeta"] = ParagraphStyle(
        name="CoverMeta",
        parent=base["BodyText"],
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=COLOR_TEXT_MUTED,
        spaceAfter=4,
    )
    out["H1"] = ParagraphStyle(
        name="H1",
        parent=base["Heading1"],
        fontSize=15,
        leading=19,
        spaceBefore=18,
        spaceAfter=8,
        textColor=COLOR_TEXT_PRIMARY,
    )
    out["H2"] = ParagraphStyle(
        name="H2",
        parent=base["Heading2"],
        fontSize=11.5,
        leading=15,
        spaceBefore=14,
        spaceAfter=4,
        textColor=COLOR_TEXT_SECONDARY,
    )
    out["Body"] = ParagraphStyle(
        name="Body",
        parent=base["BodyText"],
        fontSize=10,
        leading=14,
        spaceAfter=7,
        alignment=TA_LEFT,
    )
    out["BodySmall"] = ParagraphStyle(
        name="BodySmall",
        parent=base["BodyText"],
        fontSize=9,
        leading=12,
        spaceAfter=4,
        alignment=TA_LEFT,
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
        fontSize=9,
        leading=12,
        textColor=COLOR_TEXT_MUTED,
        spaceAfter=10,
    )
    out["Footer"] = ParagraphStyle(
        name="Footer",
        parent=base["BodyText"],
        fontSize=8,
        leading=10,
        textColor=COLOR_TEXT_MUTED,
        alignment=TA_CENTER,
    )
    out["Callout"] = ParagraphStyle(
        name="Callout",
        parent=base["BodyText"],
        fontSize=10,
        leading=14,
        leftIndent=4,
        rightIndent=4,
        spaceBefore=4,
        spaceAfter=4,
    )
    out["TOCHeading"] = ParagraphStyle(
        name="TOCHeading",
        parent=base["Heading1"],
        fontSize=15,
        leading=19,
        spaceAfter=12,
        textColor=COLOR_TEXT_PRIMARY,
    )
    out["TOC1"] = ParagraphStyle(
        name="TOC1",
        parent=base["Normal"],
        fontSize=10.5,
        leading=15,
        leftIndent=0,
        firstLineIndent=0,
    )
    out["TOC2"] = ParagraphStyle(
        name="TOC2",
        parent=base["Normal"],
        fontSize=9.5,
        leading=13,
        leftIndent=18,
        textColor=COLOR_TEXT_SECONDARY,
    )
    return out


# ---------------------------------------------------------------------------
# Block-to-flowable rendering.
# ---------------------------------------------------------------------------


def _cell(text: str, styles: dict[str, ParagraphStyle], bold: bool = False) -> Paragraph:
    """Wrap a table-cell string so it word-wraps inside its column."""
    return Paragraph(text, styles["BodySmallBold" if bold else "BodySmall"])


def _render_table(block: TableBlock, styles: dict[str, ParagraphStyle]) -> Table:
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

    # Modernized table style: horizontal rules only, no vertical grid.
    style_cmds: list = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADER_BG),
        ("LINEBELOW", (0, 0), (-1, 0), 1.0, COLOR_HEADER_RULE),
        ("LINEABOVE", (0, 0), (-1, 0), 1.0, COLOR_HEADER_RULE),
        # Row separators
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, COLOR_BODY_RULE),
        # Padding
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    # Emphasized rows: tinted background. (Bold is applied via _cell.)
    for idx in emph:
        row = idx + 1  # account for header
        style_cmds.append(("BACKGROUND", (0, row), (-1, row), COLOR_EMPH_BG))
    tbl.setStyle(TableStyle(style_cmds))
    return tbl


def _render_callout(block: CalloutBlock, styles: dict[str, ParagraphStyle]) -> Table:
    bg = COLOR_CALLOUT_WARN_BG if block.kind == "warn" else COLOR_CALLOUT_NOTE_BG
    prefix = "<b>Warning:</b> " if block.kind == "warn" else "<b>Note:</b> "
    para = Paragraph(prefix + block.text, styles["Callout"])
    tbl = Table([[para]])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_CALLOUT_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return tbl


def _render_block(block: Block, styles: dict[str, ParagraphStyle]) -> list:
    if isinstance(block, HeadingBlock):
        style = styles["H1"] if block.level == 1 else styles["H2"]
        if block.toc:
            level = 0 if block.level == 1 else 1
            return [TocParagraph(block.text, style, level)]
        return [Paragraph(block.text, style)]
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
        return [_render_table(block, styles), Spacer(1, 6)]
    if isinstance(block, CalloutBlock):
        return [_render_callout(block, styles), Spacer(1, 4)]
    if isinstance(block, PageBreakBlock):
        return [PageBreak()]
    raise TypeError(f"Unknown block type: {type(block).__name__}")


# ---------------------------------------------------------------------------
# Doc template with TOC notify + Page-N-of-M support.
# ---------------------------------------------------------------------------


class _ReportDocTemplate(BaseDocTemplate):
    """Custom doc template: notifies TOC on H1/H2 and tracks total pages."""

    def __init__(self, *args, doc_title: str = "", show_header: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self._doc_title = doc_title
        self._show_header = show_header
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

        self.addPageTemplates([
            PageTemplate(id="cover", frames=[cover_frame], onPage=self._draw_cover_chrome),
            PageTemplate(id="body", frames=[body_frame], onPage=self._draw_body_chrome),
        ])

    def afterFlowable(self, flowable):
        """Notify the TOC only when an opted-in heading is laid out.

        Plain Paragraphs styled H1/H2 do NOT emit entries — only
        TocParagraph instances do. Section titles are auto-rendered as
        TocParagraph; HeadingBlock entries opt in via toc=True.
        """
        if isinstance(flowable, TocParagraph):
            level = flowable._toc_level
            text = flowable.getPlainText()
            self.notify("TOCEntry", (level, text, self.page))

    def _draw_cover_chrome(self, canvas, doc) -> None:
        # Cover page intentionally has no header/footer.
        pass

    def _draw_body_chrome(self, canvas, doc) -> None:
        canvas.saveState()
        page_w, page_h = self.pagesize
        # Header
        if self._show_header and self._doc_title:
            canvas.setFont("Helvetica", 8.5)
            canvas.setFillColor(COLOR_TEXT_MUTED)
            canvas.drawString(0.6 * inch, page_h - 0.42 * inch, self._doc_title)
            canvas.setStrokeColor(COLOR_BODY_RULE)
            canvas.setLineWidth(0.4)
            canvas.line(0.6 * inch, page_h - 0.5 * inch,
                        page_w - 0.6 * inch, page_h - 0.5 * inch)
        # Footer
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(COLOR_TEXT_MUTED)
        if self._total_pages:
            footer = f"Page {doc.page} of {self._total_pages}"
        else:
            footer = f"Page {doc.page}"
        canvas.drawCentredString(page_w / 2, 0.35 * inch, footer)
        canvas.restoreState()


# ---------------------------------------------------------------------------
# Section validation and assembly.
# ---------------------------------------------------------------------------


def _validate_section(section: Section, idx: int) -> None:
    """Catch driver mistakes that produced the v2 PDF defects."""
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
) -> list:
    """Turn a Section into a flat list of flowables.

    Group-based assembly:
    - The title plus the first block form group 0 (prevents heading orphans).
    - Each subsequent block normally starts a new group.
    - A CalloutBlock with keep_with_previous=True joins the current group
      instead of starting a new one — the callout stays with the content
      it qualifies.
    - PageBreakBlock flushes the current group, emits a page break, and
      starts a new empty group.

    Each group becomes a single KeepTogether flowable (if it has 2+ items)
    or a plain flowable (if just one). This is what guarantees that a
    callout never floats to the next page alone.
    """
    _validate_section(section, section_index)

    title_text = (
        f"{section_index}. {section.title}" if numbered else section.title
    )
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

        rendered = _render_block(block, styles)

        if i == 0:
            # First block always joins the title group to avoid heading orphans.
            current_group.extend(rendered)
        elif isinstance(block, CalloutBlock) and block.keep_with_previous:
            # Stay in the current group with whatever it currently anchors.
            if not current_group:
                current_group = list(rendered)
            else:
                current_group.extend(rendered)
        else:
            # Normal block: end the previous group and start a new one.
            flush()
            current_group = list(rendered)

    flush()
    return out


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------


def _body_dimensions(
    page_size: tuple[float, float], show_header: bool
) -> tuple[float, float]:
    """Return (body_width, body_height) — the usable frame inside margins."""
    page_w, page_h = page_size
    margin = 0.6 * inch
    header_band = 0.3 * inch if show_header else 0.0
    body_w = page_w - 2 * margin
    body_h = page_h - 2 * margin - header_band
    return body_w, body_h


def _half_body_height(
    page_size: tuple[float, float], show_header: bool
) -> float:
    """Half the usable body-frame height — the lower bound on the
    section-break threshold (the 'previous section was large' rule)."""
    _, body_h = _body_dimensions(page_size, show_header)
    return 0.5 * body_h


def _measure_natural_height(flowables: list, avail_width: float) -> float:
    """Sum of natural rendered heights for a list of flowables.

    Used to predict how tall an upcoming section will be so the
    CondPageBreak threshold can be set to that height.

    Subtleties:
    - PageBreak / CondPageBreak contribute zero — they're layout
      instructions, not content.
    - KeepTogether.wrap() returns (0, 0) outside a live doc context,
      so we recurse into its _content list directly.
    - Other flowables (Paragraph, Table, Spacer) measure correctly via
      wrap() with a generous availHeight that prevents internal splitting.
    - On any wrap exception we silently skip the flowable; the threshold
      is then a slight underestimate, which is the safe direction (the
      worst case is a section that could have been packed but instead
      gets a fresh page — visually fine, just slightly less dense).
    """
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
    """Compute the CondPageBreak threshold for the upcoming section.

    Combines two rules into one threshold:
    1. 'Previous section was large' — fires when remaining space is
       less than half the body height. (Lower bound: half_body_h.)
    2. 'Next section is large' — fires when remaining space is less
       than the next section's natural height. (Upper bound: body_h,
       so multi-page sections don't trigger on a fresh page.)
    """
    predicted = _measure_natural_height(section_flowables, avail_width)
    return min(body_h, max(half_body_h, predicted))


def build_report(
    output_path: str,
    title: str,
    subtitle: str | None = None,
    metadata: dict[str, str] | None = None,
    sections: Sequence[Section] | None = None,
    page_size: tuple[float, float] = letter,
    cover_page: bool = True,
    table_of_contents: bool = True,
    show_header: bool = True,
    numbered_sections: bool = True,
    pack_sections: bool = True,
) -> None:
    """Build a branded PDF report and write it to output_path.

    Args:
        output_path: Absolute path for the output PDF.
        title: Document title shown on the cover and in the running header.
        subtitle: Optional second line on the cover.
        metadata: Optional dict of label->value rendered as a meta block on
            the cover page (e.g., {"Author": "...", "Date": "2026-05-07"}).
        sections: Ordered sections rendered after the cover/TOC.
        page_size: reportlab page-size tuple. Default letter; pass A4 for non-US.
        cover_page: When True (default), the title and metadata get their own
            page with vertical centering. When False, the title runs inline
            ahead of the first section.
        table_of_contents: When True (default), a TOC is generated on the
            page after the cover. Resolved via two-pass build.
        show_header: When True (default), every body page shows a thin
            running header with the document title.
        numbered_sections: When True (default), each section title is
            auto-prefixed with its 1-based index.
        pack_sections: When True (default), the builder inserts a
            CondPageBreak before each section (after the first) with a
            threshold equal to half the body height. This implements the
            rule: a section that consumed more than half a page is
            followed by a fresh page for the next section, instead of
            cramming the next section's heading into the bottom of the
            previous page. Set False to let sections pack tightly.

    Raises:
        ValueError: a section is malformed (e.g., redundant title heading).
        TypeError: a block is of an unrecognised type.
        OSError: output_path is not writable.
    """
    sections = list(sections or [])
    metadata = metadata or {}
    styles = _build_styles()

    doc = _ReportDocTemplate(
        output_path,
        pagesize=page_size,
        title=title,
        author=metadata.get("Author", ""),
        doc_title=title,
        show_header=show_header,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )

    story: list = []

    # --- Cover ---
    if cover_page:
        # Vertical centering: insert a flexible spacer that pushes content
        # toward vertical mid-page.
        page_h = page_size[1]
        # Roughly center: spacer of ~3" before title.
        story.append(Spacer(1, 2.5 * inch))
        story.append(Paragraph(title, styles["DocTitle"]))
        if subtitle:
            story.append(Paragraph(subtitle, styles["DocSubtitle"]))
        if metadata:
            for k, v in metadata.items():
                story.append(Paragraph(f"<b>{k}:</b> {v}", styles["CoverMeta"]))
        story.append(NextPageTemplate("body"))
        story.append(PageBreak())
    else:
        story.append(NextPageTemplate("body"))
        story.append(Paragraph(title, styles["DocTitle"]))
        if subtitle:
            story.append(Paragraph(subtitle, styles["DocSubtitle"]))
        if metadata:
            meta_line = " &nbsp;|&nbsp; ".join(
                f"<b>{k}:</b> {v}" for k, v in metadata.items()
            )
            story.append(Paragraph(meta_line, styles["Meta"]))
            story.append(Spacer(1, 8))

    # --- TOC ---
    if table_of_contents:
        story.append(Paragraph("Contents", styles["TOCHeading"]))
        toc = TableOfContents()
        toc.levelStyles = [styles["TOC1"], styles["TOC2"]]
        story.append(toc)
        story.append(PageBreak())

    # --- Sections ---
    body_w, body_h = _body_dimensions(page_size, show_header)
    half_body_h = 0.5 * body_h
    for idx, section in enumerate(sections, start=1):
        section_flowables = _assemble_section(
            section, idx, styles, numbered_sections
        )
        # Decide whether to insert a conditional page break. Threshold
        # combines the 'previous section was large' rule (lower bound:
        # half body) and the 'next section is large' rule (upper bound:
        # full body, capped so multi-page sections don't always break).
        if pack_sections and idx > 1 and not section.starts_on_new_page:
            threshold = _section_break_threshold(
                section_flowables, body_w, body_h, half_body_h
            )
            story.append(CondPageBreak(threshold))
        story.extend(section_flowables)

    # Two-pass build for TOC + Page N of M.
    # First pass: discover total page count and TOC entries.
    doc.multiBuild(story)
    total_pages = doc.page
    # Second pass: render with the total known.
    # Recreate doc since multiBuild already consumed the story.
    doc2 = _ReportDocTemplate(
        output_path,
        pagesize=page_size,
        title=title,
        author=metadata.get("Author", ""),
        doc_title=title,
        show_header=show_header,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )
    doc2._total_pages = total_pages
    # Rebuild the same story (rendering is idempotent for our flowables
    # because we reconstruct fresh Paragraph objects in this rebuild path).
    story2 = _rebuild_story(
        title, subtitle, metadata, sections, styles,
        cover_page, table_of_contents, page_size, numbered_sections,
        pack_sections, show_header,
    )
    doc2.multiBuild(story2)


def _rebuild_story(
    title: str,
    subtitle: str | None,
    metadata: dict[str, str],
    sections: Sequence[Section],
    styles: dict[str, ParagraphStyle],
    cover_page: bool,
    table_of_contents: bool,
    page_size: tuple[float, float],
    numbered_sections: bool,
    pack_sections: bool,
    show_header: bool,
) -> list:
    """Identical to the inline assembly in build_report; factored out so
    the two passes use the same logic."""
    story: list = []
    if cover_page:
        story.append(Spacer(1, 2.5 * inch))
        story.append(Paragraph(title, styles["DocTitle"]))
        if subtitle:
            story.append(Paragraph(subtitle, styles["DocSubtitle"]))
        if metadata:
            for k, v in metadata.items():
                story.append(Paragraph(f"<b>{k}:</b> {v}", styles["CoverMeta"]))
        story.append(NextPageTemplate("body"))
        story.append(PageBreak())
    else:
        story.append(NextPageTemplate("body"))
        story.append(Paragraph(title, styles["DocTitle"]))
        if subtitle:
            story.append(Paragraph(subtitle, styles["DocSubtitle"]))
        if metadata:
            meta_line = " &nbsp;|&nbsp; ".join(
                f"<b>{k}:</b> {v}" for k, v in metadata.items()
            )
            story.append(Paragraph(meta_line, styles["Meta"]))
            story.append(Spacer(1, 8))

    if table_of_contents:
        story.append(Paragraph("Contents", styles["TOCHeading"]))
        toc = TableOfContents()
        toc.levelStyles = [styles["TOC1"], styles["TOC2"]]
        story.append(toc)
        story.append(PageBreak())

    body_w, body_h = _body_dimensions(page_size, show_header)
    half_body_h = 0.5 * body_h
    for idx, section in enumerate(sections, start=1):
        section_flowables = _assemble_section(
            section, idx, styles, numbered_sections
        )
        if pack_sections and idx > 1 and not section.starts_on_new_page:
            threshold = _section_break_threshold(
                section_flowables, body_w, body_h, half_body_h
            )
            story.append(CondPageBreak(threshold))
        story.extend(section_flowables)
    return story


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
]
