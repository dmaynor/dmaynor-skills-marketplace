#!/usr/bin/env python3
"""
Validate dual-plane isometric asset sheets for compliance.

Checks:
- Dimensions: 2048x2048
- Background color: #FF0000 (within tolerance)
- Grid: 6 rows × 5 columns with content in each cell
- No shadows (heuristic: no dark gradients at entity bases)

Usage:
    python validate_asset_sheet.py <image_path> [--strict] [--verbose]

Exit codes:
    0 = Valid
    1 = Invalid (violations found)
    2 = Error (file not found, etc.)
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from PIL import Image
    import numpy as np
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


# Grid specification
EXPECTED_WIDTH = 2048
EXPECTED_HEIGHT = 2048
GRID_ROWS = 6
GRID_COLS = 5
BACKGROUND_RGB = (255, 0, 0)  # #FF0000
COLOR_TOLERANCE = 10  # RGB channel tolerance for background detection
CELL_CONTENT_THRESHOLD = 0.05  # Minimum non-background ratio to consider cell populated
SHADOW_DARKNESS_THRESHOLD = 50  # RGB value below which pixels are "dark"
SHADOW_RATIO_THRESHOLD = 0.02  # Max ratio of dark pixels before flagging shadows


@dataclass
class ValidationResult:
    """Result of validation check."""

    valid: bool
    violations: list[str]
    warnings: list[str]
    metrics: dict


def check_dimensions(img: "Image.Image") -> tuple[bool, Optional[str]]:
    """Check image dimensions."""
    width, height = img.size
    if width != EXPECTED_WIDTH or height != EXPECTED_HEIGHT:
        return False, f"Dimensions {width}x{height}, expected {EXPECTED_WIDTH}x{EXPECTED_HEIGHT}"
    return True, None


def check_background_color(
    pixels: "np.ndarray",
    tolerance: int = COLOR_TOLERANCE,
) -> tuple[bool, Optional[str], float]:
    """
    Check that background is #FF0000.

    Returns (valid, message, background_ratio).
    """
    # Check each channel within tolerance of expected
    r_match = np.abs(pixels[:, :, 0].astype(int) - BACKGROUND_RGB[0]) <= tolerance
    g_match = np.abs(pixels[:, :, 1].astype(int) - BACKGROUND_RGB[1]) <= tolerance
    b_match = np.abs(pixels[:, :, 2].astype(int) - BACKGROUND_RGB[2]) <= tolerance

    background_mask = r_match & g_match & b_match
    background_ratio = np.mean(background_mask)

    # Background should be at least 30% of image (accounting for assets)
    if background_ratio < 0.30:
        return (
            False,
            f"Background color ratio {background_ratio:.1%}, expected ≥30% #FF0000",
            background_ratio,
        )
    return True, None, background_ratio


def check_grid_cells(
    pixels: "np.ndarray",
    tolerance: int = COLOR_TOLERANCE,
) -> tuple[bool, list[str], dict[tuple[int, int], float]]:
    """
    Check that each grid cell contains content (non-background pixels).

    Returns (valid, messages, cell_content_ratios).
    """
    height, width = pixels.shape[:2]
    cell_height = height // GRID_ROWS
    cell_width = width // GRID_COLS

    # Background mask
    r_match = np.abs(pixels[:, :, 0].astype(int) - BACKGROUND_RGB[0]) <= tolerance
    g_match = np.abs(pixels[:, :, 1].astype(int) - BACKGROUND_RGB[1]) <= tolerance
    b_match = np.abs(pixels[:, :, 2].astype(int) - BACKGROUND_RGB[2]) <= tolerance
    background_mask = r_match & g_match & b_match

    violations = []
    cell_ratios = {}

    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            y_start = row * cell_height
            y_end = (row + 1) * cell_height
            x_start = col * cell_width
            x_end = (col + 1) * cell_width

            cell_bg = background_mask[y_start:y_end, x_start:x_end]
            content_ratio = 1.0 - np.mean(cell_bg)
            cell_ratios[(row, col)] = content_ratio

            if content_ratio < CELL_CONTENT_THRESHOLD:
                violations.append(
                    f"Cell ({row}, {col}) appears empty (content ratio {content_ratio:.1%})"
                )

    return len(violations) == 0, violations, cell_ratios


def check_shadows(
    pixels: "np.ndarray",
) -> tuple[bool, Optional[str], float]:
    """
    Heuristic shadow detection: look for dark pixels that shouldn't exist
    in a flat-lit, no-shadow asset sheet.

    Returns (valid, message, dark_pixel_ratio).
    """
    # Convert to grayscale-ish (simple average)
    gray = np.mean(pixels[:, :, :3], axis=2)

    # Find very dark pixels (potential shadows)
    dark_mask = gray < SHADOW_DARKNESS_THRESHOLD

    # Exclude background (which is red, not dark)
    r_match = np.abs(pixels[:, :, 0].astype(int) - BACKGROUND_RGB[0]) <= COLOR_TOLERANCE
    g_match = np.abs(pixels[:, :, 1].astype(int) - BACKGROUND_RGB[1]) <= COLOR_TOLERANCE
    b_match = np.abs(pixels[:, :, 2].astype(int) - BACKGROUND_RGB[2]) <= COLOR_TOLERANCE
    background_mask = r_match & g_match & b_match

    # Dark pixels that are NOT background
    shadow_candidates = dark_mask & ~background_mask
    shadow_ratio = np.mean(shadow_candidates)

    if shadow_ratio > SHADOW_RATIO_THRESHOLD:
        return (
            False,
            f"Potential shadows detected: {shadow_ratio:.1%} dark pixels (threshold {SHADOW_RATIO_THRESHOLD:.1%})",
            shadow_ratio,
        )
    return True, None, shadow_ratio


def validate_asset_sheet(
    image_path: Path,
    strict: bool = False,
    verbose: bool = False,
) -> ValidationResult:
    """
    Validate an asset sheet image.

    Args:
        image_path: Path to the image file
        strict: If True, warnings become violations
        verbose: If True, include detailed metrics

    Returns:
        ValidationResult with validity status, violations, and metrics
    """
    violations = []
    warnings = []
    metrics = {}

    # Load image
    try:
        img = Image.open(image_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        pixels = np.array(img)
    except Exception as e:
        return ValidationResult(
            valid=False,
            violations=[f"Failed to load image: {e}"],
            warnings=[],
            metrics={},
        )

    # Check dimensions
    dim_valid, dim_msg = check_dimensions(img)
    if not dim_valid:
        violations.append(dim_msg)
    metrics["dimensions"] = img.size

    # Check background color
    bg_valid, bg_msg, bg_ratio = check_background_color(pixels)
    if not bg_valid:
        violations.append(bg_msg)
    metrics["background_ratio"] = bg_ratio

    # Check grid cells
    grid_valid, grid_msgs, cell_ratios = check_grid_cells(pixels)
    if not grid_valid:
        if strict:
            violations.extend(grid_msgs)
        else:
            warnings.extend(grid_msgs)
    metrics["cell_content_ratios"] = cell_ratios

    # Check shadows
    shadow_valid, shadow_msg, shadow_ratio = check_shadows(pixels)
    if not shadow_valid:
        if strict:
            violations.append(shadow_msg)
        else:
            warnings.append(shadow_msg)
    metrics["shadow_ratio"] = shadow_ratio

    return ValidationResult(
        valid=len(violations) == 0,
        violations=violations,
        warnings=warnings,
        metrics=metrics if verbose else {},
    )


def main() -> int:
    """CLI entry point."""
    if not HAS_DEPS:
        print(
            "Error: Required dependencies not installed. Run:\n"
            "  pip install pillow numpy --break-system-packages",
            file=sys.stderr,
        )
        return 2

    parser = argparse.ArgumentParser(
        description="Validate dual-plane isometric asset sheets",
    )
    parser.add_argument(
        "image_path",
        type=Path,
        help="Path to asset sheet image",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as violations",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed metrics",
    )

    args = parser.parse_args()

    if not args.image_path.exists():
        print(f"Error: File not found: {args.image_path}", file=sys.stderr)
        return 2

    result = validate_asset_sheet(args.image_path, args.strict, args.verbose)

    # Output
    if result.valid:
        print(f"✅ VALID: {args.image_path}")
    else:
        print(f"❌ INVALID: {args.image_path}")

    if result.violations:
        print("\nViolations:")
        for v in result.violations:
            print(f"  - {v}")

    if result.warnings:
        print("\nWarnings:")
        for w in result.warnings:
            print(f"  - {w}")

    if result.metrics:
        print("\nMetrics:")
        for k, v in result.metrics.items():
            if k == "cell_content_ratios":
                print(f"  {k}:")
                for cell, ratio in sorted(v.items()):
                    print(f"    ({cell[0]}, {cell[1]}): {ratio:.1%}")
            else:
                print(f"  {k}: {v}")

    return 0 if result.valid else 1


if __name__ == "__main__":
    sys.exit(main())
