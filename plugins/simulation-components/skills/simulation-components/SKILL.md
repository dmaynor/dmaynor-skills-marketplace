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
author: dmaynor
version: 1.1.0
date: 2026-03-29
---

# Simulation Components

Create modular, deployable virtualized services that combine into coherent cyber range simulations.

## Problem

Cyber range exercises require realistic organizational infrastructure -- DNS, web services, email, Active Directory -- but building these from scratch for every exercise is time-consuming and produces inconsistent, low-fidelity environments. Without parameterized, composable building blocks that generate contextually appropriate content for a given industry and organization, exercise environments feel artificial and fail to train defenders on realistic scenarios.

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

## Generation Workflow

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
docker compose up -d

# AD population (on domain controller)
powershell -File Populate-AD.ps1
```

## Extending Components

### Add New Industry Sector

Add content templates to the relevant generator scripts (`gen_web_org.py`, `gen_dns_org.py`). See `reference.md` for detailed examples.

### Add New Component

1. Create generator script accepting `--context` and `--output` arguments
2. Register in orchestrator (see `reference.md` for registration pattern)

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

## Verification

1. Confirm all generated Docker containers start successfully: `docker compose up -d` completes with exit code 0 and all services show "running" in `docker compose ps`.
2. Verify DNS resolution works end-to-end: `dig @<dns-container-ip> www.<domain>` returns the expected A record from the generated zone file.
3. Confirm the web component serves pages: `curl http://<web-container-ip>/` returns HTML with the organization name and branding colors from the context file.
4. Validate AD population script runs without errors on a domain controller: `Populate-AD.ps1` creates the expected number of users, groups, and OUs matching the organization context headcounts.
5. Verify inter-component connectivity: the web component's DNS name resolves via the DNS component, and email MX records point to the email component's IP.

## Notes

- Full YAML schemas, detailed component specifications, multi-organization scenarios, Docker configs, and AD population details are in `reference.md`
