# Docker-Based Cyber Range Deployment

Lightweight, rapid-deployment cyber range infrastructure using Docker containers.

## When to Use Docker

| Scenario | Docker | VMs | Rationale |
|----------|--------|-----|-----------|
| Grey zone services | ✅ | ⚪ | DNS/web/mail don't need full OS |
| Red team C2 | ✅ | ⚪ | Ephemeral, disposable infrastructure |
| NPC traffic generation | ✅ | ⚪ | Lightweight, scalable |
| Windows workstations | ❌ | ✅ | Requires full Windows OS |
| Active Directory | ❌ | ✅ | Domain services need Windows Server |
| SIEM/EDR evaluation | ⚪ | ✅ | Some tools expect full OS |
| Rapid prototyping | ✅ | ⚪ | Seconds to deploy vs minutes |
| CI/CD integration | ✅ | ⚪ | Native container support |

## Architecture: Hybrid Docker + VM Range

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CYBER RANGE ARCHITECTURE                        │
│                           (Hybrid Docker + VM)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    DOCKER HOST / SWARM                           │   │
│  │                                                                   │   │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │   │
│  │   │  GREY ZONE  │  │  RED ZONE   │  │ WHITE ZONE  │            │   │
│  │   │  Containers │  │  Containers │  │  Containers │            │   │
│  │   │             │  │             │  │             │            │   │
│  │   │ dns-root    │  │ mythic-c2   │  │ scenario-api│            │   │
│  │   │ dns-tld-com │  │ covenant    │  │ automation  │            │   │
│  │   │ web-farm-*  │  │ redirectors │  │ guacamole   │            │   │
│  │   │ mail-relay  │  │ gophish     │  │ scoring     │            │   │
│  │   │ isp-router  │  │ attack-box  │  │             │            │   │
│  │   └─────────────┘  └─────────────┘  └─────────────┘            │   │
│  │                                                                   │   │
│  │   Docker Networks: grey-net, red-net, white-net, range-backbone  │   │
│  │                                                                   │   │
│  └───────────────────────────────────┬───────────────────────────────┘   │
│                                      │                                   │
│                              range-backbone                              │
│                                      │                                   │
│  ┌───────────────────────────────────┴───────────────────────────────┐   │
│  │                         VM HYPERVISOR                             │   │
│  │                    (Proxmox / VMware / KVM)                       │   │
│  │                                                                   │   │
│  │   ┌─────────────────────────────────────────────────────────┐   │   │
│  │   │                      BLUE ZONE VMs                       │   │   │
│  │   │                                                           │   │   │
│  │   │   DC01          DC02          SIEM         EDR-Console   │   │   │
│  │   │   Win2022       Win2022       Ubuntu       Win2022       │   │   │
│  │   │                                                           │   │   │
│  │   │   WKS-01        WKS-02        WKS-03       FileServer    │   │   │
│  │   │   Win11         Win11         Win11        Win2022       │   │   │
│  │   │                                                           │   │   │
│  │   └─────────────────────────────────────────────────────────┘   │   │
│  │                                                                   │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Docker Compose: Grey Zone

Complete grey zone deployment with DNS hierarchy and web services.

```yaml
# grey-zone/docker-compose.yml
version: "3.9"

networks:
  grey-internal:
    driver: bridge
    ipam:
      config:
        - subnet: 10.50.0.0/16
          gateway: 10.50.0.1
  range-backbone:
    external: true

services:
  # ==========================================================================
  # DNS HIERARCHY
  # ==========================================================================
  
  dns-root:
    build: ./dns-root
    container_name: dns-root
    hostname: a.root-servers.net
    networks:
      grey-internal:
        ipv4_address: 10.50.1.10
    volumes:
      - ./dns-root/zones:/etc/bind/zones:ro
    restart: unless-stopped
    
  dns-tld-com:
    build: ./dns-tld
    container_name: dns-tld-com
    hostname: a.gtld-servers.net
    environment:
      - TLD=com
    networks:
      grey-internal:
        ipv4_address: 10.50.1.20
    volumes:
      - ./dns-tld/zones/com:/etc/bind/zones:ro
    depends_on:
      - dns-root
    restart: unless-stopped
    
  dns-tld-org:
    build: ./dns-tld
    container_name: dns-tld-org
    hostname: a0.org.afilias-nst.info
    environment:
      - TLD=org
    networks:
      grey-internal:
        ipv4_address: 10.50.1.21
    volumes:
      - ./dns-tld/zones/org:/etc/bind/zones:ro
    depends_on:
      - dns-root
    restart: unless-stopped

  dns-tld-net:
    build: ./dns-tld
    container_name: dns-tld-net
    hostname: a.gtld-servers.net
    environment:
      - TLD=net
    networks:
      grey-internal:
        ipv4_address: 10.50.1.22
    volumes:
      - ./dns-tld/zones/net:/etc/bind/zones:ro
    depends_on:
      - dns-root
    restart: unless-stopped

  # Authoritative DNS for simulated domains
  dns-auth-google:
    build: ./dns-auth
    container_name: dns-auth-google
    environment:
      - DOMAIN=google.com
    networks:
      grey-internal:
        ipv4_address: 10.50.1.100
    volumes:
      - ./dns-auth/zones/google.com:/etc/bind/zones:ro
    restart: unless-stopped

  dns-auth-microsoft:
    build: ./dns-auth
    container_name: dns-auth-microsoft
    environment:
      - DOMAIN=microsoft.com
    networks:
      grey-internal:
        ipv4_address: 10.50.1.101
    volumes:
      - ./dns-auth/zones/microsoft.com:/etc/bind/zones:ro
    restart: unless-stopped

  # ==========================================================================
  # WEB CONTENT FARMS
  # ==========================================================================
  
  web-news:
    image: nginx:alpine
    container_name: web-news
    networks:
      grey-internal:
        ipv4_address: 10.50.2.10
    volumes:
      - ./web-content/news:/usr/share/nginx/html:ro
      - ./nginx/news.conf:/etc/nginx/conf.d/default.conf:ro
    restart: unless-stopped

  web-social:
    image: nginx:alpine
    container_name: web-social
    networks:
      grey-internal:
        ipv4_address: 10.50.2.11
    volumes:
      - ./web-content/social:/usr/share/nginx/html:ro
    restart: unless-stopped

  web-banking:
    build: ./web-banking
    container_name: web-banking
    networks:
      grey-internal:
        ipv4_address: 10.50.2.12
    environment:
      - FLASK_ENV=production
    restart: unless-stopped

  web-corporate:
    image: nginx:alpine
    container_name: web-corporate
    networks:
      grey-internal:
        ipv4_address: 10.50.2.13
    volumes:
      - ./web-content/corporate:/usr/share/nginx/html:ro
    restart: unless-stopped

  # ==========================================================================
  # EMAIL INFRASTRUCTURE
  # ==========================================================================
  
  mail-relay:
    build: ./mail-relay
    container_name: mail-relay
    hostname: mail.grey.local
    networks:
      grey-internal:
        ipv4_address: 10.50.3.10
    ports:
      - "25:25"
    volumes:
      - mail-queue:/var/spool/postfix
    restart: unless-stopped

  # ==========================================================================
  # ISP SIMULATION
  # ==========================================================================
  
  isp-router:
    build: ./isp-router
    container_name: isp-router
    hostname: gw.isp-grey.net
    networks:
      grey-internal:
        ipv4_address: 10.50.0.1
      range-backbone:
        ipv4_address: 172.16.0.10
    cap_add:
      - NET_ADMIN
    sysctls:
      - net.ipv4.ip_forward=1
    restart: unless-stopped

  # ==========================================================================
  # CDN / CONTENT DELIVERY
  # ==========================================================================
  
  cdn-edge:
    image: nginx:alpine
    container_name: cdn-edge
    networks:
      grey-internal:
        ipv4_address: 10.50.4.10
    volumes:
      - ./cdn-content:/usr/share/nginx/html:ro
      - ./nginx/cdn.conf:/etc/nginx/conf.d/default.conf:ro
    restart: unless-stopped

volumes:
  mail-queue:
```

### DNS Root Server Dockerfile

```dockerfile
# grey-zone/dns-root/Dockerfile
FROM alpine:3.19

RUN apk add --no-cache bind bind-tools

COPY named.conf /etc/bind/named.conf
COPY zones/ /etc/bind/zones/

EXPOSE 53/tcp 53/udp

CMD ["named", "-g", "-c", "/etc/bind/named.conf"]
```

### DNS Root Zone File

```zone
; grey-zone/dns-root/zones/root.zone
$TTL 86400
@   IN  SOA     a.root-servers.net. admin.root-servers.net. (
                2024010101  ; Serial
                3600        ; Refresh
                1800        ; Retry
                604800      ; Expire
                86400 )     ; Minimum TTL

; Root servers (simplified - just our simulated one)
@           IN  NS      a.root-servers.net.
a.root-servers.net.  IN  A   10.50.1.10

; TLD delegations
com.        IN  NS      a.gtld-servers.net.
a.gtld-servers.net.  IN  A   10.50.1.20

org.        IN  NS      a0.org.afilias-nst.info.
a0.org.afilias-nst.info.  IN  A   10.50.1.21

net.        IN  NS      a.gtld-servers.net.
; Reuse same server for .net in simulation
```

## Docker Compose: Red Zone

Adversary infrastructure with C2 frameworks and attack tools.

```yaml
# red-zone/docker-compose.yml
version: "3.9"

networks:
  red-internal:
    driver: bridge
    ipam:
      config:
        - subnet: 10.66.0.0/16
          gateway: 10.66.0.1
  range-backbone:
    external: true

services:
  # ==========================================================================
  # C2 FRAMEWORKS
  # ==========================================================================
  
  mythic:
    image: ghcr.io/its-a-feature/mythic_server:latest
    container_name: mythic-c2
    hostname: mythic.red.local
    networks:
      red-internal:
        ipv4_address: 10.66.1.10
    ports:
      - "7443:7443"   # Web UI
      - "17443:17443" # API
    volumes:
      - mythic-data:/mythic
    environment:
      - MYTHIC_ADMIN_USER=admin
      - MYTHIC_ADMIN_PASSWORD=mythic_password_change_me
    restart: unless-stopped

  # Sliver C2
  sliver:
    image: ghcr.io/bishopfox/sliver:latest
    container_name: sliver-c2
    hostname: sliver.red.local
    networks:
      red-internal:
        ipv4_address: 10.66.1.11
    ports:
      - "31337:31337"  # gRPC
      - "8888:8888"    # HTTP C2
      - "443:443"      # HTTPS C2
    volumes:
      - sliver-data:/root/.sliver
    restart: unless-stopped

  # ==========================================================================
  # REDIRECTORS
  # ==========================================================================
  
  redirector-http:
    build: ./redirector
    container_name: redirector-http
    networks:
      red-internal:
        ipv4_address: 10.66.2.10
      range-backbone:
        ipv4_address: 172.16.0.66
    environment:
      - BACKEND_HOST=10.66.1.10
      - BACKEND_PORT=80
      - LISTEN_PORT=80
    restart: unless-stopped

  redirector-https:
    build: ./redirector
    container_name: redirector-https
    networks:
      red-internal:
        ipv4_address: 10.66.2.11
      range-backbone:
        ipv4_address: 172.16.0.67
    environment:
      - BACKEND_HOST=10.66.1.10
      - BACKEND_PORT=443
      - LISTEN_PORT=443
    volumes:
      - ./certs:/etc/nginx/certs:ro
    restart: unless-stopped

  # ==========================================================================
  # PHISHING INFRASTRUCTURE
  # ==========================================================================
  
  gophish:
    image: gophish/gophish:latest
    container_name: gophish
    hostname: phish.red.local
    networks:
      red-internal:
        ipv4_address: 10.66.3.10
    ports:
      - "3333:3333"   # Admin
      - "8080:8080"   # Phishing
    volumes:
      - gophish-data:/opt/gophish/data
    restart: unless-stopped

  evilginx2:
    build: ./evilginx
    container_name: evilginx2
    hostname: evilginx.red.local
    networks:
      red-internal:
        ipv4_address: 10.66.3.11
    ports:
      - "53:53/udp"
      - "80:80"
      - "443:443"
    cap_add:
      - NET_ADMIN
    restart: unless-stopped

  # ==========================================================================
  # ATTACK BOXES
  # ==========================================================================
  
  kali:
    image: kalilinux/kali-rolling
    container_name: kali-attack
    hostname: kali.red.local
    networks:
      red-internal:
        ipv4_address: 10.66.4.10
    volumes:
      - kali-home:/root
      - ./payloads:/payloads
    cap_add:
      - NET_ADMIN
      - SYS_ADMIN
    stdin_open: true
    tty: true
    command: /bin/bash
    restart: unless-stopped

  # Commando VM style Windows attack (via Wine or nested)
  commando-tools:
    build: ./commando
    container_name: commando-tools
    hostname: commando.red.local
    networks:
      red-internal:
        ipv4_address: 10.66.4.11
    volumes:
      - commando-data:/opt/tools
    restart: unless-stopped

volumes:
  mythic-data:
  sliver-data:
  gophish-data:
  kali-home:
  commando-data:
```

## Docker Compose: NPC Traffic Generator

Lightweight traffic generation containers.

```yaml
# npc-traffic/docker-compose.yml
version: "3.9"

networks:
  range-backbone:
    external: true

services:
  # ==========================================================================
  # WEB BROWSING NPCs
  # ==========================================================================
  
  npc-browser-1:
    build: ./browser-npc
    container_name: npc-browser-1
    networks:
      range-backbone:
    environment:
      - NPC_ID=1
      - BROWSE_RATE=30  # seconds between requests
      - INTERNAL_RATIO=0.7
    volumes:
      - ./config/urls.yaml:/app/urls.yaml:ro
    restart: unless-stopped

  npc-browser-2:
    build: ./browser-npc
    container_name: npc-browser-2
    networks:
      range-backbone:
    environment:
      - NPC_ID=2
      - BROWSE_RATE=45
      - INTERNAL_RATIO=0.6
    volumes:
      - ./config/urls.yaml:/app/urls.yaml:ro
    restart: unless-stopped

  # Scale with replicas
  npc-browser-pool:
    build: ./browser-npc
    deploy:
      replicas: 10
    networks:
      range-backbone:
    environment:
      - BROWSE_RATE=60
      - INTERNAL_RATIO=0.7
    volumes:
      - ./config/urls.yaml:/app/urls.yaml:ro
    restart: unless-stopped

  # ==========================================================================
  # DNS QUERY GENERATORS
  # ==========================================================================
  
  npc-dns:
    build: ./dns-npc
    container_name: npc-dns
    networks:
      range-backbone:
    environment:
      - DNS_SERVER=10.50.1.10
      - QUERY_RATE=10  # queries per minute
    volumes:
      - ./config/domains.txt:/app/domains.txt:ro
    restart: unless-stopped

  # ==========================================================================
  # EMAIL TRAFFIC
  # ==========================================================================
  
  npc-email:
    build: ./email-npc
    container_name: npc-email
    networks:
      range-backbone:
    environment:
      - SMTP_SERVER=10.50.3.10
      - SEND_RATE=5  # emails per hour
    volumes:
      - ./config/email-templates:/app/templates:ro
    restart: unless-stopped

  # ==========================================================================
  # FILE ACCESS (SMB simulation via API)
  # ==========================================================================
  
  npc-fileaccess:
    build: ./file-npc
    container_name: npc-fileaccess
    networks:
      range-backbone:
    environment:
      - FILESERVER=192.168.101.20
      - ACCESS_RATE=30
    restart: unless-stopped
```

### Browser NPC Dockerfile

```dockerfile
# npc-traffic/browser-npc/Dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    playwright \
    pyyaml \
    aiohttp

RUN playwright install chromium

WORKDIR /app
COPY npc_browser.py .
COPY requirements.txt .

CMD ["python", "-u", "npc_browser.py"]
```

### Browser NPC Script

```python
#!/usr/bin/env python3
# npc-traffic/browser-npc/npc_browser.py
"""
NPC Browser Traffic Generator

Simulates realistic user web browsing behavior.
"""

import asyncio
import os
import random
import yaml
from datetime import datetime
from playwright.async_api import async_playwright

# Configuration from environment
NPC_ID = os.getenv("NPC_ID", "0")
BROWSE_RATE = int(os.getenv("BROWSE_RATE", "30"))
INTERNAL_RATIO = float(os.getenv("INTERNAL_RATIO", "0.7"))

# Load URL configuration
def load_urls(config_path: str = "/app/urls.yaml") -> dict:
    """Load URL lists from configuration file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        # Default URLs if config not provided
        return {
            "internal": [
                "http://intranet.corp.local",
                "http://sharepoint.corp.local",
                "http://hr.corp.local",
            ],
            "external": [
                "http://10.50.2.10",  # Grey zone news
                "http://10.50.2.11",  # Grey zone social
                "http://10.50.2.13",  # Grey zone corporate
            ]
        }

async def browse_page(page, url: str):
    """Visit a page and perform realistic interactions."""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        # Random scroll behavior
        scroll_count = random.randint(1, 5)
        for _ in range(scroll_count):
            scroll_amount = random.randint(100, 500)
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # Sometimes click a link
        if random.random() > 0.6:
            links = await page.query_selector_all("a[href^='http'], a[href^='/']")
            if links and len(links) > 0:
                try:
                    link = random.choice(links[:10])  # Limit to first 10 links
                    await link.click(timeout=5000)
                    await asyncio.sleep(random.uniform(1.0, 3.0))
                except Exception:
                    pass  # Ignore click failures
                    
        # Dwell time on page
        await asyncio.sleep(random.uniform(5.0, 30.0))
        
    except Exception as e:
        print(f"[NPC-{NPC_ID}] Browse error for {url}: {e}")

async def run_npc():
    """Main NPC browsing loop."""
    urls = load_urls()
    internal_urls = urls.get("internal", [])
    external_urls = urls.get("external", [])
    
    print(f"[NPC-{NPC_ID}] Starting browser NPC")
    print(f"[NPC-{NPC_ID}] Internal URLs: {len(internal_urls)}")
    print(f"[NPC-{NPC_ID}] External URLs: {len(external_urls)}")
    print(f"[NPC-{NPC_ID}] Browse rate: {BROWSE_RATE}s, Internal ratio: {INTERNAL_RATIO}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()
        
        while True:
            # Select URL based on internal/external ratio
            if random.random() < INTERNAL_RATIO and internal_urls:
                url = random.choice(internal_urls)
                url_type = "internal"
            elif external_urls:
                url = random.choice(external_urls)
                url_type = "external"
            else:
                continue
                
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[NPC-{NPC_ID}] [{timestamp}] Browsing {url_type}: {url}")
            
            await browse_page(page, url)
            
            # Variable delay with jitter
            delay = BROWSE_RATE + random.uniform(-BROWSE_RATE/4, BROWSE_RATE/4)
            await asyncio.sleep(max(5, delay))

if __name__ == "__main__":
    asyncio.run(run_npc())
```

## Orchestration: Full Range Deployment

Master compose file that brings up all zones.

```yaml
# docker-compose.yml (root)
version: "3.9"

# Create the backbone network first
networks:
  range-backbone:
    driver: bridge
    ipam:
      config:
        - subnet: 172.16.0.0/16
          gateway: 172.16.0.1

include:
  - grey-zone/docker-compose.yml
  - red-zone/docker-compose.yml
  - npc-traffic/docker-compose.yml
```

### Deployment Script

```bash
#!/bin/bash
# deploy-range.sh
# Deploy Docker-based cyber range components

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse arguments
ACTION="${1:-help}"
ZONE="${2:-all}"

case "$ACTION" in
    up)
        log_info "Deploying range zone: $ZONE"
        
        if [[ "$ZONE" == "all" ]]; then
            # Create backbone network first
            docker network create range-backbone 2>/dev/null || true
            
            # Deploy in order
            docker compose -f grey-zone/docker-compose.yml up -d
            docker compose -f red-zone/docker-compose.yml up -d
            docker compose -f npc-traffic/docker-compose.yml up -d
        else
            docker compose -f "${ZONE}-zone/docker-compose.yml" up -d
        fi
        
        log_info "Deployment complete"
        ;;
        
    down)
        log_info "Stopping range zone: $ZONE"
        
        if [[ "$ZONE" == "all" ]]; then
            docker compose -f npc-traffic/docker-compose.yml down
            docker compose -f red-zone/docker-compose.yml down
            docker compose -f grey-zone/docker-compose.yml down
        else
            docker compose -f "${ZONE}-zone/docker-compose.yml" down
        fi
        ;;
        
    status)
        log_info "Range status:"
        echo ""
        echo "=== Grey Zone ==="
        docker compose -f grey-zone/docker-compose.yml ps
        echo ""
        echo "=== Red Zone ==="
        docker compose -f red-zone/docker-compose.yml ps
        echo ""
        echo "=== NPC Traffic ==="
        docker compose -f npc-traffic/docker-compose.yml ps
        ;;
        
    reset)
        log_info "Resetting range zone: $ZONE"
        
        if [[ "$ZONE" == "all" ]]; then
            $0 down all
            docker volume prune -f
            $0 up all
        else
            docker compose -f "${ZONE}-zone/docker-compose.yml" down -v
            docker compose -f "${ZONE}-zone/docker-compose.yml" up -d
        fi
        
        log_info "Reset complete"
        ;;
        
    logs)
        CONTAINER="${3:-}"
        if [[ -n "$CONTAINER" ]]; then
            docker logs -f "$CONTAINER"
        else
            docker compose -f "${ZONE}-zone/docker-compose.yml" logs -f
        fi
        ;;
        
    health)
        log_info "Running health checks..."
        
        # DNS root check
        if docker exec dns-root dig @127.0.0.1 . NS +short > /dev/null 2>&1; then
            log_info "✅ DNS Root: OK"
        else
            log_error "❌ DNS Root: FAIL"
        fi
        
        # Web services check
        for container in web-news web-social web-banking; do
            if docker exec "$container" wget -q -O /dev/null http://localhost/ 2>/dev/null; then
                log_info "✅ $container: OK"
            else
                log_warn "⚠️  $container: DEGRADED"
            fi
        done
        
        # C2 check
        if docker exec mythic-c2 curl -sk https://localhost:7443 > /dev/null 2>&1; then
            log_info "✅ Mythic C2: OK"
        else
            log_warn "⚠️  Mythic C2: DEGRADED (may still be starting)"
        fi
        ;;
        
    help|*)
        echo "Usage: $0 <action> [zone]"
        echo ""
        echo "Actions:"
        echo "  up [zone]      - Deploy range (zone: grey, red, npc, all)"
        echo "  down [zone]    - Stop range"
        echo "  status         - Show container status"
        echo "  reset [zone]   - Reset range (recreate containers)"
        echo "  logs [zone]    - Follow logs"
        echo "  health         - Run health checks"
        echo ""
        echo "Examples:"
        echo "  $0 up all      - Deploy full range"
        echo "  $0 up grey     - Deploy grey zone only"
        echo "  $0 reset red   - Reset red zone"
        ;;
esac
```

## Resource Requirements

### Minimal Docker Range

| Component | Containers | Memory | CPU |
|-----------|------------|--------|-----|
| Grey Zone | 10-15 | 4 GB | 2 cores |
| Red Zone | 5-8 | 4 GB | 2 cores |
| NPC Traffic | 5-20 | 2 GB | 1 core |
| **Total** | 20-43 | **10 GB** | **5 cores** |

### Recommended Docker Host

- **CPU**: 8+ cores
- **RAM**: 32 GB (allows headroom for burst)
- **Disk**: 100 GB SSD (container images + volumes)
- **Network**: 1 Gbps (10 Gbps for high-fidelity)

## Limitations and Mitigations

| Limitation | Mitigation |
|------------|------------|
| No Windows containers | Hybrid approach: Docker for Linux services, VMs for Windows |
| Shared kernel | Use user namespaces for isolation; accept for training scenarios |
| Limited network realism | Use macvlan networks for L2 realism; accept for most scenarios |
| No BIOS/firmware | Accept; not required for most exercises |
| Container escape risk | Run range on dedicated host; use gVisor/Kata for high-security |
