"""SAT reference engine with explicit analyst inputs and portable contracts.

Public APIs load lazily so legacy parsing and ACH helpers remain usable without
loading optional schema dependencies merely by importing the package.
"""

from importlib import import_module
from typing import Any

__version__ = "1.1.0"
__all__ = ["assess", "verify_artifacts", "ingest_file", "ingest_text", "validate",
           "ValidationFailure", "__version__"]
_EXPORTS = {"assess": "pipeline", "verify_artifacts": "pipeline",
            "ingest_file": "parsers", "ingest_text": "parsers",
            "validate": "validators", "ValidationFailure": "validators"}


def __getattr__(name: str) -> Any:
    """Load a documented SDK entrypoint on first use."""
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(f".{_EXPORTS[name]}", __name__), name)
    globals()[name] = value
    return value
