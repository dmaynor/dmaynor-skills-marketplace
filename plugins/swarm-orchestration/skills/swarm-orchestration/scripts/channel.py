#!/usr/bin/env python3
"""
Channel management for swarm orchestration.

Provides read/write operations for the shared communication channel.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def get_channel_path(team: str) -> Path:
    """Get path to team's channel file."""
    return Path.home() / ".claude" / "teams" / team / "channel.jsonl"


def ensure_channel_exists(team: str) -> Path:
    """Ensure channel file exists, create if not."""
    path = get_channel_path(team)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()
    return path


def read_channel(
    team: str,
    mine: Optional[str] = None,
    since: Optional[str] = None,
    last_n: int = 50,
) -> list[dict]:
    """
    Read messages from channel.

    Args:
        team: Team name
        mine: If provided, filter to messages mentioning this handle
        since: ISO timestamp, only messages after this time
        last_n: Number of recent messages to return

    Returns:
        List of message dicts
    """
    path = get_channel_path(team)
    if not path.exists():
        return []

    messages = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                messages.append(msg)
            except json.JSONDecodeError:
                continue

    # Filter by timestamp
    if since:
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        messages = [
            m for m in messages
            if datetime.fromisoformat(m["ts"].replace("Z", "+00:00")) > since_dt
        ]

    # Filter by recipient
    if mine:
        handle = f"@{mine}" if not mine.startswith("@") else mine
        messages = [
            m for m in messages
            if m.get("to") is None  # Broadcast
            or handle in (m.get("to") or [])
            or "@all" in (m.get("to") or [])
        ]

    # Return last N
    return messages[-last_n:]


def write_channel(
    team: str,
    from_agent: str,
    content: str,
    reasoning: str,
    to: Optional[list[str]] = None,
    msg_type: str = "message",
) -> dict:
    """
    Write message to channel.

    Args:
        team: Team name
        from_agent: Sender agent name
        content: Message content
        reasoning: Why this message (evidence trail)
        to: List of @handles (None = broadcast)
        msg_type: Message type (message, decision, task, status, request, autonomy, system)

    Returns:
        The written message dict
    """
    path = ensure_channel_exists(team)

    # Normalize handles
    if to:
        to = [h if h.startswith("@") else f"@{h}" for h in to]

    message = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "from": from_agent,
        "to": to,
        "type": msg_type,
        "reasoning": reasoning,
        "content": content,
    }

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(message) + "\n")

    return message


def format_message(msg: dict) -> str:
    """Format message for display."""
    ts = msg.get("ts", "?")[:19]
    from_agent = msg.get("from", "?")
    to = msg.get("to")
    to_str = " → " + ", ".join(to) if to else " → @all"
    msg_type = msg.get("type", "message")
    reasoning = msg.get("reasoning", "")
    content = msg.get("content", "")

    lines = [
        f"[{ts}] {from_agent}{to_str} ({msg_type})",
    ]
    if reasoning:
        lines.append(f"  REASONING: {reasoning}")
    if content:
        lines.append(f"  {content}")
    return "\n".join(lines)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Swarm channel management")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Read command
    read_parser = subparsers.add_parser("read", help="Read channel messages")
    read_parser.add_argument("--team", required=True, help="Team name")
    read_parser.add_argument("--mine", help="Filter to messages for this handle")
    read_parser.add_argument("--since", help="ISO timestamp, messages after")
    read_parser.add_argument("--last", type=int, default=50, help="Last N messages")
    read_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Write command
    write_parser = subparsers.add_parser("write", help="Write channel message")
    write_parser.add_argument("--team", required=True, help="Team name")
    write_parser.add_argument("--from", dest="from_agent", required=True, help="Sender")
    write_parser.add_argument("--to", nargs="*", help="Recipients (@handles)")
    write_parser.add_argument("--type", dest="msg_type", default="message",
                              choices=["message", "decision", "task", "status",
                                       "request", "autonomy", "system"],
                              help="Message type")
    write_parser.add_argument("--reasoning", required=True, help="Why (evidence)")
    write_parser.add_argument("--content", required=True, help="Message content")

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize channel")
    init_parser.add_argument("--team", required=True, help="Team name")

    args = parser.parse_args()

    if args.command == "read":
        messages = read_channel(
            team=args.team,
            mine=args.mine,
            since=args.since,
            last_n=args.last,
        )
        if args.json:
            print(json.dumps(messages, indent=2))
        else:
            if not messages:
                print("No messages.")
            else:
                for msg in messages:
                    print(format_message(msg))
                    print()

    elif args.command == "write":
        msg = write_channel(
            team=args.team,
            from_agent=args.from_agent,
            content=args.content,
            reasoning=args.reasoning,
            to=args.to,
            msg_type=args.msg_type,
        )
        print(f"Message written: {msg['ts']}")

    elif args.command == "init":
        path = ensure_channel_exists(args.team)
        print(f"Channel initialized: {path}")


if __name__ == "__main__":
    main()
