#!/usr/bin/env python3
"""Build reported-clock timelines without inventing timezone or year context."""

from __future__ import annotations

import argparse
import html
import json
import math
import re
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _threshold(value: float, name: str) -> float:
    """Validate thresholds without accepting booleans or truncating fractions."""
    if type(value) not in (int, float):
        raise ValueError(f"{name} threshold must be finite and nonnegative")
    try:
        valid = math.isfinite(value) and value >= 0
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"{name} threshold must be finite and nonnegative")
    if type(value) is int and value > 2**53 - 1:
        raise ValueError(f"{name} threshold exceeds interoperable JSON integer range")
    return value


def _markdown(value: object) -> str:
    """Escape untrusted text for a Markdown table cell or paragraph."""
    text = html.escape(str(value), quote=False).replace("\\", "\\\\")
    for char in "|`*_[]{}":
        text = text.replace(char, "\\" + char)
    return text.replace("\r", "\\r").replace("\n", "\\n").encode("utf-8", errors="backslashreplace").decode("utf-8")


def _timezone(value: str | tzinfo) -> tzinfo:
    """Resolve explicit UTC, numeric offset, or IANA timezone context."""
    if isinstance(value, tzinfo):
        return value
    if value in {"UTC", "Z", "+00:00"}:
        return UTC
    match = re.fullmatch(r"([+-])(\d{2}):?(\d{2})", value)
    if match:
        hours, minutes = int(match[2]), int(match[3])
        if hours > 23 or minutes > 59:
            raise ValueError("invalid timezone offset")
        offset = timedelta(hours=hours, minutes=minutes)
        return timezone(offset if match[1] == "+" else -offset)
    try:
        return ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"unknown timezone context: {value}") from exc


def resolve_timestamp(
    ts: str | None,
    *,
    default_year: int | None = None,
    default_timezone: str | tzinfo | None = None,
    fold: int | None = None,
) -> tuple[datetime | None, str | None]:
    """Return aware UTC or an explicit unresolved reason.

    Numeric epochs have no implicit unit. Local times in a DST overlap require
    an explicit fold (0 or 1); nonexistent local times remain unresolved.
    """
    if not isinstance(ts, str) or not ts.strip() or ts == "unknown":
        return None, "missing timestamp"
    if default_year is not None and (type(default_year) is not int or not 1 <= default_year <= 9999):
        return None, "year context must be an integer from 1 through 9999"
    if fold is not None and (type(fold) is not int or fold not in (0, 1)):
        return None, "fold context must be 0 or 1"
    text = ts.strip()
    parsed: datetime | None = None
    # Require a date and clock time; fromisoformat alone accepts date-only input.
    if re.match(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}", text):
        fraction = re.match(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[.,](\d+)", text)
        if fraction and len(fraction[1]) > 6 and any(digit != "0" for digit in fraction[1][6:]):
            return None, "timestamp precision exceeds supported microseconds; no rounding applied"
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            pass
    if parsed is None:
        try:
            parsed = datetime.strptime(text, "%d/%b/%Y:%H:%M:%S %z")
        except ValueError:
            pass
    if parsed is None and re.fullmatch(r"[A-Za-z]{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}", text):
        if default_year is None:
            return None, "timestamp has no year; explicit year context required"
        try:
            parsed = datetime.strptime(f"{default_year} {text}", "%Y %b %d %H:%M:%S")
        except ValueError:
            return None, "invalid calendar timestamp"
    if parsed is None:
        return None, "unsupported or invalid timestamp; no unit or calendar context inferred"
    if parsed.tzinfo is None:
        if default_timezone is None:
            return None, "timestamp has no timezone; explicit timezone context required"
        try:
            zone = _timezone(default_timezone)
            candidates = []
            for candidate_fold in (0, 1):
                candidate = parsed.replace(tzinfo=zone, fold=candidate_fold)
                if candidate.astimezone(UTC).astimezone(zone).replace(tzinfo=None) == parsed:
                    candidates.append(candidate)
            if not candidates:
                return None, "local timestamp does not exist in the supplied timezone"
            if len({candidate.utcoffset() for candidate in candidates}) > 1 and fold is None:
                return None, "local timestamp is ambiguous; explicit fold context required"
            parsed = parsed.replace(tzinfo=zone, fold=fold or 0)
        except (ValueError, TypeError, OverflowError) as exc:
            return None, str(exc)
    try:
        return parsed.astimezone(UTC), None
    except (ValueError, OverflowError) as exc:
        return None, str(exc)


def parse_timestamp(
    ts: str | None,
    *,
    default_year: int | None = None,
    default_timezone: str | tzinfo | None = None,
    fold: int | None = None,
) -> datetime | None:
    """Parse to aware UTC; return None when timestamp context is unresolved."""
    return resolve_timestamp(ts, default_year=default_year, default_timezone=default_timezone, fold=fold)[0]


@dataclass
class TimelineEvent:
    """A source assertion and its explicitly resolved reported-clock time."""

    timestamp: str | None
    observation_id: str
    description: str
    source: str = ""
    actor: str | None = None
    target: str | None = None
    tags: list[str] = field(default_factory=list)
    _dt: datetime | None = field(default=None, repr=False)
    timestamp_context: dict[str, Any] = field(default_factory=dict)
    timestamp_resolution_error: str | None = None
    timestamp_semantics: str = "unknown"
    clock_domain: str | None = None
    timestamp_uncertainty_seconds: float | None = None
    parse_status: str = "unparsed"
    raw: str = ""
    source_id: str | None = None
    line_number: int | None = None
    record_sha256: str | None = None
    origin_id: str | None = None
    dependency_groups: list[str] = field(default_factory=list)
    parse_error: str | None = None
    raw_bytes_base64: str | None = None
    parser: str = "unknown"
    address_mentions: list[str] = field(default_factory=list)
    reliability: str = "unknown"
    reliability_reason: str | None = None


class Timeline:
    """A timeline that retains unresolved events outside duration arithmetic."""

    def __init__(self, *, gap_threshold_seconds: float = 300, rapid_threshold_seconds: float = 5) -> None:
        # Five seconds is retained only as the legacy helper's default. The
        # build_timeline engine API uses its contract's one-second default.
        self.gap_threshold_seconds = _threshold(gap_threshold_seconds, "gap")
        self.rapid_threshold_seconds = _threshold(rapid_threshold_seconds, "rapid")
        self.events: list[TimelineEvent] = []

    def add_event(
        self,
        timestamp: str | None,
        observation_id: str,
        description: str,
        source: str = "",
        actor: str | None = None,
        target: str | None = None,
        tags: list[str] | None = None,
        *,
        timestamp_context: dict[str, Any] | None = None,
        timestamp_semantics: str = "unknown",
        clock_domain: str | None = None,
        timestamp_uncertainty_seconds: float | None = None,
        parse_status: str = "unparsed",
        raw: str = "",
        source_id: str | None = None,
        line_number: int | None = None,
        record_sha256: str | None = None,
        origin_id: str | None = None,
        dependency_groups: list[str] | None = None,
        parse_error: str | None = None,
        raw_bytes_base64: str | None = None,
        parser: str = "unknown",
        address_mentions: list[str] | None = None,
        reliability: str = "unknown",
        reliability_reason: str | None = None,
    ) -> TimelineEvent:
        """Add an event; no missing calendar, zone, or uncertainty is invented."""
        for name, value in (("description", description), ("source", source), ("raw", raw),
                            ("timestamp_semantics", timestamp_semantics), ("parser", parser)):
            if not isinstance(value, str):
                raise ValueError(f"{name} must be a string")
        for name, value in (("timestamp", timestamp), ("actor", actor), ("target", target),
                            ("clock_domain", clock_domain), ("source_id", source_id),
                            ("origin_id", origin_id), ("parse_error", parse_error),
                            ("record_sha256", record_sha256), ("raw_bytes_base64", raw_bytes_base64),
                            ("reliability_reason", reliability_reason)):
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{name} must be a string or null")
        for name, value in (("tags", tags), ("dependency_groups", dependency_groups),
                            ("address_mentions", address_mentions)):
            if value is not None and (not isinstance(value, list) or any(not isinstance(item, str) for item in value)):
                raise ValueError(f"{name} must be an array of strings or null")
        if not isinstance(parse_status, str) or parse_status not in {"parsed", "unparsed", "rejected"}:
            raise ValueError("parse_status must be parsed, unparsed, or rejected")
        if not isinstance(reliability, str) or reliability not in {"A", "B", "C", "D", "E", "F", "unknown"}:
            raise ValueError("reliability must be A, B, C, D, E, F, or unknown")
        if timestamp_context is not None and not isinstance(timestamp_context, dict):
            raise ValueError("timestamp_context must be an object or null")
        if line_number is not None and (type(line_number) is not int or line_number < 1):
            raise ValueError("line_number must be a positive integer or null")
        if not isinstance(observation_id, str) or not observation_id.strip():
            raise ValueError("observation_id must be a nonempty string")
        if any(event.observation_id == observation_id for event in self.events):
            raise ValueError(f"duplicate observation_id: {observation_id}")
        if timestamp_uncertainty_seconds is not None and (
            type(timestamp_uncertainty_seconds) not in (int, float)
            or not math.isfinite(timestamp_uncertainty_seconds)
            or timestamp_uncertainty_seconds < 0
        ):
            raise ValueError("timestamp uncertainty must be finite and nonnegative, or null")
        context = deepcopy(timestamp_context or {})
        dt, error = resolve_timestamp(timestamp, default_year=context.get("year"),
                                      default_timezone=context.get("timezone"), fold=context.get("fold"))
        event = TimelineEvent(
            timestamp, observation_id, description, source, actor, target,
            list(tags or []), dt, context, error, timestamp_semantics, clock_domain,
            timestamp_uncertainty_seconds, parse_status, raw, source_id, line_number,
            record_sha256, origin_id, list(dependency_groups or []), parse_error,
            raw_bytes_base64, parser, list(address_mentions or []), reliability, reliability_reason,
        )
        self.events.append(event)
        return event

    def sort(self) -> None:
        """Sort resolved events by UTC and retain unresolved events afterward."""
        resolved = sorted((e for e in self.events if e._dt is not None), key=lambda e: (e._dt, e.observation_id))
        self.events = resolved + [e for e in self.events if e._dt is None]

    def get_time_range(self) -> tuple[str | None, str | None]:
        """Return normalized UTC endpoints from resolved events only."""
        self.sort()
        resolved = [e._dt for e in self.events if e._dt is not None]
        return (resolved[0].isoformat(), resolved[-1].isoformat()) if resolved else (None, None)

    def get_gaps(self, threshold_seconds: float | None = None) -> list[tuple[TimelineEvent, TimelineEvent, float]]:
        """Return reported-clock gaps, never a proof of physical inactivity."""
        threshold_seconds = self.gap_threshold_seconds if threshold_seconds is None else _threshold(threshold_seconds, "gap")
        self.sort()
        resolved = [event for event in self.events if event._dt is not None]
        gaps = []
        for first, second in zip(resolved, resolved[1:]):
            assert first._dt is not None and second._dt is not None
            delta = (second._dt - first._dt).total_seconds()
            if delta > threshold_seconds:
                gaps.append((first, second, delta))
        return gaps

    def filter_by_actor(self, actor: str) -> Timeline:
        """Return a timeline view containing only the requested actor."""
        result = Timeline(gap_threshold_seconds=self.gap_threshold_seconds, rapid_threshold_seconds=self.rapid_threshold_seconds)
        result.events = [e for e in self.events if e.actor == actor]
        return result

    def filter_by_tag(self, tag: str) -> Timeline:
        """Return a timeline view containing only the requested tag."""
        result = Timeline(gap_threshold_seconds=self.gap_threshold_seconds, rapid_threshold_seconds=self.rapid_threshold_seconds)
        result.events = [e for e in self.events if tag in e.tags]
        return result

    @staticmethod
    def _interval(first: TimelineEvent, second: TimelineEvent, delta: float) -> dict[str, Any]:
        """Describe interval provenance and avoid implying synchronized clocks."""
        uncertainty = None
        if first.timestamp_uncertainty_seconds is not None and second.timestamp_uncertainty_seconds is not None:
            uncertainty = first.timestamp_uncertainty_seconds + second.timestamp_uncertainty_seconds
            if not math.isfinite(uncertainty):
                uncertainty = None
        return {
            "event1": first.observation_id, "event2": second.observation_id,
            "delta_seconds": delta, "kind": "reported_clock_interval",
            "same_known_clock_domain": bool(first.clock_domain and first.clock_domain == second.clock_domain),
            "combined_timestamp_uncertainty_seconds": uncertainty,
            "physical_latency_established": False,
        }

    def analyze_sequences(self) -> dict[str, Any]:
        """Describe reported order, unresolved coverage, and clock limitations."""
        self.sort()
        actors: dict[str, dict[str, Any]] = {}
        resolved = [e for e in self.events if e._dt is not None]
        for event in self.events:
            if event.actor:
                actor = actors.setdefault(event.actor, {"count": 0, "first": None, "last": None, "unresolved": 0})
                actor["count"] += 1
                if event._dt is None:
                    actor["unresolved"] += 1
                else:
                    actor["first"] = actor["first"] or event._dt.isoformat()
                    actor["last"] = event._dt.isoformat()
        rapid = []
        for first, second in zip(resolved, resolved[1:]):
            assert first._dt is not None and second._dt is not None
            delta = (second._dt - first._dt).total_seconds()
            if 0 < delta <= self.rapid_threshold_seconds:
                rapid.append(self._interval(first, second, delta))
        caveats = [
            "Source timestamps are source assertions; reported-clock intervals do not establish physical latency or causation.",
            "Collection completeness is not established; a reported-clock gap is not evidence that no event occurred.",
        ]
        if len(resolved) != len(self.events):
            caveats.append("Unresolved timestamps are retained and excluded from endpoints and duration arithmetic.")
        if any(e.clock_domain is None for e in self.events):
            caveats.append("At least one clock domain is unknown; cross-clock synchronization is not established.")
        if any(e.timestamp_uncertainty_seconds is None for e in self.events):
            caveats.append("At least one timestamp uncertainty is unknown, not zero.")
        if any(first.timestamp_uncertainty_seconds is not None
               and second.timestamp_uncertainty_seconds is not None
               and not math.isfinite(first.timestamp_uncertainty_seconds + second.timestamp_uncertainty_seconds)
               for first, second in zip(resolved, resolved[1:])):
            caveats.append("At least one combined timestamp uncertainty exceeds the finite numeric range and is reported as null.")
        if any(e.timestamp_semantics == "unknown" for e in self.events):
            caveats.append("At least one timestamp's event meaning is unknown.")
        first, last = self.get_time_range()
        return {
            "total_events": len(self.events), "resolved_events": len(resolved),
            "unresolved_events": len(self.events) - len(resolved),
            "parse_counts": {status: sum(e.parse_status == status for e in self.events) for status in ("parsed", "unparsed", "rejected")},
            "time_range": {"first": first, "last": last}, "actors": actors,
            "tag_sequences": [], "rapid_succession": rapid,
            "gaps": [self._interval(a, b, d) for a, b, d in self.get_gaps()], "caveats": caveats,
        }

    def to_json_dict(self) -> dict[str, Any]:
        """Return a JSON-ready envelope including every unresolved event."""
        self.sort()
        events = []
        for event in self.events:
            record = asdict(event)
            dt = record.pop("_dt")
            record["timestamp_utc"] = dt.isoformat() if dt is not None else None
            events.append(record)
        return {"events": events, "analysis": self.analyze_sequences()}

    def to_markdown(self, include_gaps: bool = True) -> str:
        """Render escaped observations and explicit time-resolution limits."""
        self.sort()
        lines = ["## Event Timeline", "", "| Source time | UTC / unresolved reason | ID | Event | Actor | Source |", "|---|---|---|---|---|---|"]
        for event in self.events:
            resolved = event._dt.isoformat() if event._dt else f"Unresolved: {event.timestamp_resolution_error}"
            values = (event.timestamp or "missing", resolved, event.observation_id, event.description, event.actor or "-", event.source)
            lines.append("| " + " | ".join(_markdown(value) for value in values) + " |")
        if include_gaps:
            gaps = self.get_gaps()
            if gaps:
                lines.extend(["", "### Reported-clock gaps", ""])
                for first, second, delta in gaps:
                    lines.append(f"- {delta:.1f} seconds between {_markdown(first.observation_id)} and {_markdown(second.observation_id)}.")
        lines.extend(["", "### Limits", ""])
        lines.extend(f"- {_markdown(caveat)}" for caveat in self.analyze_sequences()["caveats"])
        return "\n".join(lines)

    def to_ascii_timeline(self, max_width: int = 80) -> str:
        """Retain legacy entrypoint as a plain-text list, with safe control text."""
        self.sort()
        if not self.events:
            return "No events in timeline."
        return "\n".join(
            f"{_markdown(e.timestamp or 'missing')} [{_markdown(e.observation_id)}] {_markdown(e.description)[:max_width]}"
            for e in self.events
        )


def from_observations_json(
    data: list[dict[str, Any]] | dict[str, Any], *,
    default_year: int | None = None, default_timezone: str | None = None, fold: int | None = None,
    gap_threshold_seconds: float = 300, rapid_threshold_seconds: float = 5,
) -> Timeline:
    """Read a legacy observation list or parser envelope, preserving each row."""
    if isinstance(data, dict):
        data = data.get("entries", data.get("observations"))
    if not isinstance(data, list):
        raise ValueError("expected an observation list or an entries/observations envelope")
    timeline = Timeline(gap_threshold_seconds=gap_threshold_seconds, rapid_threshold_seconds=rapid_threshold_seconds)
    for index, obs in enumerate(data, 1):
        if not isinstance(obs, dict):
            raise ValueError(f"observation {index} is not an object")
        context = {key: value for key, value in (("year", default_year), ("timezone", default_timezone), ("fold", fold)) if value is not None}
        supplied_context = obs.get("timestamp_context", {})
        if not isinstance(supplied_context, dict):
            raise ValueError(f"observation {index} timestamp_context is not an object")
        context.update(supplied_context)
        observation_id = obs.get("observation_id", obs.get("id"))
        if observation_id is None:
            raise ValueError(f"observation {index} has no observation_id")
        timeline.add_event(
            timestamp=obs.get("timestamp"), observation_id=observation_id,
            description=obs.get("description") or obs.get("message") or obs.get("raw") or "",
            source=obs.get("source", ""), actor=obs.get("actor", obs.get("user")),
            target=obs.get("target"), tags=obs.get("tags", []), timestamp_context=context,
            **{key: obs[key] for key in ("timestamp_semantics", "clock_domain", "timestamp_uncertainty_seconds", "parse_status", "raw", "source_id", "line_number", "record_sha256", "origin_id", "dependency_groups", "parse_error", "raw_bytes_base64", "parser", "address_mentions", "reliability", "reliability_reason") if key in obs},
        )
    return timeline


def build_timeline(
    observations: list[dict[str, Any]],
    *,
    gap_threshold_seconds: float = 300,
    rapid_threshold_seconds: float = 1,
    default_year: int | None = None,
    default_timezone: str | None = None,
    fold: int | None = None,
) -> dict[str, Any]:
    """Build a versioned timeline without changing source time or provenance.

    Only explicitly resolved reported clocks enter interval arithmetic. Gap
    threshold comparison is strict (>); rapid succession uses (0, threshold].
    Simultaneous reported times do not establish succession. Unresolved events
    remain visible after resolved events in their original supplied order.
    """
    from .validators import validate

    if not isinstance(observations, list):
        raise ValueError("observations must be an array")
    for index, observation in enumerate(observations, 1):
        if not isinstance(observation, dict) or "id" not in observation:
            raise ValueError(f"observation {index} must be an object with an id")
        if "observation_id" in observation:
            raise ValueError(f"observation {index} uses legacy observation_id; the engine requires id")
        validate("observation", observation)
    if default_year is not None and (type(default_year) is not int or not 1 <= default_year <= 9999):
        raise ValueError("year context must be an integer from 1 through 9999")
    if default_timezone is not None and (not isinstance(default_timezone, str) or not default_timezone.strip()):
        raise ValueError("timezone context must be a nonempty string")
    if fold is not None and (type(fold) is not int or fold not in (0, 1)):
        raise ValueError("fold context must be 0 or 1")
    timeline = from_observations_json(
        observations, default_year=default_year, default_timezone=default_timezone,
        fold=fold, gap_threshold_seconds=gap_threshold_seconds,
        rapid_threshold_seconds=rapid_threshold_seconds,
    )
    result = timeline.to_json_dict()
    result["schema_version"] = "1"
    result["gap_threshold_seconds"] = timeline.gap_threshold_seconds
    result["rapid_threshold_seconds"] = timeline.rapid_threshold_seconds
    for event in result["events"]:
        event["id"] = event.pop("observation_id")
    validate("timeline", result)
    return result


def main() -> None:
    """Build a Markdown or JSON timeline with explicit optional time context."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observations", type=Path)
    parser.add_argument("--output-format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--json", action="store_true", help="alias for --output-format json")
    parser.add_argument("--year", type=int, help="explicit year for yearless source timestamps")
    parser.add_argument("--timezone", help="explicit timezone for unzoned source timestamps")
    parser.add_argument("--fold", type=int, choices=(0, 1), help="explicit DST overlap selection")
    parser.add_argument("--gap-threshold-seconds", type=float, default=300)
    parser.add_argument("--rapid-threshold-seconds", type=float, default=5,
                        help="reported-clock rapid threshold (legacy default: 5 seconds)")
    args = parser.parse_args()
    try:
        def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            """Reject repeated keys before JSON decoding can overwrite evidence."""
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError(f"duplicate JSON field: {key}")
                result[key] = value
            return result

        def invalid_constant(value: str) -> None:
            """Reject non-finite JSON extensions rather than storing ambiguity."""
            raise ValueError(f"non-finite JSON constant: {value}")

        data = json.loads(args.observations.read_text(encoding="utf-8"),
                          object_pairs_hook=unique_object, parse_constant=invalid_constant)
        timeline = from_observations_json(data, default_year=args.year, default_timezone=args.timezone, fold=args.fold,
                                          gap_threshold_seconds=args.gap_threshold_seconds,
                                          rapid_threshold_seconds=args.rapid_threshold_seconds)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    print(json.dumps(timeline.to_json_dict(), ensure_ascii=True, indent=2, allow_nan=False) if args.json or args.output_format == "json" else timeline.to_markdown())


if __name__ == "__main__":
    main()
