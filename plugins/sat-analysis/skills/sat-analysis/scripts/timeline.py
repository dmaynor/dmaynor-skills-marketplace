#!/usr/bin/env python3
"""Compatibility entrypoint; implementation lives in sat_engine.timeline."""

from __future__ import annotations

import sys
from pathlib import Path

# Source-checkout scripts work without installation; installed imports also work.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sat_engine import timeline as _implementation

if __name__ == "__main__":
    _implementation.main()
else:
    # Keep legacy module patching and callable/dataclass imports compatible.
    sys.modules[__name__] = _implementation
