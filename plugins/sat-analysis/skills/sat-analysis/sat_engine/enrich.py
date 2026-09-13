"""Add deterministic doctrine context to a derived Markdown rendering only."""

from __future__ import annotations

import html
import re
from typing import Any

from .doctrine import resolve_rules
from .validators import ValidationFailure


_NOTICE = (
    "Reference context only; rule selection does not establish compliance, "
    "verify the analysis, or change its judgment. Summaries are paraphrases; "
    "severity labels are local engine choices."
)


def _escape(text: str) -> str:
    text = re.sub(r"[\x00-\x1f\x7f]", " ", html.escape(text, quote=True))
    return re.sub(r"([\\`*_{}\[\]()#+.!|~\-])", r"\\\1", text)


def _reference(rule: dict[str, Any]) -> str:
    """Render curated external URLs as links and local policy URNs as text."""
    citation = _escape(rule["citation"])
    if rule["implementation_policy"]:
        return citation
    return f"[{citation}]({rule['url']})"


def _inline_note(rule: dict[str, Any]) -> str:
    identifier = rule["rule_id"]
    kind = "Local implementation policy" if rule["implementation_policy"] else "Source principle (paraphrase)"
    return (
        f"<!-- sat-engine:doctrine:v1:{identifier}:begin -->"
        f" ({kind}; {_escape(identifier)}; local severity {_escape(rule['severity'])}: "
        f"{_escape(rule['summary'])} {_reference(rule)}. Reference context, not a compliance finding.)"
        f"<!-- sat-engine:doctrine:v1:{identifier}:end -->"
    )


def _append_block(text: str, rules: list[dict[str, Any]], mode: str) -> str:
    if not rules:
        return text
    lines = [f"<!-- sat-engine:doctrine:v1:{mode}:begin -->"]
    if mode == "appendix":
        lines.extend(["## Doctrine references", "", _NOTICE, ""])
        for rule in rules:
            kind = "Local implementation policy" if rule["implementation_policy"] else "Source principle (paraphrase)"
            lines.extend([
                f"### {_escape(rule['rule_id'])}: {_escape(rule['title'])}", "",
                f"{kind}. Local severity: {_escape(rule['severity'])}.", "",
                _escape(rule["summary"]), "", f"Reference: {_reference(rule)}.", "",
            ])
    else:
        lines.extend([_NOTICE, "", " ".join(_inline_note(rule) for rule in rules), ""])
    lines.append(f"<!-- sat-engine:doctrine:v1:{mode}:end -->")
    block = "\n\n" + "\n".join(lines)
    return text if text.endswith(block) else text + block


def enrich(text: str, rule_ids: list[str] | tuple[str, ...], mode: str = "appendix") -> str:
    """Return a derived rendering; never edit an artifact, file, or input object.

    Appendix mode appends a reference section. Inline mode adds compact notes at
    explicit ``[[doctrine:RULE-ID]]`` anchors, preserving those authored anchors;
    rules without an anchor receive compact context at the end. The same call on
    its own output is byte-idempotent. Empty selections return the text unchanged.
    No free-text citation is guessed, retrieved, or declared verified.
    """
    if not isinstance(text, str):
        raise ValidationFailure(
            "ENRICH_INVALID_TEXT", "Enrichment requires a rendered text string.",
            "$.text", "Render the canonical artifact first and pass the derived text.",
        )
    try:
        text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValidationFailure(
            "ENRICH_INVALID_TEXT", "Rendered text contains unpaired Unicode surrogates.",
            "$.text", "Use valid Unicode display text; retain original invalid bytes separately.",
        ) from exc
    if not isinstance(mode, str) or mode not in {"appendix", "inline"}:
        raise ValidationFailure(
            "ENRICH_INVALID_MODE", "Enrichment mode must be appendix or inline.",
            "$.mode", "Choose appendix or inline.",
        )
    rules = resolve_rules(rule_ids)
    if mode == "appendix":
        return _append_block(text, rules, mode)
    unanchored = []
    for rule in rules:
        anchor = f"[[doctrine:{rule['rule_id']}]]"
        if anchor not in text:
            unanchored.append(rule)
            continue
        note = _inline_note(rule)
        # Keep existing generated notes; insert only at unannotated occurrences.
        text = re.sub(re.escape(anchor) + "(?!" + re.escape(note) + ")",
                      lambda match: match.group(0) + note, text)
    return _append_block(text, unanchored, mode)
