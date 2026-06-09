# dmaynor Skills Marketplace

Private plugin marketplace for Claude Code.

## Plugins

### Apple / macOS vulnerability research

| Plugin | Description |
|--------|-------------|
| `apple-silicon-attack-surface-enumeration` | Systematic attack surface enumeration for Apple Silicon (A/M-series) |
| `apple-vuln-research-apple-silicon-kernel-layout` | Find the correct arm64e kernel and per-SoC kernelcache for a target |
| `apple-vuln-research-cve-to-binary-regression` | Validate that a seed CVE maps to a specific macOS/iOS binary |
| `apple-vuln-research-daemon-enum-recovery` | Recover message/frame/command enums and dispatch tables from stripped daemons |
| `apple-vuln-research-kernelcache-kext-binary-diff` | Diff a single kext between macOS versions inside the kernelcache |
| `apple-vuln-research-nsxpc-listener-enum` | Enumerate the server-side NSXPC attack surface of an Apple daemon |
| `apple-vuln-research-security-report-submission` | Submit vulnerability reports to Apple Security Research |
| `apple-vuln-research-txm-sptm-firmware-extraction` | Extract and analyze TXM/SPTM firmware from IM4P containers |
| `macos-dyld-shared-cache-analysis` | Analyze framework binaries in the dyld shared cache via `dyld_info` |
| `macos-preference-injection-hunting` | Find NSUserDefaults preference-injection bugs in macOS daemons |
| `macos-screen-flash-triage` | Triage "screen flashed like a screenshot" reports via unified logs |

### Wireless / hardware

| Plugin | Description |
|--------|-------------|
| `wireless-driver-control-frame-audit` | Audit wireless driver control-frame / IE parsing across kernel drivers |
| `wireless-multiplex-state-audit` | Audit protocol-multiplex state machines in wireless drivers |
| `hardware-re-usb-hid` | Reverse engineer USB HID peripherals via Linux hidraw |

### Cyber range & red/purple team

| Plugin | Description |
|--------|-------------|
| `cyber-range-design` | Design and implement high-fidelity cyber ranges |
| `simulation-components` | Modular virtualized services for cyber range sims |
| `purple-teaming` | Purple team exercises and detection validation |

### Analysis & advisory

| Plugin | Description |
|--------|-------------|
| `sat-analysis` | Structured Analytic Techniques for rigorous analysis |
| `zero-analysis` | Critical analysis persona for security research |
| `strategic-advisor` | Brutally honest strategic evaluation |
| `rca-investigation` | Root cause analysis via layered taxonomy and causal chains |
| `design-philosophy` | Rigorous design philosophy for simplicity, UX, and quality |
| `pdf-report-formatting` | Branded, themed PDF reports (light/cyber) for analysis deliverables |

### Agents & tooling

| Plugin | Description |
|--------|-------------|
| `swarm-orchestration` | Multi-agent swarm orchestration with TD coordination |
| `autonomous-research-loop` | Run Claude Code as an autonomous research agent with restart-with-state loops |
| `autonomous-loop-safety-constraints` | Harden autonomous research loop safety blocks against rationalization |
| `claudeception` | Continuous-learning meta-skill that creates new skills from a session |
| `claude-code-hook-debugging` | Debug Claude Code hook errors (SessionStart, PreToolUse, etc.) |

### Development & recovery

| Plugin | Description |
|--------|-------------|
| `godot` | Godot Engine 4.x game development |
| `zig` | Zig systems programming language |
| `gits-dual-plane-isometric-assets` | Isometric sprite sheets for dual-plane city simulation |
| `windows-boot-recovery` | Diagnose and recover non-booting Windows from a Linux environment |

## Installation

```bash
# Add this marketplace
/plugin marketplace add dmaynor/dmaynor-skills-marketplace

# Install a plugin
/plugin install cyber-range-design@dmaynor-skills-marketplace
```
