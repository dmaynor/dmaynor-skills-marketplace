#!/usr/bin/env python3
"""Extract source assertions while retaining every nonblank physical log record.

Supported structures: syslog, SSH/sudo messages, combined web access logs,
JSON objects, and a simple Windows event text layout. Unknown text is unparsed;
malformed recognized structures are rejected without discarding their raw bytes.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import ipaddress
import io
import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, BinaryIO, Iterator

from .timeline import resolve_timestamp


@dataclass
class LogEntry:
    """Extracted fields remain assertions made by the preserved source record."""

    timestamp: str | None = None
    source: str = ""
    raw: str = ""
    host: str | None = None
    process: str | None = None
    pid: int | None = None
    user: str | None = None
    src_ip: str | None = None
    dst_ip: str | None = None
    src_port: int | None = None
    dst_port: int | None = None
    action: str | None = None
    status: str | None = None
    message: str | None = None
    observation_id: str | None = None
    tags: list[str] = field(default_factory=list)
    source_id: str = ""
    line_number: int | None = None
    record_sha256: str = ""
    parse_status: str = "unparsed"
    parse_error: str | None = None
    parser: str = "generic_text"
    address_mentions: list[str] = field(default_factory=list)
    origin_id: str | None = None
    dependency_groups: list[str] = field(default_factory=list)
    timestamp_semantics: str = "unknown"
    clock_domain: str | None = None
    timestamp_uncertainty_seconds: float | None = None
    timestamp_context: dict[str, str | int] = field(default_factory=dict)
    raw_bytes_base64: str | None = None
    reliability: str = "unknown"
    reliability_reason: str | None = None


PATTERNS = {
    "syslog": re.compile(r"^(?P<timestamp>[A-Za-z]{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(?P<host>\S+)\s+(?P<process>\S+?)(?:\[(?P<pid>\d+)\])?:\s*(?P<message>.*)$"),
    "syslog_iso": re.compile(r"^(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+(?P<host>\S+)\s+(?P<process>\S+?)(?:\[(?P<pid>\d+)\])?:\s*(?P<message>.*)$"),
    "auth_ssh_fail": re.compile(r"^Failed (?:password|publickey) for (?:invalid user )?(?P<user>\S+) from (?P<src_ip>\S+) port (?P<src_port>\d+)(?:\s|$)"),
    "auth_ssh_success": re.compile(r"^Accepted (?:password|publickey) for (?P<user>\S+) from (?P<src_ip>\S+) port (?P<src_port>\d+)(?:\s|$)"),
    "auth_sudo": re.compile(r"^(?P<user>\S+)\s*:\s*TTY=\S+\s*;\s*PWD=\S+\s*;\s*USER=(?P<target_user>\S+)\s*;\s*COMMAND=(?P<command>.*)$"),
    "apache_combined": re.compile(r'^(?P<src_ip>\S+)\s+\S+\s+(?P<user>\S+)\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>\S+)\s+(?P<path>\S+)\s+(?P<protocol>[^"\r\n]+)"\s+(?P<status>\d{3})\s+(?P<bytes>\d+|-)\s+"(?P<referer>[^"\r\n]*)"\s+"(?P<user_agent>[^"\r\n]*)"\s*$'),
    "windows_event": re.compile(r"^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(?P<level>\w+)\s+(?P<process>\S+)\s+(?P<event_id>\d+)\s+(?P<message>.*)$"),
}
PATTERNS["nginx_combined"] = PATTERNS["apache_combined"]


def _address_mentions(text: str) -> list[str]:
    """Extract valid address literals without assigning network roles."""
    mentions = set()
    for candidate in re.findall(r"[0-9A-Fa-f:.%]+", text):
        try:
            mentions.add(str(ipaddress.ip_address(candidate.strip("."))))
        except ValueError:
            continue
    return sorted(mentions)


def _entry(line: str, source: str, parser: str = "generic_text") -> LogEntry:
    """Create a byte-bound record; file parsing adds the physical line number."""
    raw_bytes = line.encode("utf-8", errors="surrogateescape")
    digest = hashlib.sha256(raw_bytes).hexdigest()
    source_id = "src-" + hashlib.sha256(source.encode("utf-8", errors="surrogateescape")).hexdigest()[:20]
    return LogEntry(source=source, raw=line, message=line.rstrip("\r\n"), parser=parser,
                    record_sha256=digest, source_id=source_id,
                    observation_id=f"{source_id}:record:{digest[:20]}",
                    address_mentions=_address_mentions(line))


def _reject(entry: LogEntry, error: str) -> LogEntry:
    """Retain the record and describe why structure or field extraction failed."""
    entry.parse_status = "rejected"
    entry.parse_error = error
    return entry


def _port(text: object) -> int:
    """Validate a source-asserted network port without truncating values."""
    if isinstance(text, bool) or not isinstance(text, (int, str)):
        raise ValueError("port must be an integer or decimal string")
    if isinstance(text, str) and not text.isdecimal():
        raise ValueError("port must be decimal")
    value = int(text)
    if not 0 <= value <= 65535:
        raise ValueError("port outside 0..65535")
    return value


def _finish_addresses(entry: LogEntry) -> LogEntry:
    """Leave only unassigned address literals in address_mentions."""
    entry.address_mentions = [address for address in entry.address_mentions if address not in {entry.src_ip, entry.dst_ip}]
    return entry


def parse_syslog_line(line: str, source: str = "syslog") -> LogEntry:
    """Parse known syslog structure; generic text never gains an IP role."""
    entry = _entry(line, source)
    for pattern_name in ("syslog_iso", "syslog"):
        match = PATTERNS[pattern_name].fullmatch(line.rstrip("\r\n"))
        if match:
            fields = match.groupdict()
            entry.timestamp, entry.host, entry.process = fields["timestamp"], fields["host"], fields["process"]
            entry.message = fields["message"]
            entry.parser, entry.parse_status = pattern_name, "parsed"
            try:
                entry.pid = int(fields["pid"]) if fields["pid"] else None
            except ValueError as exc:
                return _reject(entry, f"invalid syslog PID: {exc}")
            break
    if entry.parse_status != "parsed":
        return entry
    if entry.process == "sshd":
        for pattern, action, status in (("auth_ssh_fail", "ssh_auth_fail", "failure"), ("auth_ssh_success", "ssh_auth_success", "success")):
            match = PATTERNS[pattern].match(entry.message or "")
            if match:
                try:
                    entry.src_ip = str(ipaddress.ip_address(match["src_ip"]))
                    entry.src_port = _port(match["src_port"])
                except ValueError as exc:
                    return _reject(entry, f"invalid SSH field: {exc}")
                entry.user, entry.action, entry.status = match["user"], action, status
                entry.tags = ["authentication", "ssh"]
                break
    if entry.process == "sudo" and PATTERNS["auth_sudo"].fullmatch(entry.message or ""):
        match = PATTERNS["auth_sudo"].fullmatch(entry.message or "")
        assert match is not None
        entry.user, entry.action, entry.tags = match["user"], "sudo", ["sudo"]
    return _finish_addresses(entry)


def parse_apache_line(line: str, source: str = "apache") -> LogEntry:
    """Extract combined-log assertions without labeling request strings attacks."""
    entry = _entry(line, source, "apache_combined")
    match = PATTERNS["apache_combined"].fullmatch(line.rstrip("\r\n"))
    if not match:
        return _reject(entry, "record does not match combined access-log structure")
    try:
        entry.src_ip = str(ipaddress.ip_address(match["src_ip"]))
    except ValueError as exc:
        return _reject(entry, f"invalid remote address: {exc}")
    entry.timestamp = match["timestamp"]
    entry.user = match["user"] if match["user"] != "-" else None
    entry.status, entry.action = match["status"], f"{match['method']} {match['path']}"
    entry.tags, entry.parse_status = ["web"], "parsed"
    return _finish_addresses(entry)


def parse_json_line(line: str, source: str = "json") -> LogEntry:
    """Extract explicit named fields; reject incompatible field values visibly."""
    entry = _entry(line, source, "json")
    try:
        def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
            result: dict[str, object] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError(f"duplicate JSON field: {key}")
                result[key] = value
            return result

        def invalid_constant(value: str) -> None:
            raise ValueError(f"non-finite JSON constant: {value}")

        data = json.loads(line, object_pairs_hook=unique_object, parse_constant=invalid_constant)
        if not isinstance(data, dict):
            return _reject(entry, "JSON log record must be an object")
        mappings = {
            "timestamp": ("timestamp", "time", "@timestamp", "datetime", "ts"),
            "host": ("host", "hostname", "server", "node"),
            "src_ip": ("src_ip", "source_ip", "client_ip", "remote_addr", "clientip"),
            "dst_ip": ("dst_ip", "dest_ip", "destination_ip", "server_ip"),
            "src_port": ("src_port", "source_port"), "dst_port": ("dst_port", "destination_port", "dest_port"),
            "user": ("user", "username", "user_name", "account"),
            "action": ("action", "event", "event_type", "activity"),
            "status": ("status", "result", "outcome"),
            "message": ("message", "msg", "description", "details"),
            "process": ("process", "program", "application", "service"),
            "pid": ("pid", "process_id"),
        }
        for name, aliases in mappings.items():
            supplied = [(alias, data[alias]) for alias in aliases if alias in data and data[alias] is not None]
            if not supplied:
                continue
            if any(value != supplied[0][1] for _, value in supplied[1:]):
                raise ValueError(f"conflicting aliases for {name}: {', '.join(alias for alias, _ in supplied)}")
            value = supplied[0][1]
            if name in {"src_ip", "dst_ip"}:
                if not isinstance(value, str):
                    raise ValueError(f"{name} must be an address string")
                value = str(ipaddress.ip_address(value))
            elif name in {"src_port", "dst_port"}:
                value = _port(value)
            elif name == "pid":
                if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).isdecimal():
                    raise ValueError("pid must be a nonnegative integer or decimal string")
                value = int(value)
            elif not isinstance(value, str):
                if name in {"status", "timestamp"} and type(value) in (int, float) and math.isfinite(value):
                    value = str(value)  # Numeric time remains unresolved without epoch unit context.
                else:
                    raise ValueError(f"{name} must be a string")
            if isinstance(value, str):
                # Escaped lone surrogates can be decoded by Python's JSON reader,
                # but are not portable Unicode or valid RFC 8785 strings.
                value.encode("utf-8", errors="strict")
            setattr(entry, name, value)
    except (json.JSONDecodeError, ValueError, TypeError, OverflowError, RecursionError) as exc:
        return _reject(entry, f"JSON extraction failed: {exc}")
    entry.parse_status = "parsed"
    return _finish_addresses(entry)


def parse_windows_line(line: str, source: str = "windows") -> LogEntry:
    """Parse the supported Windows text layout without supplying its timezone."""
    entry = _entry(line, source, "windows_event")
    match = PATTERNS["windows_event"].fullmatch(line.rstrip("\r\n"))
    if not match:
        return _reject(entry, "record does not match supported Windows event text layout")
    entry.timestamp, entry.process = match["timestamp"], match["process"]
    entry.status, entry.action, entry.message = match["level"], f"event_id={match['event_id']}", match["message"]
    entry.parse_status = "parsed"
    return entry


def _validate_context(
    *, source: str, source_id: str | None, log_format: str,
    dependency_groups: list[str] | None, default_year: int | None,
    default_timezone: str | None, fold: int | None, timestamp_semantics: str,
    clock_domain: str | None, timestamp_uncertainty_seconds: float | None,
    origin_id: str | None, reliability: str, reliability_reason: str | None,
) -> None:
    """Reject malformed caller metadata before consuming a source stream."""
    if not isinstance(log_format, str) or log_format not in {"auto", "syslog", "apache", "nginx", "json", "windows"}:
        raise ValueError(f"unsupported log format: {log_format}")
    for name, value in (("source", source), ("timestamp_semantics", timestamp_semantics)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a nonempty string")
        value.encode("utf-8", errors="strict")
    for name, value in (("source_id", source_id), ("clock_domain", clock_domain),
                        ("origin_id", origin_id), ("reliability_reason", reliability_reason)):
        if value is not None:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty string or null")
            value.encode("utf-8", errors="strict")
    if dependency_groups is not None:
        if not isinstance(dependency_groups, list) or any(not isinstance(group, str) or not group.strip() for group in dependency_groups):
            raise ValueError("dependency_groups must be an array of nonempty strings")
        for group in dependency_groups:
            group.encode("utf-8", errors="strict")
    if default_year is not None and (type(default_year) is not int or not 1 <= default_year <= 9999):
        raise ValueError("year context must be an integer from 1 through 9999")
    if default_timezone is not None:
        if not isinstance(default_timezone, str) or not default_timezone.strip():
            raise ValueError("timezone context must be a nonempty string")
        default_timezone.encode("utf-8", errors="strict")
    if fold is not None and (type(fold) is not int or fold not in (0, 1)):
        raise ValueError("fold context must be 0 or 1")
    if timestamp_uncertainty_seconds is not None and (type(timestamp_uncertainty_seconds) not in (int, float) or not math.isfinite(timestamp_uncertainty_seconds) or timestamp_uncertainty_seconds < 0):
        raise ValueError("timestamp uncertainty must be finite and nonnegative, or null")
    if not isinstance(reliability, str) or reliability not in {"A", "B", "C", "D", "E", "F", "unknown"}:
        raise ValueError("reliability must be A, B, C, D, E, F, or unknown")


def _parse_stream(
    stream: BinaryIO,
    source: str,
    log_format: str = "auto",
    *,
    source_id: str | None = None,
    dependency_groups: list[str] | None = None,
    default_year: int | None = None,
    default_timezone: str | None = None,
    fold: int | None = None,
    timestamp_semantics: str = "unknown",
    clock_domain: str | None = None,
    timestamp_uncertainty_seconds: float | None = None,
    origin_id: str | None = None,
    reliability: str = "unknown",
    reliability_reason: str | None = None,
) -> Iterator[LogEntry]:
    """Preserve LF-delimited physical records and their exact line endings."""
    _validate_context(source=source, source_id=source_id, log_format=log_format,
                      dependency_groups=dependency_groups, default_year=default_year,
                      default_timezone=default_timezone, fold=fold,
                      timestamp_semantics=timestamp_semantics, clock_domain=clock_domain,
                      timestamp_uncertainty_seconds=timestamp_uncertainty_seconds,
                      origin_id=origin_id, reliability=reliability,
                      reliability_reason=reliability_reason)
    context = {key: value for key, value in (("year", default_year), ("timezone", default_timezone), ("fold", fold)) if value is not None}
    for line_number, raw_bytes in enumerate(stream, 1):
        if not raw_bytes.strip():
            continue
        line = raw_bytes.decode("utf-8", errors="surrogateescape")
        try:
            raw_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            entry = _reject(_entry(line, source, "utf8_decoder"), str(exc))
            entry.raw_bytes_base64 = base64.b64encode(raw_bytes).decode("ascii")
        else:
            selected = log_format
            if selected == "auto":
                stripped = line.lstrip()
                if stripped.startswith(("{", "[")):
                    selected = "json"
                elif PATTERNS["apache_combined"].fullmatch(line.rstrip("\r\n")):
                    selected = "apache"
                elif PATTERNS["windows_event"].fullmatch(line.rstrip("\r\n")):
                    selected = "windows"
                else:
                    selected = "syslog"
            parser = {"json": parse_json_line, "apache": parse_apache_line, "nginx": parse_apache_line, "windows": parse_windows_line, "syslog": parse_syslog_line}[selected]
            try:
                entry = parser(line, source)
            except (ValueError, TypeError, OverflowError, RecursionError) as exc:
                # A malformed field must not abort ingestion of later records.
                entry = _reject(_entry(line, source, selected), f"{selected} extraction failed: {exc}")
        entry.source_id = source_id if source_id is not None else entry.source_id
        entry.line_number = line_number
        entry.observation_id = f"{entry.source_id}:L{line_number}:{entry.record_sha256[:20]}"
        entry.dependency_groups = list(dict.fromkeys(dependency_groups or []))
        entry.timestamp_context = context.copy()
        entry.timestamp_semantics, entry.clock_domain = timestamp_semantics, clock_domain
        entry.timestamp_uncertainty_seconds = timestamp_uncertainty_seconds
        entry.origin_id, entry.reliability, entry.reliability_reason = origin_id, reliability, reliability_reason
        yield entry


def parse_log_file(
    filepath: Path | str,
    log_format: str = "auto",
    *,
    source_id: str | None = None,
    dependency_groups: list[str] | None = None,
    default_year: int | None = None,
    default_timezone: str | None = None,
    fold: int | None = None,
    timestamp_semantics: str = "unknown",
    clock_domain: str | None = None,
    timestamp_uncertainty_seconds: float | None = None,
    origin_id: str | None = None,
    reliability: str = "unknown",
    reliability_reason: str | None = None,
    source: str | None = None,
) -> Iterator[LogEntry]:
    """Yield legacy entries with lossless surrogateescape text for invalid bytes.

    The source locator defaults to the full resolved path; an explicit locator or
    stable source_id may preserve continuity across relocation. Engine callers
    should use ingest_file for portable replacement-Unicode observation records.
    This function only opens supplied files for reading, including on errors.
    """
    locator = str(Path(filepath).resolve()) if source is None else source
    with Path(filepath).open("rb") as stream:
        yield from _parse_stream(stream, locator, log_format, source_id=source_id,
                                 dependency_groups=dependency_groups, default_year=default_year,
                                 default_timezone=default_timezone, fold=fold,
                                 timestamp_semantics=timestamp_semantics, clock_domain=clock_domain,
                                 timestamp_uncertainty_seconds=timestamp_uncertainty_seconds,
                                 origin_id=origin_id, reliability=reliability,
                                 reliability_reason=reliability_reason)


def _observation(entry: LogEntry) -> dict[str, Any]:
    """Adapt legacy records to versioned, RFC 8785-compatible observations."""
    from .validators import validate

    record = asdict(entry)
    record["schema_version"] = "1"
    record["id"] = record.pop("observation_id")
    if entry.raw_bytes_base64 is not None:
        raw_bytes = base64.b64decode(entry.raw_bytes_base64, validate=True)
        record["raw"] = raw_bytes.decode("utf-8", errors="replace")
        record["message"] = record["raw"].rstrip("\r\n")
    # Python can parse source integers outside interoperable JSON's exact range.
    # Keep those assertions in raw while rejecting the extracted semantic field.
    for name in ("pid", "src_port", "dst_port"):
        value = record[name]
        if type(value) is int and abs(value) > 2**53 - 1:
            record[name] = None
            record["parse_status"] = "rejected"
            problem = f"{name} exceeds interoperable JSON integer range; original retained in raw"
            record["parse_error"] = f"{record['parse_error']}; {problem}" if record["parse_error"] else problem
    validate("observation", record)
    return record


def ingest_file(path: Path | str, log_format: str = "auto", **context: Any) -> list[dict[str, Any]]:
    """Return schema-family-1 observations bound to the original file bytes.

    Rejected source records remain observations; missing/unreadable paths and
    malformed caller context raise without changing the supplied file.
    """
    return [_observation(entry) for entry in parse_log_file(path, log_format, **context)]


def ingest_text(
    text: str | bytes,
    source: str = "inline",
    source_id: str | None = None,
    log_format: str = "auto",
    **context: Any,
) -> list[dict[str, Any]]:
    """Ingest inline text or bytes with IDs stable for a source, line and bytes.

    Separate sources should supply distinct source/source_id values. Identical
    text from the same declared source is deliberately idempotent. LF boundaries
    match ingest_file, so CRLF and Unicode line-separator characters keep their
    exact original representation. Strings must contain valid Unicode; callers
    holding undecodable source material can supply bytes without losing it.
    """
    if not isinstance(text, (str, bytes)):
        raise ValueError("text must be a Unicode string or bytes")
    raw_bytes = text.encode("utf-8", errors="strict") if isinstance(text, str) else text
    with io.BytesIO(raw_bytes) as stream:
        return [_observation(entry) for entry in _parse_stream(
            stream, source, log_format, source_id=source_id, **context)]


def _markdown(value: object) -> str:
    """Escape untrusted record content in Markdown cells."""
    text = html.escape(str(value), quote=False).replace("\\", "\\\\")
    for char in "|`*_[]{}":
        text = text.replace(char, "\\" + char)
    return text.replace("\r", "\\r").replace("\n", "\\n").encode("utf-8", errors="backslashreplace").decode("utf-8")


def entries_to_observations_table(entries: list[LogEntry]) -> str:
    """Render source assertions with extraction status, not inferred attacks."""
    lines = ["| ID | Timestamp | Source assertion | Parse status | Source |", "|---|---|---|---|---|"]
    for entry in entries:
        fields = [entry.action] if entry.action else []
        if entry.user:
            fields.append(f"user={entry.user}")
        if entry.src_ip:
            fields.append(f"source_address={entry.src_ip}")
        if entry.status:
            fields.append(f"status={entry.status}")
        description = " ".join(fields) if fields else (entry.message or entry.raw)
        values = (entry.observation_id, entry.timestamp or "unknown", description,
                  entry.parse_status + (f": {entry.parse_error}" if entry.parse_error else ""), entry.source)
        lines.append("| " + " | ".join(_markdown(value) for value in values) + " |")
    return "\n".join(lines)


def summarize_entries(entries: list[LogEntry]) -> dict[str, object]:
    """Report parse coverage and only explicitly resolvable UTC time bounds."""
    resolved = []
    for entry in entries:
        dt, _ = resolve_timestamp(entry.timestamp, default_year=entry.timestamp_context.get("year"),
                                  default_timezone=entry.timestamp_context.get("timezone"), fold=entry.timestamp_context.get("fold"))
        if dt is not None:
            resolved.append(dt)
    counts = Counter(entry.parse_status for entry in entries)
    return {
        "total_entries": len(entries), "total": len(entries),
        "parsed": counts["parsed"], "unparsed": counts["unparsed"], "rejected": counts["rejected"],
        "unique_src_ips": sorted({entry.src_ip for entry in entries if entry.src_ip}),
        "unique_users": sorted({entry.user for entry in entries if entry.user}),
        "actions": dict(Counter(entry.action for entry in entries if entry.action)),
        "statuses": dict(Counter(entry.status for entry in entries if entry.status)),
        "tags": dict(Counter(tag for entry in entries for tag in entry.tags)),
        "time_range": {"first": min(resolved).isoformat() if resolved else None, "last": max(resolved).isoformat() if resolved else None},
        "resolved_timestamps": len(resolved), "unresolved_timestamps": len(entries) - len(resolved),
        "caveats": ["Counts cover nonblank physical records in the supplied files, not collection completeness.",
                    "Extracted fields are source assertions; parsing does not verify their truth.",
                    "Time bounds use resolved source clocks only; clock synchronization and timestamp meaning require independent validation."],
    }


def main() -> None:
    """Parse logs to escaped Markdown or a JSON entries/summary envelope."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logfile", type=Path)
    parser.add_argument("format", nargs="?", default="auto", choices=("auto", "syslog", "apache", "nginx", "json", "windows"))
    parser.add_argument("--output-format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--json", action="store_true", help="alias for --output-format json")
    parser.add_argument("--source-id", help="explicit stable identity for this source")
    parser.add_argument("--dependency-group", action="append", default=[])
    parser.add_argument("--year", type=int)
    parser.add_argument("--timezone")
    parser.add_argument("--fold", type=int, choices=(0, 1))
    parser.add_argument("--timestamp-semantics", default="unknown")
    parser.add_argument("--clock-domain")
    parser.add_argument("--timestamp-uncertainty-seconds", type=float)
    args = parser.parse_args()
    try:
        entries = list(parse_log_file(args.logfile, args.format, source_id=args.source_id,
                       dependency_groups=args.dependency_group, default_year=args.year,
                       default_timezone=args.timezone, fold=args.fold, timestamp_semantics=args.timestamp_semantics,
                       clock_domain=args.clock_domain, timestamp_uncertainty_seconds=args.timestamp_uncertainty_seconds))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    summary = summarize_entries(entries)
    if args.json or args.output_format == "json":
        print(json.dumps({"entries": [asdict(entry) for entry in entries], "summary": summary}, ensure_ascii=True, indent=2, allow_nan=False))
    else:
        print(f"## Log Summary\n\nNonblank records: {summary['total']}; parsed: {summary['parsed']}; unparsed: {summary['unparsed']}; rejected: {summary['rejected']}.\n")
        print(entries_to_observations_table(entries))
        print("\n" + "\n".join(f"- {caveat}" for caveat in summary["caveats"]))


if __name__ == "__main__":
    main()
