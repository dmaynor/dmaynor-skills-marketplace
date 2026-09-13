"""Load versioned doctrine references from packaged resources, without network I/O.

Catalog inclusion is a reference aid, not evidence of compliance. Source summaries
are paraphrases; severity and implementation policies are local engine choices.
"""

from __future__ import annotations

from copy import deepcopy
from importlib.resources import files
from typing import Any

from .validators import ValidationFailure, loads_json, validate


def _validate_catalog(catalog: object) -> dict[str, Any]:
    """Check the portable contract and reject ambiguous rule identities."""
    validate("doctrine", catalog)
    seen: set[str] = set()
    for index, rule in enumerate(catalog["rules"]):
        identifier = rule["rule_id"]
        if identifier in seen:
            raise ValidationFailure(
                "DOCTRINE_DUPLICATE_ID", f"Duplicate doctrine rule ID: {identifier}",
                f"$.rules[{index}].rule_id", "Use one definition for each rule ID.",
            )
        seen.add(identifier)
    return catalog


def load_catalog() -> dict[str, Any]:
    """Return a fresh validated catalog from the installed package.

    No caller-owned dictionary or process-global mutable catalog is returned.
    Source editions are pinned in citations; this does not check for new editions.
    """
    resource = files("sat_engine").joinpath("resources", "doctrine", "catalog.v1.json")
    try:
        catalog = loads_json(resource.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        raise ValidationFailure(
            "DOCTRINE_RESOURCE_UNAVAILABLE", "The packaged doctrine catalog could not be read.",
            "$.catalog", "Reinstall a complete SAT engine package including its resources.",
        ) from exc
    return deepcopy(_validate_catalog(catalog))


def resolve_rules(
    rule_ids: list[str] | tuple[str, ...], catalog: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Resolve selected IDs deterministically and return independent rule objects.

    Repeated selections are deduplicated and IDs are sorted. A supplied catalog
    may select/reorder packaged rules or add explicit local policies. It cannot
    redefine a packaged rule or introduce an unverified external-source principle.
    Schema validation alone cannot establish the truth of a citation.
    """
    if not isinstance(rule_ids, (list, tuple)):
        raise ValidationFailure(
            "DOCTRINE_INVALID_IDS", "rule_ids must be an array of nonempty strings.",
            "$.rule_ids", "Pass explicit catalog rule IDs, or an empty array.",
        )
    for index, identifier in enumerate(rule_ids):
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValidationFailure(
                "DOCTRINE_INVALID_IDS", "Each rule ID must be a nonempty string.",
                f"$.rule_ids[{index}]", "Use an exact rule_id from the catalog.",
            )
    packaged = load_catalog()
    if catalog is None:
        selected_catalog = packaged
    else:
        selected_catalog = _validate_catalog(deepcopy(catalog))
        trusted = {rule["rule_id"]: rule for rule in packaged["rules"]}
        for index, rule in enumerate(selected_catalog["rules"]):
            identifier = rule["rule_id"]
            if identifier in trusted and rule != trusted[identifier]:
                raise ValidationFailure(
                    "DOCTRINE_REFERENCE_MISMATCH", f"Packaged rule {identifier} was redefined.",
                    f"$.rules[{index}]", "Use the packaged definition; give a local adaptation a new ID.",
                )
            if identifier not in trusted and not rule["implementation_policy"]:
                raise ValidationFailure(
                    "DOCTRINE_UNVERIFIED_CITATION",
                    f"External-source rule {identifier} is not in the packaged reference catalog.",
                    f"$.rules[{index}]",
                    "Review and package the source before treating it as a source principle; label local policies explicitly.",
                )
    by_id = {rule["rule_id"]: rule for rule in selected_catalog["rules"]}
    for index, identifier in enumerate(rule_ids):
        if identifier not in by_id:
            raise ValidationFailure(
                "DOCTRINE_UNKNOWN_RULE", f"Unknown doctrine rule ID: {identifier}",
                f"$.rule_ids[{index}]", "Choose an exact ID from the available catalog; no citation was inferred.",
            )
    return [deepcopy(by_id[identifier]) for identifier in sorted(set(rule_ids))]
