"""Strict, offline validation and portable canonical JSON for SAT records.

Schemas describe structure. Cross-record meaning, scoring and analyst judgment
are deliberately owned by their respective engine stages.
"""

from __future__ import annotations

import base64
import binascii
from copy import deepcopy
from datetime import datetime
from functools import lru_cache
import hashlib
from importlib.resources import files
import json
import math
import re
from typing import Any
from urllib.parse import urlsplit

import rfc8785
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource, Unresolvable


SCHEMA_KINDS = (
    "observation", "hypothesis", "evidence", "timeline", "ach_matrix",
    "decision_card", "analytic_trace", "tasking_view", "doctrine",
    "analysis_request", "engine_result",
)


class ValidationFailure(ValueError):
    """A stable, machine-readable failure suitable for SDK and CLI callers."""

    def __init__(
        self, code: str, message: str, path: str = "$", remediation: str = ""
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.path = path
        self.remediation = remediation

    def diagnostic(self) -> dict[str, str]:
        return {
            "code": self.code,
            "path": self.path,
            "message": self.message,
            "severity": "error",
            "remediation": self.remediation,
        }


def _child_path(path: str, key: str | int) -> str:
    if isinstance(key, int):
        return f"{path}[{key}]"
    return f"{path}[{json.dumps(key, ensure_ascii=True)}]"


def _check_json_value(value: Any, path: str = "$", ancestors: set[int] | None = None) -> None:
    """Reject values outside JSON/I-JSON without coercing caller objects."""
    if value is None or type(value) is bool:
        return
    if type(value) is str:
        try:
            value.encode("utf-8", "strict")
        except UnicodeEncodeError as exc:
            raise ValidationFailure(
                "invalid_unicode", "JSON strings must not contain unpaired Unicode surrogates.",
                path, "Preserve invalid original bytes in raw_bytes_base64.",
            ) from exc
        return
    if type(value) is int:
        if not -(2**53 - 1) <= value <= 2**53 - 1:
            raise ValidationFailure(
                "nonportable_number", "Integer is outside the interoperable IEEE 754 safe integer range.",
                path, "Preserve exact larger integers as source text rather than silently rounding them.",
            )
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ValidationFailure("nonfinite_number", "JSON numbers must be finite.", path)
        return
    if type(value) not in (dict, list):
        raise ValidationFailure(
            "non_json_value", f"Value of type {type(value).__name__} is not a JSON value.", path,
            "Use only JSON objects, arrays, strings, finite numbers, booleans and null.",
        )
    ancestors = ancestors if ancestors is not None else set()
    identity = id(value)
    if identity in ancestors:
        raise ValidationFailure("non_json_value", "JSON values cannot contain cycles.", path)
    ancestors.add(identity)
    try:
        if isinstance(value, dict):
            for key, item in value.items():
                if type(key) is not str:
                    raise ValidationFailure("non_json_value", "JSON object keys must be strings.", path)
                child = _child_path(path, key)
                _check_json_value(key, child, ancestors)
                _check_json_value(item, child, ancestors)
        else:
            for index, item in enumerate(value):
                _check_json_value(item, _child_path(path, index), ancestors)
    finally:
        ancestors.remove(identity)


def loads_json(text: str | bytes | bytearray) -> Any:
    """Parse JSON, refusing duplicate names, nonfinite numbers and invalid Unicode."""
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValidationFailure(
                    "duplicate_key", f"Duplicate JSON object key: {key!r}.",
                    remediation="Supply each object key exactly once.",
                )
            result[key] = value
        return result

    def constant(token: str) -> Any:
        raise ValidationFailure("nonfinite_number", f"Nonfinite JSON constant {token!r} is forbidden.")

    try:
        result = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except ValidationFailure:
        raise
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError, RecursionError) as exc:
        raise ValidationFailure("invalid_json", f"Invalid JSON: {exc}.") from exc
    try:
        _check_json_value(result)
    except RecursionError as exc:
        raise ValidationFailure("invalid_json", "JSON nesting exceeds the supported depth.") from exc
    return result


def canonical_bytes(value: Any) -> bytes:
    """Serialize RFC 8785 JSON; never normalize strings or round large integers."""
    try:
        _check_json_value(value)
        return rfc8785.dumps(value)
    except ValidationFailure:
        raise
    except (rfc8785.CanonicalizationError, RecursionError) as exc:
        raise ValidationFailure("non_json_value", f"Value cannot be canonicalized: {exc}.") from exc


def content_hash(value: Any) -> str:
    """Return lowercase SHA-256 of the complete RFC 8785 serialization."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


_FORMAT_CHECKER = FormatChecker()


@_FORMAT_CHECKER.checks("uri", raises=ValueError)
def _is_uri(value: Any) -> bool:
    """Check absolute ASCII URI syntax without optional jsonschema extras."""
    if not isinstance(value, str):
        return True
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9+.-]*:[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+", value):
        return False
    if re.search(r"%(?![0-9A-Fa-f]{2})", value) or value.count("#") > 1:
        return False
    parts = urlsplit(value)
    if parts.scheme.lower() in {"http", "https"}:
        return bool(parts.hostname) and (parts.port is None or 0 <= parts.port <= 65535)
    return True


@_FORMAT_CHECKER.checks("date-time", raises=ValueError)
def _is_datetime(value: Any) -> bool:
    """Require RFC 3339 clock text with an explicit offset, never local time."""
    if not isinstance(value, str):
        return True
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt](?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]+)?(?:[Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])", value):
        return False
    resolved = datetime.fromisoformat(value.replace("t", "T").replace("z", "+00:00").replace("Z", "+00:00"))
    return resolved.tzinfo is not None


@_FORMAT_CHECKER.checks("base64", raises=(ValueError, binascii.Error))
def _is_base64(value: Any) -> bool:
    if not isinstance(value, str):
        return True
    decoded = base64.b64decode(value, validate=True)
    return base64.b64encode(decoded).decode("ascii") == value


def _deny_retrieval(uri: str) -> Resource[Any]:
    # No network/file retrieval is attempted, including for otherwise valid URIs.
    raise NoSuchResource(ref=uri)


@lru_cache(maxsize=1)
def _bundled_contracts() -> tuple[dict[str, dict[str, Any]], Registry[Any]]:
    schemas: dict[str, dict[str, Any]] = {}
    root = files("sat_engine").joinpath("resources", "schemas")
    for kind in SCHEMA_KINDS:
        schema = loads_json(root.joinpath(f"{kind}.v1.json").read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        schemas[kind] = schema
    registry: Registry[Any] = Registry(retrieve=_deny_retrieval).with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()
    )
    return schemas, registry


def load_schema(kind: str) -> dict[str, Any]:
    """Read a bundled schema, returning an independent copy for inspection."""
    if kind not in SCHEMA_KINDS:
        raise ValidationFailure("unknown_schema", f"Unknown schema kind: {kind!r}.", remediation=f"Use one of: {', '.join(SCHEMA_KINDS)}.")
    return deepcopy(_bundled_contracts()[0][kind])


def validate(kind: str, value: Any) -> None:
    """Validate structure and portability without changing or repairing input."""
    if kind not in SCHEMA_KINDS:
        raise ValidationFailure("unknown_schema", f"Unknown schema kind: {kind!r}.")
    canonical_bytes(value)
    schemas, registry = _bundled_contracts()
    validator = Draft202012Validator(schemas[kind], registry=registry, format_checker=_FORMAT_CHECKER)
    try:
        error = next(validator.iter_errors(value), None)
    except Unresolvable as exc:
        raise ValidationFailure("forbidden_schema_reference", "Schema reference is not bundled; external resolution is forbidden.") from exc
    if error is not None:
        path = "$"
        for component in error.absolute_path:
            path = _child_path(path, component)
        raise ValidationFailure(
            "schema_validation", error.message, path,
            f"Correct the value to match the bundled {kind} schema; do not replace unknowns with invented values.",
        )
