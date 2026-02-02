#!/usr/bin/env python3
"""
Simulation Orchestrator

Generates complete cyber range simulation by combining multiple components.

Usage:
    python orchestrate.py --context org-context.yaml --output ./simulation/
    python orchestrate.py --context org-context.yaml --output ./simulation/ --components dns,web,ad
"""

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

COMPONENTS = {
    'dns': ('gen_dns_org.py', 'dns-org', 'DNS infrastructure'),
    'web': ('gen_web_org.py', 'web-org', 'Organization website'),
    'ad': ('gen_ad_population.py', 'ad-population', 'AD population scripts'),
}


def generate_component(name: str, context_path: Path, output_dir: Path, scripts_dir: Path) -> bool:
    script, subdir, desc = COMPONENTS[name]
    script_path = scripts_dir / script
    component_output = output_dir / subdir
    
    if not script_path.exists():
        print(f"  [SKIP] {name}: script not found")
        return False
    
    result = subprocess.run(
        [sys.executable, str(script_path), '--context', str(context_path), '--output', str(component_output)],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        print(f"  [OK] {name}: {desc}")
        return True
    else:
        print(f"  [FAIL] {name}: {result.stderr[:100]}")
        return False


def generate_master_compose(output_dir: Path, components: list, context: dict):
    org = context['organization']
    
    compose = f"""# Simulation: {org['name']}
# Generated: {datetime.now().isoformat()}

version: "3.9"

networks:
  range-backbone:
    driver: bridge
    ipam:
      config:
        - subnet: 172.16.0.0/16

"""
    
    includes = []
    if 'dns' in components:
        includes.append("  - dns-org/docker-compose.yml")
    if 'web' in components:
        includes.append("  - web-org/docker-compose.yml")
    
    if includes:
        compose += "include:\n" + "\n".join(includes) + "\n"
    
    (output_dir / 'docker-compose.yml').write_text(compose)


def generate_readme(output_dir: Path, context: dict, components: list):
    org = context['organization']
    
    readme = f"""# {org['name']} Simulation

## Organization Profile

| Property | Value |
|----------|-------|
| Name | {org['name']} |
| Domain | {org['domain']} |
| Industry | {org.get('industry', {}).get('sector', 'N/A')} |
| Employees | {org.get('size', {}).get('employees', 'N/A')} |

## Components

"""
    
    for c in components:
        _, subdir, desc = COMPONENTS[c]
        readme += f"- **{c}**: {desc} (`{subdir}/`)\n"
    
    readme += f"""
## Deployment

### Docker Components

```bash
docker network create range-backbone
docker compose up -d
docker compose ps
```

### AD Population

```powershell
# On domain controller
cd ad-population
.\\Populate-AD.ps1 -WhatIf  # Dry run
.\\Populate-AD.ps1          # Execute
```

## Network

- External: {org.get('network', {}).get('external_ip_range', 'N/A')}
- Internal: {org.get('network', {}).get('internal_ip_range', 'N/A')}
"""
    
    (output_dir / 'README.md').write_text(readme)


def main():
    parser = argparse.ArgumentParser(description="Generate complete simulation")
    parser.add_argument('--context', '-c', type=Path, required=True)
    parser.add_argument('--output', '-o', type=Path, default=Path('./simulation'))
    parser.add_argument('--components', type=str, default='dns,web,ad')
    parser.add_argument('--scripts-dir', type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    
    requested = [c.strip() for c in args.components.split(',')]
    valid = [c for c in requested if c in COMPONENTS]
    
    if not valid:
        print(f"No valid components. Available: {', '.join(COMPONENTS.keys())}")
        return 1
    
    with open(args.context, 'r') as f:
        context = yaml.safe_load(f)
    
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy(args.context, output / 'org-context.yaml')
    
    print(f"Generating: {context['organization']['name']}")
    print(f"Components: {', '.join(valid)}")
    print()
    
    generated = []
    for c in valid:
        if generate_component(c, args.context, output, args.scripts_dir):
            generated.append(c)
    
    docker_components = [c for c in generated if c in ['dns', 'web']]
    if docker_components:
        generate_master_compose(output, docker_components, context)
    
    generate_readme(output, context, generated)
    
    print()
    print(f"Generated {len(generated)}/{len(valid)} components")
    print(f"Output: {output}")
    print(f"See {output}/README.md for deployment")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
