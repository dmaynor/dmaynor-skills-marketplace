#!/usr/bin/env python3
"""
Timeline builder for SAT Analysis.

Constructs event timelines from structured observations for causal analysis.
"""

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from pathlib import Path


@dataclass
class TimelineEvent:
    """Single event in timeline."""
    
    timestamp: str
    observation_id: str
    description: str
    source: str = ""
    actor: Optional[str] = None
    target: Optional[str] = None
    tags: list = field(default_factory=list)
    
    # For sorting
    _dt: Optional[datetime] = field(default=None, repr=False)


def parse_timestamp(ts: str) -> Optional[datetime]:
    """Attempt to parse various timestamp formats."""
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%b %d %H:%M:%S",
        "%d/%b/%Y:%H:%M:%S %z",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    
    return None


class Timeline:
    """Event timeline with analysis capabilities."""
    
    def __init__(self):
        self.events: list[TimelineEvent] = []
    
    def add_event(
        self,
        timestamp: str,
        observation_id: str,
        description: str,
        source: str = "",
        actor: Optional[str] = None,
        target: Optional[str] = None,
        tags: Optional[list] = None,
    ) -> TimelineEvent:
        """Add event to timeline."""
        event = TimelineEvent(
            timestamp=timestamp,
            observation_id=observation_id,
            description=description,
            source=source,
            actor=actor,
            target=target,
            tags=tags or [],
            _dt=parse_timestamp(timestamp),
        )
        self.events.append(event)
        return event
    
    def sort(self):
        """Sort events chronologically."""
        # Events with parseable timestamps first, sorted; then unparseable
        parseable = [e for e in self.events if e._dt is not None]
        unparseable = [e for e in self.events if e._dt is None]
        
        parseable.sort(key=lambda e: e._dt)
        self.events = parseable + unparseable
    
    def get_time_range(self) -> tuple[Optional[str], Optional[str]]:
        """Get first and last timestamps."""
        self.sort()
        if not self.events:
            return None, None
        return self.events[0].timestamp, self.events[-1].timestamp
    
    def get_gaps(self, threshold_seconds: float = 300) -> list[tuple[TimelineEvent, TimelineEvent, float]]:
        """Find significant time gaps between events."""
        self.sort()
        gaps = []
        
        for i in range(len(self.events) - 1):
            e1, e2 = self.events[i], self.events[i + 1]
            if e1._dt and e2._dt:
                delta = (e2._dt - e1._dt).total_seconds()
                if delta > threshold_seconds:
                    gaps.append((e1, e2, delta))
        
        return gaps
    
    def filter_by_actor(self, actor: str) -> "Timeline":
        """Return new timeline filtered to specific actor."""
        filtered = Timeline()
        filtered.events = [e for e in self.events if e.actor == actor]
        return filtered
    
    def filter_by_tag(self, tag: str) -> "Timeline":
        """Return new timeline filtered to events with specific tag."""
        filtered = Timeline()
        filtered.events = [e for e in self.events if tag in e.tags]
        return filtered
    
    def to_markdown(self, include_gaps: bool = True) -> str:
        """Generate markdown timeline representation."""
        self.sort()
        
        lines = [
            "## Event Timeline\n",
            "| Time | ID | Event | Actor | Source |",
            "|------|----|----|-------|--------|",
        ]
        
        for event in self.events:
            actor = event.actor or "-"
            lines.append(
                f"| {event.timestamp} | {event.observation_id} | "
                f"{event.description} | {actor} | {event.source} |"
            )
        
        if include_gaps:
            gaps = self.get_gaps()
            if gaps:
                lines.append("\n### Timeline Gaps\n")
                for e1, e2, delta in gaps:
                    minutes = delta / 60
                    lines.append(
                        f"- **{minutes:.1f} min gap** between {e1.observation_id} "
                        f"({e1.timestamp}) and {e2.observation_id} ({e2.timestamp})"
                    )
        
        return "\n".join(lines)
    
    def to_ascii_timeline(self, max_width: int = 80) -> str:
        """Generate ASCII art timeline."""
        self.sort()
        
        if not self.events:
            return "No events in timeline."
        
        lines = ["```"]
        
        for event in self.events:
            time_str = event.timestamp[-8:] if len(event.timestamp) > 8 else event.timestamp
            desc = event.description[:50] + "..." if len(event.description) > 50 else event.description
            
            lines.append(f"  {time_str} ─┬─ [{event.observation_id}] {desc}")
            
            if event.actor:
                lines.append(f"             │   Actor: {event.actor}")
            if event.tags:
                lines.append(f"             │   Tags: {', '.join(event.tags)}")
            
            lines.append("             │")
        
        # Remove last connector
        if lines[-1] == "             │":
            lines[-1] = "             ╵"
        
        lines.append("```")
        
        return "\n".join(lines)
    
    def analyze_sequences(self) -> dict:
        """Analyze event sequences for patterns."""
        self.sort()
        
        analysis = {
            "total_events": len(self.events),
            "actors": {},
            "tag_sequences": [],
            "rapid_succession": [],  # Events within 5 seconds
        }
        
        # Count events per actor
        for event in self.events:
            if event.actor:
                if event.actor not in analysis["actors"]:
                    analysis["actors"][event.actor] = {"count": 0, "first": None, "last": None}
                analysis["actors"][event.actor]["count"] += 1
                if not analysis["actors"][event.actor]["first"]:
                    analysis["actors"][event.actor]["first"] = event.timestamp
                analysis["actors"][event.actor]["last"] = event.timestamp
        
        # Find rapid succession events
        for i in range(len(self.events) - 1):
            e1, e2 = self.events[i], self.events[i + 1]
            if e1._dt and e2._dt:
                delta = (e2._dt - e1._dt).total_seconds()
                if 0 < delta <= 5:
                    analysis["rapid_succession"].append({
                        "event1": e1.observation_id,
                        "event2": e2.observation_id,
                        "delta_seconds": delta,
                    })
        
        return analysis


def from_observations_json(data: list[dict]) -> Timeline:
    """Build timeline from list of observation dictionaries."""
    timeline = Timeline()
    
    for obs in data:
        timeline.add_event(
            timestamp=obs.get("timestamp", "unknown"),
            observation_id=obs.get("observation_id", obs.get("id", "?")),
            description=obs.get("description", obs.get("message", "")),
            source=obs.get("source", ""),
            actor=obs.get("actor", obs.get("user")),
            target=obs.get("target"),
            tags=obs.get("tags", []),
        )
    
    return timeline


def main():
    """CLI interface for timeline building."""
    if len(sys.argv) < 2:
        print("Usage: timeline.py <observations.json>")
        print("\nExpected JSON format:")
        print('[{"timestamp": "...", "observation_id": "O1", "description": "...", ...}]')
        sys.exit(1)
    
    filepath = Path(sys.argv[1])
    
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    
    with open(filepath) as f:
        data = json.load(f)
    
    timeline = from_observations_json(data)
    
    print(timeline.to_markdown())
    print("\n" + timeline.to_ascii_timeline())
    
    analysis = timeline.analyze_sequences()
    
    print("\n## Timeline Analysis\n")
    print(f"- **Total events**: {analysis['total_events']}")
    print(f"- **Unique actors**: {len(analysis['actors'])}")
    
    if analysis["actors"]:
        print("\n### Activity by Actor\n")
        for actor, info in analysis["actors"].items():
            print(f"- **{actor}**: {info['count']} events ({info['first']} to {info['last']})")
    
    if analysis["rapid_succession"]:
        print("\n### Rapid Succession Events (≤5 sec)\n")
        for seq in analysis["rapid_succession"]:
            print(f"- {seq['event1']} → {seq['event2']} ({seq['delta_seconds']:.1f}s)")


if __name__ == "__main__":
    main()
