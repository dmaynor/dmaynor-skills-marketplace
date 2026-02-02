# NPC and Traffic Generation Strategies

Approaches for generating realistic background traffic and user activity simulation in cyber ranges.

## Why Traffic Generation Matters

Without realistic background traffic:
- Adversary activity is trivially detectable (only traffic on wire)
- Security tools have no baseline for anomaly detection
- Defenders cannot practice tuning alert thresholds
- Exercise fidelity is severely degraded

**Goal**: Generate traffic indistinguishable from real enterprise activity while providing sufficient volume to mask adversary operations.

## Traffic Generation Approaches

### Approach Comparison

| Approach | Realism | Complexity | Resource Cost | Detectability |
|----------|---------|------------|---------------|---------------|
| Scripted replay | Low | Low | Low | High (patterns repeat) |
| Protocol generators | Medium | Medium | Medium | Medium |
| Headless browsers | Medium-High | Medium | Medium-High | Medium-Low |
| Full VM NPCs | High | High | High | Low |
| LLM-driven behavioral | Ultra | High | Medium-High | Very Low |

### 1. Scripted Traffic Replay

**Description**: Replay captured PCAP files or generate traffic from templates.

**Pros**: Simple, predictable, low resource
**Cons**: Easily fingerprinted, no adaptive behavior, obvious patterns

```bash
# tcpreplay example
tcpreplay --intf1=eth0 --topspeed captured_traffic.pcap

# Loop with timing variation
while true; do
    tcpreplay --intf1=eth0 --multiplier=0.5 captured_traffic.pcap
    sleep $((RANDOM % 60 + 30))
done
```

**Best For**: Initial testing, low-fidelity exercises, protocol validation

### 2. Protocol-Level Generators

**Description**: Generate traffic at protocol level (HTTP, SMTP, SMB, etc.)

**Tools**:
- `curl` / `wget` for HTTP
- `swaks` for SMTP
- `smbclient` for SMB
- Custom scripts for specific protocols

```bash
#!/bin/bash
# Simple web traffic generator

URLS=(
    "http://internal-web/portal"
    "http://internal-web/hr"
    "http://internal-web/finance"
    "http://intranet.corp.local/news"
)

while true; do
    URL=${URLS[$RANDOM % ${#URLS[@]}]}
    curl -s -o /dev/null "$URL"
    sleep $((RANDOM % 30 + 5))
done
```

**Best For**: Specific protocol testing, lightweight traffic fill

### 3. Headless Browser Automation

**Description**: Automated browsers performing realistic web interactions.

**Tools**:
- Selenium WebDriver
- Playwright
- Puppeteer

```python
#!/usr/bin/env python3
"""
Headless browser NPC for web traffic generation.
"""

import asyncio
import random
from playwright.async_api import async_playwright

INTERNAL_SITES = [
    "http://intranet.corp.local",
    "http://hr.corp.local",
    "http://sharepoint.corp.local",
]

EXTERNAL_SITES = [
    "http://news.grey.local",
    "http://weather.grey.local",
    "http://social.grey.local",
]

async def browse_site(page, url: str):
    """Visit a site and perform random interactions."""
    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        
        # Random scroll behavior
        for _ in range(random.randint(1, 5)):
            await page.evaluate(f"window.scrollBy(0, {random.randint(100, 500)})")
            await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # Maybe click a link
        if random.random() > 0.5:
            links = await page.query_selector_all("a[href]")
            if links:
                link = random.choice(links)
                await link.click()
                await asyncio.sleep(random.uniform(1.0, 3.0))
                
    except Exception as e:
        print(f"Browse error: {e}")

async def npc_browser_session():
    """Run a simulated user browsing session."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        while True:
            # Mix of internal and external browsing
            if random.random() > 0.3:
                url = random.choice(INTERNAL_SITES)
            else:
                url = random.choice(EXTERNAL_SITES)
            
            await browse_site(page, url)
            
            # Variable delay between sites (30s - 5min)
            await asyncio.sleep(random.uniform(30, 300))

if __name__ == "__main__":
    asyncio.run(npc_browser_session())
```

**Best For**: Web-heavy exercises, realistic browse patterns

### 4. Full VM NPC Simulation

**Description**: Dedicated VMs running full user simulation with multiple activities.

**SEI GHOSTS Framework**: https://github.com/cmu-sei/GHOSTS

```yaml
# GHOSTS NPC configuration example
npc_profile:
  name: "Standard Office Worker"
  
  activities:
    - type: web_browse
      weight: 40
      internal_ratio: 0.7
      session_duration_minutes: 5-30
      
    - type: email
      weight: 25
      check_interval_minutes: 15-60
      compose_ratio: 0.2
      
    - type: file_access
      weight: 20
      paths:
        - "\\\\fileserver\\shared"
        - "\\\\fileserver\\department"
      operations: [read, write, copy]
      
    - type: application
      weight: 10
      apps:
        - word
        - excel
        - outlook
        
    - type: idle
      weight: 5
      duration_minutes: 5-15
      
  schedule:
    work_start: "08:00"
    work_end: "17:00"
    lunch_start: "12:00"
    lunch_duration_minutes: 30-60
    break_frequency_hours: 2
    break_duration_minutes: 5-15
```

**Best For**: High-fidelity exercises, realistic telemetry generation

### 5. LLM-Driven Behavioral Simulation

**Description**: AI-driven NPCs that make contextual decisions about activity.

**Concept**: Instead of scripted actions, NPCs use language models to decide what to do based on their "role" and current context.

```python
#!/usr/bin/env python3
"""
LLM-driven NPC behavioral simulation concept.
"""

import random
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class NPCPersona:
    name: str
    department: str
    role: str
    seniority: str
    work_patterns: str
    interests: List[str]
    
    def to_prompt(self) -> str:
        return f"""You are {self.name}, a {self.seniority} {self.role} in the {self.department} department.

Work patterns: {self.work_patterns}
Personal interests: {', '.join(self.interests)}

You are simulating realistic work activity. Based on your role and the current context,
decide what action to take next. Actions should be realistic for your role.

Available actions:
- browse_internal: Visit internal company websites
- browse_external: Visit external websites (news, reference, etc.)
- check_email: Check and potentially respond to emails
- file_access: Access files on network shares
- application: Use desktop applications (Word, Excel, etc.)
- idle: Take a short break
- meeting: Join a virtual meeting (audio/video)

Respond with a JSON object:
{{
    "action": "<action_type>",
    "target": "<specific target if applicable>",
    "duration_minutes": <estimated duration>,
    "reasoning": "<brief reasoning>"
}}
"""

class LLMNPCEngine:
    def __init__(self, persona: NPCPersona, llm_client):
        self.persona = persona
        self.llm = llm_client
        self.action_history: List[dict] = []
        self.current_time = "09:00"
        
    async def decide_next_action(self) -> dict:
        """Use LLM to decide next action based on context."""
        
        # Build context from recent history
        recent_actions = self.action_history[-5:] if self.action_history else []
        
        context = f"""
Current time: {self.current_time}
Recent actions: {recent_actions}

What should {self.persona.name} do next?
"""
        
        prompt = self.persona.to_prompt() + context
        
        response = await self.llm.complete(prompt)
        action = self._parse_action(response)
        
        self.action_history.append(action)
        return action
    
    def _parse_action(self, response: str) -> dict:
        """Parse LLM response into action dict."""
        # Implementation: parse JSON from response
        pass

# Example personas for different departments
FINANCE_ANALYST = NPCPersona(
    name="Sarah Chen",
    department="Finance",
    role="Financial Analyst",
    seniority="Mid-level",
    work_patterns="Heavy spreadsheet use, quarterly reporting cycles, frequent email with executives",
    interests=["market news", "economic indicators", "financial regulations"]
)

IT_HELPDESK = NPCPersona(
    name="Mike Rodriguez",
    department="IT",
    role="Help Desk Technician",
    seniority="Junior",
    work_patterns="Ticket-driven work, remote desktop sessions, knowledge base lookups",
    interests=["tech news", "gaming", "troubleshooting guides"]
)

EXECUTIVE = NPCPersona(
    name="Jennifer Williams",
    department="Executive",
    role="VP of Operations",
    seniority="Executive",
    work_patterns="Many meetings, strategic documents, minimal technical work, delegate tasks",
    interests=["industry news", "leadership content", "competitor analysis"]
)
```

**Best For**: Ultra-high fidelity, adaptive behavior, SOC training against realistic patterns

## Protocol-Specific Traffic Patterns

### DNS Traffic

```yaml
dns_traffic:
  internal_queries:
    - "dc01.corp.local"
    - "mail.corp.local"
    - "sharepoint.corp.local"
    frequency: high
    
  external_queries:
    - type: legitimate
      domains: ["google.com", "microsoft.com", "news.com"]
      frequency: high
    - type: cdn
      domains: ["cloudfront.net", "akamai.net", "cloudflare.com"]
      frequency: medium
    - type: analytics
      domains: ["google-analytics.com", "facebook.com/tr"]
      frequency: medium
      
  suspicious_patterns_to_avoid:
    - Long subdomain queries (DGA-like)
    - High-frequency single domain
    - TXT record abuse
```

### HTTP/HTTPS Traffic

```yaml
http_traffic:
  internal:
    patterns:
      - "GET /portal/dashboard"
      - "POST /api/auth/login"
      - "GET /sharepoint/sites/hr/documents"
    user_agents:
      - "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
      - "Microsoft Office/16.0"
      
  external:
    patterns:
      - Mixed GET/POST
      - Realistic referrer chains
      - Cookie handling
    categories:
      - news (30%)
      - reference (20%)
      - business (25%)
      - entertainment (15%)
      - other (10%)
```

### SMB/File Access Traffic

```yaml
smb_traffic:
  shares:
    - "\\\\fileserver\\shared"
    - "\\\\fileserver\\department\\{dept}"
    - "\\\\fileserver\\home\\{username}"
    
  operations:
    - read: 60%
    - write: 25%
    - delete: 5%
    - create: 10%
    
  file_types:
    - ".docx", ".xlsx", ".pptx" (office)
    - ".pdf" (documents)
    - ".txt", ".csv" (data)
    - ".zip" (archives)
    
  timing:
    burst_on_login: true
    steady_state_iops: 10-50 per user
```

### Email Traffic

```yaml
email_traffic:
  internal:
    volume: 20-50 emails/user/day
    patterns:
      - Reply chains (60%)
      - New threads (30%)
      - Forwards (10%)
    attachments:
      frequency: 20%
      types: [".docx", ".xlsx", ".pdf"]
      
  external:
    volume: 5-15 emails/user/day
    patterns:
      - Newsletters
      - Vendor correspondence
      - Customer communication
      
  timing:
    peak_hours: ["09:00-11:00", "14:00-16:00"]
    check_frequency: 15-60 minutes
```

## Traffic Volume Guidelines

### Per-User Baseline Traffic

| Activity | Sessions/Day | Avg Duration | Data Volume |
|----------|--------------|--------------|-------------|
| Web browsing | 20-50 | 2-10 min | 50-200 MB |
| Email | 5-10 | 1-5 min | 5-20 MB |
| File access | 10-30 | < 1 min | 10-100 MB |
| Application use | 5-15 | 10-60 min | 1-10 MB |

### Network-Wide Targets

| Metric | Small Range | Medium Range | Large Range |
|--------|-------------|--------------|-------------|
| DNS queries/sec | 10-50 | 50-200 | 200-1000 |
| HTTP requests/sec | 20-100 | 100-500 | 500-2000 |
| SMB ops/sec | 50-200 | 200-1000 | 1000-5000 |
| SMTP messages/hour | 100-500 | 500-2000 | 2000-10000 |

## Telemetry Generation

Traffic generation should produce security-relevant telemetry:

### Windows Event Logs

```yaml
expected_events:
  security:
    - 4624: Successful logon (high volume)
    - 4625: Failed logon (low volume, occasional)
    - 4634: Logoff (matches 4624)
    - 4648: Explicit credential logon
    
  powershell:
    - 4104: Script block logging
    - 4103: Module logging
    
  sysmon:
    - Event 1: Process creation
    - Event 3: Network connection
    - Event 7: Image load
    - Event 11: File create
    - Event 22: DNS query
```

### Network Telemetry

```yaml
expected_flow_data:
  netflow:
    - Internal-to-internal (majority)
    - Internal-to-DMZ (services)
    - Internal-to-external via proxy (web)
    - External-to-DMZ (inbound services)
    
  zeek_logs:
    - conn.log: All connections
    - dns.log: DNS queries
    - http.log: HTTP transactions
    - ssl.log: TLS handshakes
    - files.log: File transfers
```

## Implementation Checklist

### Pre-Exercise Traffic Setup

- [ ] NPC user accounts created in AD
- [ ] NPC VMs deployed and logged in
- [ ] Traffic generators configured and running
- [ ] Baseline telemetry verified in SIEM
- [ ] Traffic patterns validated (no obvious anomalies)
- [ ] Resource utilization acceptable
- [ ] Network bandwidth within limits

### Validation Tests

```bash
# Verify DNS traffic
tcpdump -i eth0 port 53 -c 100 | grep -c "corp.local"

# Verify HTTP traffic
tcpdump -i eth0 port 80 or port 443 -c 100

# Verify SMB traffic
tcpdump -i eth0 port 445 -c 50

# Check SIEM for event volume
# (SIEM-specific query)
```

### Tuning Parameters

| Parameter | Effect of Increase | Effect of Decrease |
|-----------|-------------------|-------------------|
| Activity frequency | More traffic, more load | Less cover for adversary |
| Session duration | Longer connections | More bursty patterns |
| Randomization | Less predictable | Potential clustering |
| User count | More volume | Less per-user diversity |

## Tools Reference

### Open Source

| Tool | Purpose | URL |
|------|---------|-----|
| GHOSTS | Full NPC simulation | https://github.com/cmu-sei/GHOSTS |
| Selenium/Playwright | Browser automation | https://playwright.dev |
| tcpreplay | PCAP replay | https://tcpreplay.appneta.com |
| hping3 | Packet crafting | http://www.hping.org |
| Locust | Load testing | https://locust.io |

### Commercial

| Tool | Purpose | Notes |
|------|---------|-------|
| BreakingPoint | Full traffic simulation | Keysight product |
| Ixia | Network testing | Keysight product |
| Spirent | Traffic generation | Enterprise-grade |
