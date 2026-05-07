---
name: cyber-range-design
description: >-
  Design, architect, and implement high-fidelity cyber ranges for training and
  exercises. Based on SEI/CERT methodology with modern extensions for cloud,
  zero-trust, and AI-driven simulation. Triggers on "cyber range", "exercise
  environment", "training range", "simulation environment", or requests for
  range zones, NPC traffic, ICS/SCADA/OT integration, range resets, or fidelity
  assessment. Modes: DESIGN (architecture), IMPLEMENT (build guidance), EXERCISE
  (execution planning).
author: dmaynor
version: 1.1.0
date: 2026-03-29
---

# Cyber Range Design and Implementation

Design, build, and operate high-fidelity virtualized cyber ranges that maximize training value through realistic adversary simulation and enterprise environment replication.

## Problem

Designing realistic cyber range exercises from scratch is a complex, multi-discipline challenge. Teams struggle with zone architecture, fidelity tradeoffs, NPC traffic generation, and infrastructure sizing -- leading to ranges that are either too simplistic to provide training value or too complex to maintain and reset reliably.

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

A cyber range is a fully interactive virtual instance of enterprise IT infrastructure dedicated to cyberwarfare training. Realism is the primary driver of training value -- ranges must support "train as you fight" principles.

| Fidelity Level | Characteristics | Training Value |
|----------------|-----------------|----------------|
| Low | Basic networking, minimal services, no traffic | Limited -- trivial to detect adversary |
| Medium | Core services, basic policies, scripted traffic | Moderate -- builds tool familiarity |
| High | Production-replica configs, realistic NPCs, proper noise | High -- develops operational intuition |
| Ultra | Threat intel-driven TTPs, adaptive adversary AI, full telemetry | Elite -- nation-state operator development |

## Zone Architecture Model

```
+---------------------------------------------------------------+
|                     OUT OF GAME                                |
|  +-------------+  +-------------+  +-------------+            |
|  |    CORE     |  |    WHITE    |  |   ACCESS    |            |
|  | INFRA ZONE  |  |    ZONE     |  |    ZONE     |            |
|  | Hypervisor  |  | (Exercise   |  | (Participant|            |
|  | Storage     |  |  Admin)     |  |  Interface) |            |
|  | Network     |  | Automation  |  | Web Portal  |            |
|  +-------------+  | Timeline    |  | VM Access   |            |
|                   +-------------+  +-------------+            |
|  +-------------+                                              |
|  |  METRICS    |                                              |
|  | Scoring     |                                              |
|  | Analytics   |                                              |
|  +-------------+                                              |
+---------------------------------------------------------------+

+---------------------------------------------------------------+
|                      IN GAME                                   |
|  +--------+       +---------+       +--------+                |
|  |  RED   |<----->|  GREY   |<----->|  BLUE  |                |
|  | Attack |       | Sim     |       | Defend |                |
|  | Infra  |       | Internet|       | Enter- |                |
|  | C2     |       | DNS/ISP |       | prise  |                |
|  +--------+       +---------+       +--------+                |
+---------------------------------------------------------------+
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

For zero-trust environments, add an explicit Identity Zone: IdP (SAML/OIDC), Certificate Authority (PKI), Federation Services, MFA Infrastructure (TOTP/FIDO2).

## Implementation Sequence

Critical dependency ordering for range deployment:

```
Phase 1: Foundation
  1.1 Core Infrastructure Zone (hypervisor, storage, network)
  1.2 Exercise Admin (White) Zone (automation, IaC)

Phase 2: Identity & Network Core
  2.1 Blue Zone Phase 1 (L3 routing, DNS, AD/LDAP)
  2.2 Identity Zone if applicable (IdP, CA)

Phase 3: Internet Simulation
  3.1 Grey Zone (root DNS, TLD servers, ISP routing, web content)

Phase 4: Enterprise Services
  4.1 Blue Zone Phase 2 (apps, security stack, workstations, firewall lockdown)

Phase 5: Adversary Infrastructure
  5.1 Red Zone (C2, exploitation tooling, IP diversity)

Phase 6: Participant Interface
  6.1 Access Zone (portal, VM access, comms)
  6.2 Metrics Zone (scoring, dashboards)
```

## Key Decision Points

### Cloud vs. On-Premise

| Factor | On-Premise | Cloud |
|--------|------------|-------|
| Initial cost | High (hardware) | Low (pay-as-you-go) |
| Setup time | Weeks-months | Hours-days |
| Isolation | Physical air-gap possible | Logical isolation only |
| Scalability | Limited by hardware | Effectively unlimited |
| Compliance | Easier for classified | May require GovCloud |

### NPC Traffic Generation

Without background traffic, adversary activity is trivially detectable.

| Traffic Type | Implementation | Fidelity Impact |
|--------------|----------------|-----------------|
| Web browsing | Selenium/Playwright bots | Medium |
| Email | SMTP traffic generation | Medium |
| File access | SMB/NFS activity scripts | Medium |
| Application use | Protocol-specific generators | High |
| **LLM-driven NPCs** | Behavioral AI simulation | Ultra-high |

### Reset Strategy

| Level | Scope | Time | Use Case |
|-------|-------|------|----------|
| VM snapshot revert | Single VM | Seconds | Quick undo |
| Team enclave reset | All VMs in team | Minutes | Between rounds |
| Full range reset | Entire range | 30-60 min | Exercise restart |
| Golden image redeploy | Full rebuild | Hours | Major changes |

## Verification

1. Range deploys successfully: all VMs in every zone (Core, White, Access, Metrics, Red, Grey, Blue) boot and pass health checks
2. Zone connectivity verified: inter-zone routing works per design (Red <-> Grey <-> Blue), and isolation holds (no unintended cross-zone leakage)
3. NPC traffic generation active: background traffic visible in SIEM/packet captures, adversary actions are not trivially distinguishable from noise
4. Exercise scenarios execute end-to-end: at least one inject fires, blue team receives telemetry, and scoring engine records results
5. Range reset completes within target time: full range revert to golden snapshot finishes within the documented SLA (e.g., 30-60 minutes for full reset)

## Notes

See `reference.md` for complete sizing tables, cost models, tool catalogs, ICS/SCADA integration details, image strategy, exercise checklists, skill set requirements, and platform configurations.

## Resources

See `resources/` directory:
- `architecture/zone-templates.md` - Zone architecture templates and diagrams
- `infrastructure/sizing-calculator.md` - Compute/storage/network sizing guidance
- `implementation/iac-examples.md` - Terraform/Ansible examples for range deployment
- `implementation/docker-deployment.md` - Docker-based range deployment with working examples
- `traffic-generation/npc-strategies.md` - NPC simulation approaches and tooling
- `exercises/planning-templates.md` - Exercise planning and execution templates

See `templates/` directory:
- `range-design-document.md` - Comprehensive range design document template
- `exercise-plan.md` - Exercise planning template
- `roi-assessment.md` - Range ROI and effectiveness assessment template

See `scripts/` directory:
- `health-check.py` - Range health verification script
- `reset-orchestrator.py` - Automated range reset coordination
