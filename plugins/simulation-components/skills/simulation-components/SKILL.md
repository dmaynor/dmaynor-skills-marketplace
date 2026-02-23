---
name: simulation-components
description: >-
  Create modular, composable virtualized roles and services for cyber range
  simulations. Generates complete, deployable components that combine into
  larger exercise environments. Triggers on "create a simulated X", "build me a
  fake Y", "generate org content", or requests for DNS infrastructure, realistic
  web content, email infrastructure, Active Directory population, NPC personas,
  or combining services into coherent simulations. Outputs: Docker containers,
  zone files, web content, AD population scripts, NPC configs.
---

# Simulation Components

Create modular, deployable virtualized services that combine into coherent cyber range simulations.

## Core Concept

Simulation components are **self-contained, parameterized building blocks** that:

1. Accept organization context (name, industry, size, structure)
2. Generate contextually appropriate content and configuration
3. Deploy via Docker or integrate with VMs
4. Interconnect with other components via standard interfaces
5. Reset to known state instantly

```
┌─────────────────────────────────────────────────────────────────────┐
│                    COMPONENT COMPOSITION                            │
│                                                                     │
│   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐          │
│   │   DNS   │ + │   WEB   │ + │  EMAIL  │ + │   AD    │ = SIMULATION
│   │Component│   │Component│   │Component│   │Component│          │
│   └─────────┘   └─────────┘   └─────────┘   └─────────┘          │
│        │             │             │             │                 │
│        └─────────────┴──────┬──────┴─────────────┘                 │
│                             │                                       │
│                    ┌────────┴────────┐                             │
│                    │  Organization   │                             │
│                    │    Context      │                             │
│                    └─────────────────┘                             │
└─────────────────────────────────────────────────────────────────────┘
```

## When to Use

- Building new cyber range scenarios
- Creating industry-specific training environments
- Generating realistic content for exercises
- Populating AD with contextually appropriate users/groups
- Simulating supply chain or partner organizations
- Creating grey zone "Internet" services

## Component Catalog

| Component | Purpose | Output |
|-----------|---------|--------|
| `dns-org` | Organization DNS (external + internal) | Docker + zone files |
| `web-org` | Organization website | Docker + HTML/CSS |
| `ad-population` | AD users, groups, OUs | PowerShell + CSV |
| `email-org` | Email infrastructure | Docker + configs |
| `npc-personas` | User profiles for traffic gen | YAML configs |
| `file-share` | Sample documents | Office docs, PDFs |

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

## Supported Industry Sectors

| Sector | Content Generated |
|--------|-------------------|
| `financial_services` | Trading systems, client portals, wire rooms, Bloomberg/Reuters |
| `healthcare` | EHR, PACS, pharmacy, patient portals, telehealth |
| `manufacturing` | SCADA, MES, ERP, PLM, quality systems |
| `defense` | C2, SIPR gateway, intel, logistics, training |
| `energy` | SCADA, EMS, OMS, DMS, GIS, metering |
| `retail` | POS, inventory, ecommerce, loyalty, warehouse |
| `generic` | Standard corporate services |

## Quick Start

### 1. Define Organization Context

```bash
# Use a template or create custom
cp templates/financial-services.yaml my-org.yaml
# Edit to customize
```

### 2. Generate Components

```bash
# Generate all components
python generators/orchestrate.py \
    --context my-org.yaml \
    --output ./my-simulation/

# Or generate specific components
python generators/gen_dns_org.py --context my-org.yaml --output ./dns/
python generators/gen_web_org.py --context my-org.yaml --output ./web/
python generators/gen_ad_population.py --context my-org.yaml --output ./ad/
```

### 3. Deploy

```bash
cd my-simulation

# Docker components
docker compose up -d

# AD population (on domain controller)
# Copy ad-population/ to DC, then:
powershell -File Populate-AD.ps1
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

## Combining Components

### Multi-Organization Scenario

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

## Resources

See `generators/` directory:
- `gen_dns_org.py` - DNS infrastructure generator
- `gen_web_org.py` - Website content generator
- `gen_ad_population.py` - AD population generator
- `orchestrate.py` - Multi-component orchestrator

See `templates/` directory:
- `financial-services.yaml` - Investment bank template
- `healthcare.yaml` - Hospital system template
- `defense-contractor.yaml` - Defense company template
- `manufacturing.yaml` - Manufacturing company template
- `energy.yaml` - Utility company template

See `examples/` directory:
- `complete-simulation/` - Full multi-component example
- `grey-zone-internet/` - Internet simulation example
