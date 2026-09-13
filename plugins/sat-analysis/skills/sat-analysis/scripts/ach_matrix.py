#!/usr/bin/env python3
"""Compatibility entrypoint for the corrected ACH helper, now in sat_engine.ach."""

from __future__ import annotations

import sys
from pathlib import Path

# Support direct source-checkout execution as well as installed package imports.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sat_engine.ach import (  # noqa: E402,F401
    ACHMatrix, Assessment, Evidence, Hypothesis, PROBABILITY_TOLERANCE,
    RATINGS, RATING_VALUES, RELATIONSHIPS, compute_matrix, create_empty_matrix,
    from_json, interactive_rating, main,
)


if __name__ == "__main__":
    raise SystemExit(main())
