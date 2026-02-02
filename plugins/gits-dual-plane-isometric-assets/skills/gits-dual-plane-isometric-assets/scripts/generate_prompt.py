#!/usr/bin/env python3
"""
Generate canonical image generation prompts for dual-plane isometric assets.

Usage:
    python generate_prompt.py <entity_class> [--variant VARIANT] [--rows ROW_SPEC]

Examples:
    python generate_prompt.py NetworkNode
    python generate_prompt.py Building --variant critical_infrastructure
    python generate_prompt.py Ghost --rows "stable,stable,destabilized,destabilized,fragmented,fragmented"
"""

import argparse
import sys
from typing import Optional


# Entity class definitions with default row specifications and Column 5 semantics
ENTITY_DEFINITIONS: dict[str, dict] = {
    # Physical Plane
    "HumanBody": {
        "plane": "physical",
        "default_rows": [
            "civilian operator",
            "civilian operator",
            "military operator",
            "military operator",
            "augmented specialist",
            "augmented specialist",
        ],
        "column5_description": "CyberLinked state showing active interface cables and data stream connection",
    },
    "Building": {
        "plane": "physical",
        "default_rows": [
            "residential building",
            "residential building",
            "commercial building",
            "commercial building",
            "critical infrastructure facility",
            "critical infrastructure facility",
        ],
        "column5_description": "cyber overlay view showing embedded network activity and data flow intensity through hosted nodes",
    },
    # Cyber Plane
    "NetworkNode": {
        "plane": "cyber",
        "default_rows": [
            "civilian infrastructure node",
            "civilian infrastructure node",
            "corporate data center",
            "corporate data center",
            "hardened government node",
            "hardened military node",
        ],
        "column5_description": "internal cyber cutaway showing data routing core, security layers, and resident process activity",
    },
    "DataFlow": {
        "plane": "cyber",
        "default_rows": [
            "low-sensitivity civilian data packet",
            "low-sensitivity civilian data packet",
            "encrypted corporate data stream",
            "encrypted corporate data stream",
            "high-sensitivity classified transmission",
            "high-sensitivity classified transmission",
        ],
        "column5_description": "mid-transit visualization showing packet integrity indicators and encryption envelope",
    },
    "SecurityControl": {
        "plane": "cyber",
        "default_rows": [
            "firewall",
            "firewall",
            "intrusion detection system",
            "intrusion detection system",
            "sandbox containment unit",
            "airgap isolation barrier",
        ],
        "column5_description": "engaged/active configuration showing interception fields and barrier visualization",
    },
    # Cognitive Plane
    "Ghost": {
        "plane": "cognitive",
        "default_rows": [
            "stable ghost (body-resident)",
            "stable ghost (node-resident)",
            "destabilized ghost",
            "destabilized ghost",
            "fragmented ghost",
            "forked ghost instance",
        ],
        "column5_description": "residency state visualization showing substrate anchor type (body-bound silhouette, node tether, or distributed multi-tether)",
    },
    "CognitiveProcess": {
        "plane": "cognitive",
        "default_rows": [
            "routine cognitive task",
            "routine cognitive task",
            "high-demand computation",
            "high-demand computation",
            "autonomous agent process",
            "autonomous agent process",
        ],
        "column5_description": "running state showing active computation patterns and resource consumption flow",
    },
    "MemoryShard": {
        "plane": "cognitive",
        "default_rows": [
            "intact high-fidelity memory",
            "intact high-fidelity memory",
            "decaying memory fragment",
            "decaying memory fragment",
            "encrypted secure memory",
            "corrupted memory shard",
        ],
        "column5_description": "decay rate visualization showing edge erosion and fidelity degradation patterns",
    },
}


def generate_prompt(
    entity_class: str,
    variant: Optional[str] = None,
    row_spec: Optional[list[str]] = None,
) -> str:
    """
    Generate a canonical image generation prompt for the specified entity class.

    Args:
        entity_class: One of the defined entity classes (e.g., 'NetworkNode', 'Ghost')
        variant: Optional variant descriptor for filename/context
        row_spec: Optional list of 6 row descriptions; uses defaults if not provided

    Returns:
        Complete prompt string ready for image generation

    Raises:
        ValueError: If entity_class is not recognized or row_spec has wrong length
    """
    if entity_class not in ENTITY_DEFINITIONS:
        valid_classes = ", ".join(sorted(ENTITY_DEFINITIONS.keys()))
        raise ValueError(
            f"Unknown entity class '{entity_class}'. Valid classes: {valid_classes}"
        )

    definition = ENTITY_DEFINITIONS[entity_class]
    rows = row_spec if row_spec else definition["default_rows"]

    if len(rows) != 6:
        raise ValueError(f"Row specification must have exactly 6 entries, got {len(rows)}")

    plane = definition["plane"]
    column5_desc = definition["column5_description"]

    # Build row breakdown
    row_lines = "\n".join(f"Row {i + 1}: {desc}" for i, desc in enumerate(rows))

    prompt = f"""Red background, 6 rows, 5 columns, 2048x2048 square.

Create a dual-plane isometric asset sheet for {entity_class.upper()} entities ({plane} plane) in a Ghost-in-the-Shell-inspired city simulation.

Each row represents ONE {entity_class}.
Columns 1-4: the same entity isometrically projected facing north-west, north-east, south-east, south-west.
Column 5: {column5_desc}.

ALL ASSETS MUST BE HYPER REALISTIC.
NO SHADOWS.
Centered in each cell.
Consistent scale across all rows.
No text, no UI elements, no symbols, no labels.

Row breakdown:
{row_lines}

Style: Industrial, restrained, clinical. No neon fantasy aesthetics. No holographic UI overlays."""

    return prompt


def generate_filename(
    entity_class: str,
    variant: Optional[str] = None,
) -> str:
    """
    Generate canonical filename for the asset sheet.

    Format: plane_entitytype_variant_states.png
    """
    definition = ENTITY_DEFINITIONS[entity_class]
    plane = definition["plane"]
    entity_lower = entity_class.lower()
    variant_part = f"_{variant}" if variant else ""
    return f"{plane}_{entity_lower}{variant_part}_states.png"


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate canonical prompts for dual-plane isometric assets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Valid entity classes: {', '.join(sorted(ENTITY_DEFINITIONS.keys()))}",
    )
    parser.add_argument(
        "entity_class",
        help="Entity class to generate prompt for",
    )
    parser.add_argument(
        "--variant",
        help="Optional variant name for filename",
    )
    parser.add_argument(
        "--rows",
        help="Comma-separated list of 6 row descriptions (overrides defaults)",
    )
    parser.add_argument(
        "--filename-only",
        action="store_true",
        help="Only output the canonical filename, not the prompt",
    )

    args = parser.parse_args()

    row_spec = None
    if args.rows:
        row_spec = [r.strip() for r in args.rows.split(",")]

    try:
        if args.filename_only:
            print(generate_filename(args.entity_class, args.variant))
        else:
            prompt = generate_prompt(args.entity_class, args.variant, row_spec)
            filename = generate_filename(args.entity_class, args.variant)
            print(f"# Suggested filename: {filename}\n")
            print(prompt)
        return 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
