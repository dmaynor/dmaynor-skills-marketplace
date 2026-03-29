---
parent: SKILL.md
---

# Simulation Components Reference

Full YAML schemas, detailed component specifications, multi-organization scenario examples, Docker configs, and AD population details.

## Organization Context Schema

All components consume a standard organization context file:

```yaml
organization:
  name: "Meridian Financial Services"
  short_name: "Meridian"
  domain: "meridianfs.com"
  internal_domain: "meridian.local"

  industry:
    sector: "financial_services"    # Drives content generation
    subsector: "investment_banking"

  size:
    employees: 2500
    locations: 5

  geography:
    headquarters: "New York, NY"
    country: "US"
    timezone: "America/New_York"

  structure:
    departments:
      - name: "Executive"
        headcount: 15
        prefix: "EXEC"
      - name: "Trading"
        headcount: 200
        prefix: "TRD"
      - name: "Technology"
        headcount: 300
        prefix: "TECH"
      # ... more departments

  network:
    external_ip_range: "203.0.113.0/24"
    internal_ip_range: "10.10.0.0/16"
    dmz_range: "172.16.0.0/24"

  branding:
    primary_color: "#1a365d"
    secondary_color: "#e2e8f0"
    logo_text: "MERIDIAN"
    tagline: "Building Tomorrow's Wealth Today"
```

## Component Details

### DNS Organization (`gen_dns_org.py`)

Generates complete DNS infrastructure:

**External Zone** (`meridianfs.com`):
- SOA, NS records
- MX records with SPF/DMARC
- Standard services (www, mail, vpn, portal)
- Industry-specific records (trading, clientportal for finance)

**Internal Zone** (`meridian.local`):
- Domain controller records
- Core infrastructure (SCCM, WSUS, SIEM)
- Department-specific application servers
- Printer records

**Output**:
```
dns-org/
├── Dockerfile
├── docker-compose.yml
├── named.conf
└── zones/
    ├── meridianfs.com.zone
    └── meridian.local.zone
```

### Web Organization (`gen_web_org.py`)

Generates industry-appropriate website:

**Pages**:
- Homepage with hero, services, news
- About page with org description
- Industry-specific navigation and content

**Branding**:
- CSS using organization colors
- Industry-appropriate imagery references
- Realistic news/press releases

**Output**:
```
web-org/
├── Dockerfile
├── docker-compose.yml
└── html/
    ├── index.html
    ├── about.html
    └── css/
        └── style.css
```

### AD Population (`gen_ad_population.py`)

Generates Active Directory structure:

**Organizational Units**:
- Users (with department sub-OUs)
- Groups
- Computers (Servers, Workstations)
- Service Accounts

**Users**:
- Realistic names (diverse name pool)
- Department assignment
- Job titles appropriate to department
- Manager relationships
- Unique usernames and employee IDs

**Groups**:
- Department groups (GRP_TECH_Users)
- Manager groups (GRP_TECH_Managers)
- Global groups (All_Employees, VPN_Users)

**Output**:
```
ad-population/
├── Populate-AD.ps1
├── users.csv
└── groups.csv
```

## Multi-Organization Scenarios

### Combining Components

```bash
# Target organization (Blue team defends)
python generators/orchestrate.py \
    --context target-corp.yaml \
    --output ./range/target/

# Partner organization (supply chain)
python generators/orchestrate.py \
    --context partner.yaml \
    --output ./range/partner/

# Attacker infrastructure (Red team uses)
python generators/orchestrate.py \
    --context attacker-front.yaml \
    --output ./range/attacker/
```

### Grey Zone Internet

```bash
# Multiple "Internet" organizations
for org in google microsoft amazon cloudflare; do
    python generators/gen_dns_org.py \
        --context templates/internet/${org}.yaml \
        --output ./grey-zone/dns-${org}/
done

# Combine into grey zone compose
python generators/combine_grey.py --output ./grey-zone/
```

## Extending Components

### Add New Industry Sector

1. Add content templates to generator:

```python
# In gen_web_org.py
INDUSTRY_CONTENT['new_sector'] = {
    'nav_items': ['Products', 'Services', ...],
    'hero_headlines': [...],
    'services': [...],
    'news_topics': [...],
}
```

2. Add DNS records:

```python
# In gen_dns_org.py
def generate_industry_records(industry, domain, base_ip):
    if sector == 'new_sector':
        records += f"""
sector_app  IN  A   {prefix}.100
...
"""
```

### Add New Component

1. Create generator script following pattern:
   - Accept `--context` and `--output` arguments
   - Load organization context
   - Generate industry-aware content
   - Output deployable artifacts

2. Register in orchestrator:

```python
AVAILABLE_COMPONENTS['new_component'] = {
    'script': 'gen_new_component.py',
    'description': 'Description here',
    'output_dir': 'new-component',
}
```
