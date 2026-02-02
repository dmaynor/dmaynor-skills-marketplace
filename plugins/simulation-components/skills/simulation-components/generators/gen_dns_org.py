#!/usr/bin/env python3
"""
DNS Organization Component Generator

Generates authoritative DNS zone files and Docker deployment
for a simulated organization based on organization context.

Usage:
    python gen_dns_org.py --context org-context.yaml --output ./dns-org/
"""

import argparse
from datetime import datetime
from pathlib import Path

import yaml


def load_context(context_path: Path) -> dict:
    with open(context_path, 'r') as f:
        return yaml.safe_load(f)


def generate_serial() -> str:
    return datetime.now().strftime("%Y%m%d") + "01"


def calculate_ips(base_range: str) -> dict:
    base = base_range.split('/')[0]
    prefix = '.'.join(base.split('.')[:3])
    return {
        'ns1_ip': f"{prefix}.2", 'ns2_ip': f"{prefix}.3",
        'www_ip': f"{prefix}.10", 'mail_ip': f"{prefix}.20",
        'mail2_ip': f"{prefix}.21", 'vpn_ip': f"{prefix}.30",
        'portal_ip': f"{prefix}.40",
    }


INDUSTRY_RECORDS = {
    'financial_services': """
; Financial services
trading         IN  A       {prefix}.100
bloomberg       IN  A       {prefix}.101
reuters         IN  A       {prefix}.102
clientportal    IN  A       {prefix}.110
wireroom        IN  A       {prefix}.120
""",
    'healthcare': """
; Healthcare services
ehr             IN  A       {prefix}.100
pacs            IN  A       {prefix}.101
pharmacy        IN  A       {prefix}.102
patientportal   IN  A       {prefix}.120
telehealth      IN  A       {prefix}.121
""",
    'manufacturing': """
; Manufacturing services
scada           IN  A       {prefix}.100
mes             IN  A       {prefix}.101
erp             IN  A       {prefix}.102
plm             IN  A       {prefix}.110
""",
    'defense': """
; Defense services
sipr-gateway    IN  A       {prefix}.100
c2              IN  A       {prefix}.101
intel           IN  A       {prefix}.102
training        IN  A       {prefix}.121
""",
    'energy': """
; Energy services
scada           IN  A       {prefix}.100
ems             IN  A       {prefix}.101
oms             IN  A       {prefix}.102
gis             IN  A       {prefix}.120
""",
}


def generate_external_zone(context: dict) -> str:
    org = context['organization']
    domain = org['domain']
    external_range = org.get('network', {}).get('external_ip_range', '203.0.113.0/24')
    ips = calculate_ips(external_range)
    prefix = '.'.join(external_range.split('/')[0].split('.')[:3])
    sector = org.get('industry', {}).get('sector', 'generic')
    
    zone = f"""; Zone file for {domain}
; Generated: {datetime.now().isoformat()}
; Organization: {org['name']}

$TTL 86400
$ORIGIN {domain}.

@   IN  SOA     ns1.{domain}. admin.{domain}. (
                {generate_serial()}  ; Serial
                3600    ; Refresh
                1800    ; Retry
                604800  ; Expire
                86400 ) ; Minimum TTL

; Name servers
@           IN  NS      ns1.{domain}.
@           IN  NS      ns2.{domain}.
ns1         IN  A       {ips['ns1_ip']}
ns2         IN  A       {ips['ns2_ip']}

; MX records
@           IN  MX  10  mail.{domain}.
@           IN  MX  20  mail2.{domain}.

; SPF/DMARC
@           IN  TXT     "v=spf1 mx -all"
_dmarc      IN  TXT     "v=DMARC1; p=quarantine"

; Standard services
www         IN  A       {ips['www_ip']}
mail        IN  A       {ips['mail_ip']}
mail2       IN  A       {ips['mail2_ip']}
vpn         IN  A       {ips['vpn_ip']}
portal      IN  A       {ips['portal_ip']}
autodiscover IN A       {ips['mail_ip']}
"""
    
    # Add industry-specific records
    industry_zone = INDUSTRY_RECORDS.get(sector, """
; General services
app1            IN  A       {prefix}.100
api             IN  A       {prefix}.102
""")
    zone += industry_zone.format(prefix=prefix)
    
    return zone


def generate_internal_zone(context: dict) -> str:
    org = context['organization']
    internal_domain = org.get('internal_domain', f"{org['short_name'].lower()}.local")
    internal_range = org.get('network', {}).get('internal_ip_range', '10.10.0.0/16')
    prefix = '.'.join(internal_range.split('/')[0].split('.')[:2])
    
    zone = f"""; Internal zone for {internal_domain}
; Generated: {datetime.now().isoformat()}

$TTL 86400
$ORIGIN {internal_domain}.

@   IN  SOA     dc01.{internal_domain}. admin.{internal_domain}. (
                {generate_serial()}
                3600  1800  604800  86400 )

@           IN  NS      dc01.{internal_domain}.
@           IN  NS      dc02.{internal_domain}.

; Domain controllers
dc01        IN  A       {prefix}.1.10
dc02        IN  A       {prefix}.1.11

; Infrastructure
sccm        IN  A       {prefix}.1.20
wsus        IN  A       {prefix}.1.21
siem        IN  A       {prefix}.1.30
edr         IN  A       {prefix}.1.31
fileserver  IN  A       {prefix}.2.10

"""
    
    # Department servers
    for i, dept in enumerate(org.get('structure', {}).get('departments', [])):
        pfx = dept.get('prefix', 'DEPT').lower()
        zone += f"{pfx}-app    IN  A       {prefix}.3.{100+i}\n"
    
    return zone


def generate_dockerfile() -> str:
    return """FROM alpine:3.19
RUN apk add --no-cache bind bind-tools
COPY zones/ /etc/bind/zones/
COPY named.conf /etc/bind/named.conf
RUN named-checkconf /etc/bind/named.conf
EXPOSE 53/tcp 53/udp
HEALTHCHECK --interval=30s --timeout=5s CMD dig @127.0.0.1 localhost +short || exit 1
CMD ["named", "-g", "-c", "/etc/bind/named.conf", "-u", "named"]
"""


def generate_named_conf(domain: str, internal_domain: str) -> str:
    return f"""options {{
    directory "/var/bind";
    listen-on {{ any; }};
    allow-query {{ any; }};
    recursion no;
}};

zone "{domain}" {{ type master; file "/etc/bind/zones/{domain}.zone"; }};
zone "{internal_domain}" {{ type master; file "/etc/bind/zones/{internal_domain}.zone"; }};
"""


def generate_compose(domain: str) -> str:
    safe = domain.replace('.', '-')
    return f"""version: "3.9"
services:
  dns-{safe}:
    build: .
    container_name: dns-{safe}
    hostname: ns1.{domain}
    networks:
      range-backbone:
    restart: unless-stopped

networks:
  range-backbone:
    external: true
"""


def main():
    parser = argparse.ArgumentParser(description="Generate DNS component")
    parser.add_argument('--context', '-c', type=Path, required=True)
    parser.add_argument('--output', '-o', type=Path, default=Path('./dns-org'))
    args = parser.parse_args()
    
    context = load_context(args.context)
    org = context['organization']
    
    output = args.output
    zones = output / 'zones'
    zones.mkdir(parents=True, exist_ok=True)
    
    domain = org['domain']
    internal = org.get('internal_domain', f"{org['short_name'].lower()}.local")
    
    (zones / f"{domain}.zone").write_text(generate_external_zone(context))
    (zones / f"{internal}.zone").write_text(generate_internal_zone(context))
    (output / 'Dockerfile').write_text(generate_dockerfile())
    (output / 'named.conf').write_text(generate_named_conf(domain, internal))
    (output / 'docker-compose.yml').write_text(generate_compose(domain))
    
    print(f"Generated DNS component: {output}")
    print(f"  External: {domain}")
    print(f"  Internal: {internal}")


if __name__ == "__main__":
    main()
