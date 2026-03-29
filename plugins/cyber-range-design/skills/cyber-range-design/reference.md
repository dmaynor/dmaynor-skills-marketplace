---
parent: SKILL.md
---

# Cyber Range Design Reference

Detailed sizing tables, cost models, tool catalogs, and implementation specifics. See SKILL.md for core methodology and zone architecture.

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

## Cloud Cost Model

```
Monthly Cost = (Compute Hours x Rate) + (Storage GB x Rate) + (Egress GB x Rate)

Example (AWS, 100-VM range, 8 hours/day, 20 days/month):
- Compute: 100 VMs x 8h x 20d x $0.10/h = $1,600
- Storage: 5 TB x $0.10/GB = $500
- Egress: 500 GB x $0.09/GB = $45
- Total: ~$2,145/month
```

## Reset and Snapshot Strategy

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
