#!/usr/bin/env python3
"""
Log parsing utilities for SAT Analysis.

Parses common log formats into structured observations for analysis.
Supports: syslog, auth.log, Apache/Nginx access, Windows Event, JSON logs.
"""

import re
import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Iterator
from pathlib import Path


@dataclass
class LogEntry:
    """Structured log entry for analysis."""
    
    timestamp: Optional[str] = None
    source: str = ""
    raw: str = ""
    
    # Parsed fields
    host: Optional[str] = None
    process: Optional[str] = None
    pid: Optional[int] = None
    user: Optional[str] = None
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    action: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None
    
    # Analysis metadata
    observation_id: Optional[str] = None
    tags: list = field(default_factory=list)


# Regex patterns for common log formats
PATTERNS = {
    "syslog": re.compile(
        r"^(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
        r"(?P<host>\S+)\s+"
        r"(?P<process>\S+?)(?:\[(?P<pid>\d+)\])?:\s+"
        r"(?P<message>.*)$"
    ),
    "syslog_iso": re.compile(
        r"^(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)\s+"
        r"(?P<host>\S+)\s+"
        r"(?P<process>\S+?)(?:\[(?P<pid>\d+)\])?:\s+"
        r"(?P<message>.*)$"
    ),
    "auth_ssh_fail": re.compile(
        r"Failed (?:password|publickey) for (?:invalid user )?(?P<user>\S+) "
        r"from (?P<src_ip>\d+\.\d+\.\d+\.\d+) port (?P<src_port>\d+)"
    ),
    "auth_ssh_success": re.compile(
        r"Accepted (?:password|publickey) for (?P<user>\S+) "
        r"from (?P<src_ip>\d+\.\d+\.\d+\.\d+) port (?P<src_port>\d+)"
    ),
    "auth_sudo": re.compile(
        r"(?P<user>\S+)\s*:\s*TTY=\S+\s*;\s*PWD=\S+\s*;\s*USER=(?P<target_user>\S+)\s*;\s*"
        r"COMMAND=(?P<command>.*)"
    ),
    "apache_combined": re.compile(
        r'^(?P<src_ip>\d+\.\d+\.\d+\.\d+)\s+-\s+(?P<user>\S+)\s+'
        r'\[(?P<timestamp>[^\]]+)\]\s+'
        r'"(?P<method>\w+)\s+(?P<path>\S+)\s+(?P<protocol>[^"]+)"\s+'
        r'(?P<status>\d+)\s+(?P<bytes>\d+|-)\s+'
        r'"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)"'
    ),
    "nginx_combined": re.compile(
        r'^(?P<src_ip>\d+\.\d+\.\d+\.\d+)\s+-\s+(?P<user>\S+)\s+'
        r'\[(?P<timestamp>[^\]]+)\]\s+'
        r'"(?P<method>\w+)\s+(?P<path>\S+)\s+(?P<protocol>[^"]+)"\s+'
        r'(?P<status>\d+)\s+(?P<bytes>\d+)\s+'
        r'"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)"'
    ),
    "ip_address": re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
    "windows_event": re.compile(
        r"(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+"
        r"(?P<level>\w+)\s+(?P<source>\S+)\s+(?P<event_id>\d+)\s+"
        r"(?P<message>.*)"
    ),
}


def parse_syslog_line(line: str, source: str = "syslog") -> Optional[LogEntry]:
    """Parse a syslog format line."""
    entry = LogEntry(raw=line.strip(), source=source)
    
    # Try ISO format first, then traditional
    for pattern_name in ["syslog_iso", "syslog"]:
        match = PATTERNS[pattern_name].match(line)
        if match:
            groups = match.groupdict()
            entry.timestamp = groups.get("timestamp")
            entry.host = groups.get("host")
            entry.process = groups.get("process")
            entry.pid = int(groups["pid"]) if groups.get("pid") else None
            entry.message = groups.get("message")
            break
    
    if not entry.message:
        entry.message = line.strip()
    
    # Parse SSH auth events
    if "sshd" in (entry.process or ""):
        ssh_fail = PATTERNS["auth_ssh_fail"].search(entry.message or "")
        if ssh_fail:
            entry.user = ssh_fail.group("user")
            entry.src_ip = ssh_fail.group("src_ip")
            entry.src_port = int(ssh_fail.group("src_port"))
            entry.action = "ssh_auth_fail"
            entry.status = "failure"
            entry.tags.append("authentication")
            entry.tags.append("ssh")
            return entry
        
        ssh_success = PATTERNS["auth_ssh_success"].search(entry.message or "")
        if ssh_success:
            entry.user = ssh_success.group("user")
            entry.src_ip = ssh_success.group("src_ip")
            entry.src_port = int(ssh_success.group("src_port"))
            entry.action = "ssh_auth_success"
            entry.status = "success"
            entry.tags.append("authentication")
            entry.tags.append("ssh")
            return entry
    
    # Parse sudo events
    if "sudo" in (entry.process or ""):
        sudo_match = PATTERNS["auth_sudo"].search(entry.message or "")
        if sudo_match:
            entry.user = sudo_match.group("user")
            entry.action = "sudo"
            entry.tags.append("privilege_escalation")
            return entry
    
    # Extract any IP addresses from message
    if entry.message:
        ips = PATTERNS["ip_address"].findall(entry.message)
        if ips and not entry.src_ip:
            entry.src_ip = ips[0]
    
    return entry


def parse_apache_line(line: str, source: str = "apache") -> Optional[LogEntry]:
    """Parse Apache/Nginx combined log format."""
    entry = LogEntry(raw=line.strip(), source=source)
    
    for pattern_name in ["apache_combined", "nginx_combined"]:
        match = PATTERNS[pattern_name].match(line)
        if match:
            groups = match.groupdict()
            entry.timestamp = groups.get("timestamp")
            entry.src_ip = groups.get("src_ip")
            entry.user = groups.get("user") if groups.get("user") != "-" else None
            entry.status = groups.get("status")
            entry.action = f"{groups.get('method')} {groups.get('path')}"
            entry.message = line.strip()
            entry.tags.append("web")
            
            # Tag suspicious patterns
            path = groups.get("path", "")
            if ".." in path or "%2e%2e" in path.lower():
                entry.tags.append("path_traversal_attempt")
            if "' or " in path.lower() or "union select" in path.lower():
                entry.tags.append("sqli_attempt")
            if "<script" in path.lower() or "javascript:" in path.lower():
                entry.tags.append("xss_attempt")
            
            return entry
    
    return None


def parse_json_line(line: str, source: str = "json") -> Optional[LogEntry]:
    """Parse JSON formatted log line."""
    try:
        data = json.loads(line.strip())
    except json.JSONDecodeError:
        return None
    
    entry = LogEntry(raw=line.strip(), source=source)
    
    # Common JSON log field mappings
    field_mappings = {
        "timestamp": ["timestamp", "time", "@timestamp", "datetime", "ts"],
        "host": ["host", "hostname", "server", "node"],
        "src_ip": ["src_ip", "source_ip", "client_ip", "remote_addr", "clientip"],
        "dst_ip": ["dst_ip", "dest_ip", "destination_ip", "server_ip"],
        "user": ["user", "username", "user_name", "account"],
        "action": ["action", "event", "event_type", "activity"],
        "status": ["status", "result", "outcome"],
        "message": ["message", "msg", "description", "details"],
        "process": ["process", "program", "application", "service"],
        "pid": ["pid", "process_id"],
    }
    
    for field, candidates in field_mappings.items():
        for candidate in candidates:
            if candidate in data:
                value = data[candidate]
                if field == "pid" and value:
                    value = int(value)
                setattr(entry, field, value)
                break
    
    return entry


def parse_log_file(
    filepath: Path,
    log_format: str = "auto"
) -> Iterator[LogEntry]:
    """
    Parse a log file and yield structured entries.
    
    Args:
        filepath: Path to log file
        log_format: One of 'auto', 'syslog', 'apache', 'json'
    
    Yields:
        LogEntry objects
    """
    source = filepath.name
    obs_counter = 0
    
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            entry = None
            
            if log_format == "auto":
                # Try each parser
                if line.startswith("{"):
                    entry = parse_json_line(line, source)
                elif PATTERNS["apache_combined"].match(line):
                    entry = parse_apache_line(line, source)
                else:
                    entry = parse_syslog_line(line, source)
            elif log_format == "syslog":
                entry = parse_syslog_line(line, source)
            elif log_format == "apache":
                entry = parse_apache_line(line, source)
            elif log_format == "json":
                entry = parse_json_line(line, source)
            
            if entry:
                obs_counter += 1
                entry.observation_id = f"O{obs_counter}"
                yield entry


def entries_to_observations_table(entries: list[LogEntry]) -> str:
    """Convert log entries to markdown observation table."""
    lines = [
        "| ID | Timestamp | Observation | Source |",
        "|----|-----------|-------------|--------|",
    ]
    
    for entry in entries:
        obs_text = []
        
        if entry.action:
            obs_text.append(entry.action)
        if entry.user:
            obs_text.append(f"user={entry.user}")
        if entry.src_ip:
            obs_text.append(f"from {entry.src_ip}")
            if entry.src_port:
                obs_text[-1] += f":{entry.src_port}"
        if entry.status:
            obs_text.append(f"status={entry.status}")
        if not obs_text and entry.message:
            obs_text.append(entry.message[:80])
        
        observation = " ".join(obs_text) if obs_text else entry.raw[:80]
        timestamp = entry.timestamp or "-"
        
        lines.append(
            f"| {entry.observation_id} | {timestamp} | {observation} | {entry.source} |"
        )
    
    return "\n".join(lines)


def summarize_entries(entries: list[LogEntry]) -> dict:
    """Generate summary statistics from log entries."""
    summary = {
        "total_entries": len(entries),
        "unique_src_ips": set(),
        "unique_users": set(),
        "actions": {},
        "statuses": {},
        "time_range": {"first": None, "last": None},
        "tags": {},
    }
    
    for entry in entries:
        if entry.src_ip:
            summary["unique_src_ips"].add(entry.src_ip)
        if entry.user:
            summary["unique_users"].add(entry.user)
        if entry.action:
            summary["actions"][entry.action] = summary["actions"].get(entry.action, 0) + 1
        if entry.status:
            summary["statuses"][entry.status] = summary["statuses"].get(entry.status, 0) + 1
        if entry.timestamp:
            if not summary["time_range"]["first"]:
                summary["time_range"]["first"] = entry.timestamp
            summary["time_range"]["last"] = entry.timestamp
        for tag in entry.tags:
            summary["tags"][tag] = summary["tags"].get(tag, 0) + 1
    
    summary["unique_src_ips"] = list(summary["unique_src_ips"])
    summary["unique_users"] = list(summary["unique_users"])
    
    return summary


def main():
    """CLI interface for log parsing."""
    if len(sys.argv) < 2:
        print("Usage: parse_logs.py <logfile> [format]")
        print("Formats: auto, syslog, apache, json")
        sys.exit(1)
    
    filepath = Path(sys.argv[1])
    log_format = sys.argv[2] if len(sys.argv) > 2 else "auto"
    
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    
    entries = list(parse_log_file(filepath, log_format))
    
    print("## Log Summary\n")
    summary = summarize_entries(entries)
    print(f"- **Total entries**: {summary['total_entries']}")
    print(f"- **Unique source IPs**: {len(summary['unique_src_ips'])}")
    print(f"- **Unique users**: {len(summary['unique_users'])}")
    print(f"- **Time range**: {summary['time_range']['first']} to {summary['time_range']['last']}")
    
    if summary["tags"]:
        print(f"- **Tags detected**: {summary['tags']}")
    
    print("\n## Observations\n")
    print(entries_to_observations_table(entries))


if __name__ == "__main__":
    main()
