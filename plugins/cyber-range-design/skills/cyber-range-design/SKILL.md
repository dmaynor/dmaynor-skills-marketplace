---
name: cyber-range-design
description: |
  Design, architect, and implement high-fidelity cyber ranges for training and exercises.
  Based on SEI/CERT methodology with modern extensions for cloud, zero-trust, and AI-driven simulation.

  TRIGGERS - Use this skill when user:
  - Wants to design or build a cyber range
  - Needs architecture for cyber warfare exercises
  - Asks about range zones (red/blue/grey/white)
  - Wants to plan team-based cyber exercises
  - Needs NPC traffic generation strategies
  - Asks about range infrastructure (compute, storage, network)
  - Says "cyber range", "exercise environment", "training range", "simulation environment"
  - Wants to integrate ICS/SCADA/OT into a range
  - Needs to plan range resets or snapshot strategies
  - Asks about range fidelity or realism

  MODES: DESIGN (architecture), IMPLEMENT (build guidance), EXERCISE (execution planning)
---

# Cyber Range Design and Implementation

Design, build, and operate high-fidelity virtualized cyber ranges that maximize training value through realistic adversary simulation and enterprise environment replication.

## When to Use

- Designing new cyber range architectures
- Planning cyber warfare exercises
- Evaluating range infrastructure requirements
- Implementing zone-based network topologies
- Integrating NPC traffic generation
- Planning ICS/SCADA/OT range components
- Assessing range fidelity and realism
- Designing exercise automation and orchestration
- Planning cloud vs. on-premise range deployment

## When NOT to Use

- Production security infrastructure design (use standard enterprise architecture)
- Penetration testing methodology (use red team skills)
- Detection engineering without range context (use purple-teaming skill)
- Incident response procedures (use IR-specific frameworks)

## Core Concept

A cyber range is a fully interactive virtual instance of enterprise IT infrastructure dedicated to cyberwarfare training. Realism is the primary driver of training value—ranges must support "train as you fight" principles.

| Fidelity Level | Characteristics | Training Value |
|----------------|-----------------|----------------|
| Low | Basic networking, minimal services, no traffic | Limited—trivial to detect adversary |
| Medium | Core services, basic policies, scripted traffic | Moderate—builds tool familiarity |
| High | Production-replica configs, realistic NPCs, proper noise | High—develops operational intuition |
| Ultra | Threat intel-driven TTPs, adaptive adversary AI, full telemetry | Elite—nation-state operator development |

## Zone Architecture Model

### Zone Taxonomy

```
┌─────────────────────────────────────────────────────────────────┐
│                     OUT OF GAME                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │    CORE     │  │    WHITE    │  │   ACCESS    │             │
│  │ INFRA ZONE  │  │    ZONE     │  │    ZONE     │             │
│  │             │  │  (Exercise  │  │ (Participant│             │
│  │ Hypervisor  │  │   Admin)    │  │  Interface) │             │
│  │ Storage     │  │             │  │             │             │
│  │ Network     │  │ Automation  │  │ Web Portal  │             │
│  └─────────────┘  │ Timeline    │  │ VM Access   │             │
│                   │ Inject Ctrl │  │ Comms       │             │
│  ┌─────────────┐  └─────────────┘  └─────────────┘             │
│  │  METRICS    │                                               │
│  │    ZONE     │                                               │
│  │             │                                               │
│  │ Scoring     │                                               │
│  │ Evaluation  │                                               │
│  │ Analytics   │                                               │
│  └─────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      IN GAME                                    │
│                                                                 │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐     │
│  │    RED      │      │    GREY     │      │    BLUE     │     │
│  │    ZONE     │◄────►│    ZONE     │◄────►│    ZONE     │     │
│  │             │      │             │      │             │     │
│  │ Attack Infra│      │ Simulated   │      │ Defender    │     │
│  │ C2 Servers  │      │ Internet    │      │ Enterprise  │     │
│  │ Tooling     │      │ DNS Roots   │      │ AD/LDAP     │     │
│  │ IP Diversity│      │ ISP Sim     │      │ Workstations│     │
│  └─────────────┘      │ Routing     │      │ Servers     │     │
│                       └─────────────┘      │ Security    │     │
│                                            └─────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### Zone Definitions

| Zone | Purpose | Trust Level | Key Components |
|------|---------|-------------|----------------|
| **Core Infrastructure** | Hypervisor/storage/network substrate | Privileged | ESXi/Proxmox, SAN/NAS, physical switches |
| **White (Exercise Admin)** | Timeline orchestration, event injection | Privileged | Automation APIs, scenario engine, inject controller |
| **Access** | Participant interface to range VMs | Semi-trusted | Web portal, Guacamole/SPICE, file transfer, chat |
| **Metrics/Evaluation** | Scoring, feedback, ROI measurement | Privileged | Scoring engine, analytics, dashboards |
| **Red (Adversary)** | Attack infrastructure | Adversarial | C2 frameworks, exploitation tools, IP rotation |
| **Grey (Simulated Internet)** | Public Internet simulation | Neutral | DNS roots/TLDs, ISP simulation, web content |
| **Blue (Defender)** | Scaled enterprise replica | Target | AD, workstations, servers, security stack |

### Modern Extension: Identity Zone

Add explicit Identity Zone for zero-trust environments:

| Component | Purpose |
|-----------|---------|
| Identity Provider (IdP) | SAML/OIDC simulation (Okta/Azure AD replica) |
| Certificate Authority | PKI hierarchy for TLS, code signing |
| Federation Services | Cross-domain trust simulation |
| MFA Infrastructure | TOTP/FIDO2 simulation |

## Implementation Sequence

Critical dependency ordering for range deployment:

```
Phase 1: Foundation
├── 1.1 Core Infrastructure Zone
│   ├── Hypervisor cluster deployment
│   ├── Storage provisioning
│   └── Physical network configuration
└── 1.2 Exercise Admin (White) Zone
    ├── Automation platform deployment
    └── IaC tooling setup

Phase 2: Identity & Network Core
├── 2.1 Blue Zone - Phase 1
│   ├── L3 routing (no ACLs yet)
│   ├── DNS infrastructure
│   └── Directory Services (AD/LDAP)
└── 2.2 Identity Zone (if applicable)
    ├── IdP deployment
    └── CA hierarchy

Phase 3: Internet Simulation
└── 3.1 Grey Zone
    ├── Root DNS servers
    ├── TLD authoritative servers
    ├── ISP routing simulation
    └── Web content farms

Phase 4: Enterprise Services
└── 4.1 Blue Zone - Phase 2
    ├── Connect to Grey Zone
    ├── Application servers (web, DB, file)
    ├── Security stack (SIEM, EDR, IDS)
    ├── End-user workstations (NPCs)
    └── Firewall lockdown (production ACLs)

Phase 5: Adversary Infrastructure
└── 5.1 Red Zone
    ├── C2 server deployment
    ├── Exploitation tooling
    └── IP diversity mechanisms

Phase 6: Participant Interface
├── 6.1 Access Zone
│   ├── Web portal deployment
│   ├── VM access (Guacamole/SPICE)
│   └── Communication channels
└── 6.2 Metrics Zone
    ├── Scoring engine
    └── Analytics dashboards
```

## Infrastructure Requirements

### Compute Sizing

| Scale | VMs | vCPU | RAM | Notes |
|-------|-----|------|-----|-------|
| Small (training) | 50-100 | 200-400 | 256-512 GB | Single team exercises |
| Medium (exercise) | 100-500 | 500-2000 | 1-4 TB | Multi-team force-on-force |
| Large (enterprise) | 500-2000 | 2000-8000 | 4-16 TB | Full enterprise simulation |
| Massive (national) | 2000+ | 8000+ | 16+ TB | Nation-state level exercises |

### Storage Architecture

| Tier | Technology | Purpose | IOPS Target |
|------|------------|---------|-------------|
| Hot | NVMe/SSD | Active VMs, snapshots | 100K+ |
| Warm | SSD/HDD Hybrid | Golden images, recent backups | 10K-50K |
| Cold | HDD/Object | Archives, long-term retention | 1K-5K |

**Critical**: Storage must support instant snapshot and rapid clone operations for range resets.

### Network Requirements

| Requirement | Specification |
|-------------|---------------|
| Core bandwidth | 10+ Gbps between hypervisors |
| VLAN capacity | 1000+ VLANs for team isolation |
| Isolation | Air-gap or strict firewall from production |
| Monitoring | SPAN/TAP ports for packet capture |

## Machine Image Strategy

### Image Count Minimization

Keep total unique images low to reduce maintenance burden:

| Category | Recommended Images | Notes |
|----------|-------------------|-------|
| Windows Server | 2-3 | 2019/2022, DC vs. member |
| Windows Workstation | 2 | Win10/11 variants |
| Linux Server | 3-4 | Ubuntu, CentOS/Rocky, Debian, specialty |
| Network Appliances | Per-vendor | Often require manual config |
| Security Tools | As needed | SIEM, EDR, IDS/IPS |

### Image Design Principles

1. **Generic base images** accepting IaC configuration
2. **Parameterized deployment** (hostname, IP, domain join via cloud-init/Sysprep)
3. **No sensitive data** in images (production clones require sanitization)
4. **Patch synchronization process** for ongoing maintenance

### Automation Trade-offs

| Component | Automation Feasibility | Notes |
|-----------|----------------------|-------|
| Windows/Linux VMs | High | Terraform, Ansible, cloud-init |
| AD/LDAP population | High | PowerShell, Python scripts |
| Network topology | Medium | Depends on hypervisor API |
| Vendor appliances | Low-Medium | Often require manual licensing |
| Security tool configs | Low-Medium | Vendor-specific APIs vary |

## Realism Drivers

### Traffic Generation (NPC Simulation)

Without background traffic, adversary activity is trivially detectable.

| Traffic Type | Implementation | Fidelity Impact |
|--------------|----------------|-----------------|
| Web browsing | Selenium/Playwright bots | Medium |
| Email | SMTP traffic generation | Medium |
| File access | SMB/NFS activity scripts | Medium |
| Application use | Protocol-specific generators | High |
| **LLM-driven NPCs** | Behavioral AI simulation | Ultra-high |

### Configuration Depth

| Layer | Low Fidelity | High Fidelity |
|-------|--------------|---------------|
| Firewall | Allow all | Production ACLs |
| AD | Default policies | GPOs matching production |
| SIEM | Basic collection | Full correlation rules |
| EDR | Passive mode | Active blocking |
| DNS | Basic resolution | Split-horizon, internal zones |

### Adversary Realism

| Level | Characteristics |
|-------|-----------------|
| Script kiddie | Public exploits, noisy, single-stage |
| Criminal | Commodity malware, basic evasion, financial motive |
| APT | Custom tooling, living-off-the-land, multi-stage |
| Nation-state | Zero-days, supply chain, long-term persistence |

## Cloud vs. On-Premise Decision Matrix

| Factor | On-Premise | Cloud |
|--------|------------|-------|
| **Initial cost** | High (hardware) | Low (pay-as-you-go) |
| **Operating cost** | Lower long-term | Higher (egress, sustained use) |
| **Setup time** | Weeks-months | Hours-days |
| **Image library** | Build yourself | Vendor-provided |
| **Isolation** | Physical air-gap possible | Logical isolation only |
| **Scalability** | Limited by hardware | Effectively unlimited |
| **Control** | Full | Constrained by provider |
| **Compliance** | Easier for classified | May require GovCloud |

### Cloud Cost Model

```
Monthly Cost = (Compute Hours × Rate) + (Storage GB × Rate) + (Egress GB × Rate)

Example (AWS, 100-VM range, 8 hours/day, 20 days/month):
- Compute: 100 VMs × 8h × 20d × $0.10/h = $1,600
- Storage: 5 TB × $0.10/GB = $500
- Egress: 500 GB × $0.09/GB = $45
- Total: ~$2,145/month
```

## Reset and Snapshot Strategy

### Reset Levels

| Level | Scope | Time | Use Case |
|-------|-------|------|----------|
| VM snapshot revert | Single VM | Seconds | Quick undo |
| Team enclave reset | All VMs in team | Minutes | Between exercise rounds |
| Full range reset | Entire range | 30-60 min | Exercise restart |
| Golden image redeploy | Full rebuild | Hours | Major changes |

### Implementation Approaches

1. **Snapshot trees**: Pre-exercise snapshots at known-good state
2. **Linked clones**: Storage-efficient copies from golden images
3. **IaC redeploy**: Terraform destroy/apply for full rebuild
4. **Differential restore**: Restore only modified VMs

## ICS/SCADA/OT Integration

### Integration Methods

| Method | Complexity | Fidelity |
|--------|------------|----------|
| Software simulation | Low | Low-Medium |
| Hardware-in-the-loop | Medium | High |
| Full physical testbed | High | Ultra |

### Connectivity Options

| Physical Device Type | Integration Method |
|---------------------|-------------------|
| TCP/IP managed | Direct VLAN connection |
| Serial-only | Serial-to-IP converter |
| Air-gapped | KVM-over-IP |
| Proprietary protocol | Protocol gateway |

## Exercise Execution Checklist

### Pre-Exercise (T-30 days to T-1 day)

- [ ] Range architecture validated
- [ ] All VMs deployed and accessible
- [ ] Network connectivity verified (all zones)
- [ ] NPC traffic generation active
- [ ] Security tools collecting telemetry
- [ ] Adversary infrastructure prepared
- [ ] Participant accounts provisioned
- [ ] Access portal tested
- [ ] Scoring system calibrated
- [ ] Snapshot baseline captured
- [ ] Communication channels established
- [ ] Rules of engagement documented

### Exercise Day (T-0)

- [ ] Range health check (all VMs responsive)
- [ ] NPC activity confirmed
- [ ] White team stations manned
- [ ] Timeline inject schedule loaded
- [ ] Scoring dashboard live
- [ ] Participant check-in complete
- [ ] Exercise start time synchronized

### Post-Exercise

- [ ] Final scores captured
- [ ] Telemetry exported for analysis
- [ ] Participant feedback collected
- [ ] Range reset (if re-use planned)
- [ ] Lessons learned documented
- [ ] Artifact preservation (if required)

## Skill Set Requirements

| Role | Zones | Key Skills |
|------|-------|------------|
| Enterprise Architect | All | System design, capacity planning |
| Virtualization Engineer | Core, Blue, Grey, Red | ESXi/Proxmox, storage, networking |
| Network Engineer | Core, Blue, Grey | Routing, switching, VLANs, firewalls |
| Windows Admin | Blue, Grey | AD, GPO, Windows Server |
| Linux Admin | Blue, Grey, Red | Multiple distros, scripting |
| Security SME | Blue | SIEM, EDR, IDS configuration |
| Offensive Operator | Red | C2, exploitation, tradecraft |
| Automation Engineer | White, Core | Terraform, Ansible, Python |
| Software Developer | White, Access | Portal development, API integration |
| NPC/Traffic SME | Blue, Grey | Traffic generation, behavioral modeling |

## Tools and References

### SEI/CERT Open Source Tools

- **Crucible**: Exercise management and scenario orchestration
- **GHOSTS**: NPC simulation framework for realistic user activity
- **TopoMojo**: Dynamic topology management

### Infrastructure as Code

| Tool | Purpose | Range Application |
|------|---------|-------------------|
| Terraform | Infrastructure provisioning | VM deployment, networking |
| Ansible | Configuration management | Post-deploy config, hardening |
| Packer | Image building | Golden image creation |
| cloud-init | First-boot configuration | Hostname, IP, domain join |

### Virtualization Platforms

| Platform | License | Best For |
|----------|---------|----------|
| VMware vSphere | Commercial | Enterprise ranges, full features |
| Proxmox VE | Open source | Cost-sensitive, Linux-centric |
| OpenStack | Open source | Large scale, cloud-like |
| AWS/Azure/GCP | Commercial | Rapid deployment, scalability |
| **Docker/Podman** | Open source | Lightweight ranges, rapid iteration, CI/CD integration |

### Docker-Based Ranges

Docker provides a lightweight alternative for specific range use cases:

**Advantages:**
- Sub-second container startup vs. minutes for VMs
- Minimal resource overhead (no hypervisor layer)
- Version-controlled infrastructure (Dockerfiles as IaC)
- Native CI/CD integration for automated testing
- Easy distribution via container registries

**Limitations:**
- Shared kernel limits OS diversity (Linux-only without nested VMs)
- No true Windows workstation simulation
- Network isolation less robust than VLANs
- Some security tools expect full OS environment

**Best Use Cases:**
- Grey zone services (DNS, web, mail)
- Red team infrastructure (C2, redirectors)
- NPC traffic generators
- Security tool evaluation
- Training environments for Linux-focused exercises
- Rapid prototyping before VM deployment

**Hybrid Approach:**
Combine Docker for lightweight services with VMs for full-fidelity endpoints:
```
Blue Zone: VMs (Windows AD, workstations, SIEM)
Grey Zone: Docker (DNS hierarchy, web farms, mail)
Red Zone: Docker (C2 servers, attack tools)
White Zone: Docker (automation, APIs)
```

## Resources

See `resources/` directory:
- `architecture/zone-templates.md` - Zone architecture templates and diagrams
- `infrastructure/sizing-calculator.md` - Compute/storage/network sizing guidance
- `implementation/iac-examples.md` - Terraform/Ansible examples for range deployment
- `implementation/docker-deployment.md` - **Docker-based range deployment with working examples**
- `traffic-generation/npc-strategies.md` - NPC simulation approaches and tooling
- `exercises/planning-templates.md` - Exercise planning and execution templates

See `templates/` directory:
- `range-design-document.md` - Comprehensive range design document template
- `exercise-plan.md` - Exercise planning template
- `roi-assessment.md` - Range ROI and effectiveness assessment template

See `scripts/` directory:
- `health-check.py` - Range health verification script
- `reset-orchestrator.py` - Automated range reset coordination
