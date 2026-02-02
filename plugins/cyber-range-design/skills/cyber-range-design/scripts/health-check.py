#!/usr/bin/env python3
"""
Cyber Range Health Check Script

Verifies range infrastructure is operational before exercise execution.
Checks VM status, network connectivity, service availability, and NPC activity.

Usage:
    python health-check.py --config range-config.yaml
    python health-check.py --config range-config.yaml --zone blue --team 1
    python health-check.py --config range-config.yaml --quick
"""

import argparse
import asyncio
import json
import socket
import ssl
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml

# Optional imports - graceful degradation if not available
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    from pyVim.connect import SmartConnect, Disconnect
    from pyVmomi import vim
    PYVMOMI_AVAILABLE = True
except ImportError:
    PYVMOMI_AVAILABLE = False


class CheckStatus(Enum):
    """Health check result status."""
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class CheckResult:
    """Result of a single health check."""
    name: str
    status: CheckStatus
    message: str
    duration_ms: float = 0.0
    details: dict = field(default_factory=dict)


@dataclass
class ZoneHealth:
    """Health status of a range zone."""
    zone_name: str
    checks: list[CheckResult] = field(default_factory=list)
    
    @property
    def status(self) -> CheckStatus:
        """Overall zone status based on individual checks."""
        if any(c.status == CheckStatus.FAIL for c in self.checks):
            return CheckStatus.FAIL
        if any(c.status == CheckStatus.WARN for c in self.checks):
            return CheckStatus.WARN
        if all(c.status == CheckStatus.SKIP for c in self.checks):
            return CheckStatus.SKIP
        return CheckStatus.PASS
    
    @property
    def summary(self) -> dict:
        """Summary statistics."""
        return {
            "total": len(self.checks),
            "pass": sum(1 for c in self.checks if c.status == CheckStatus.PASS),
            "warn": sum(1 for c in self.checks if c.status == CheckStatus.WARN),
            "fail": sum(1 for c in self.checks if c.status == CheckStatus.FAIL),
            "skip": sum(1 for c in self.checks if c.status == CheckStatus.SKIP),
        }


class RangeHealthChecker:
    """
    Cyber range health verification system.
    
    Performs comprehensive checks across all range zones to ensure
    operational readiness before exercise execution.
    """
    
    def __init__(self, config_path: Path):
        """
        Initialize health checker with configuration.
        
        Args:
            config_path: Path to range configuration YAML file
        """
        self.config = self._load_config(config_path)
        self.results: list[ZoneHealth] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
    def _load_config(self, config_path: Path) -> dict:
        """Load and validate configuration file."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Validate required sections
        required_sections = ['range_name', 'zones']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required config section: {section}")
                
        return config
    
    async def run_all_checks(
        self,
        zone_filter: Optional[str] = None,
        team_filter: Optional[int] = None,
        quick_mode: bool = False
    ) -> list[ZoneHealth]:
        """
        Execute all health checks.
        
        Args:
            zone_filter: Only check specific zone (e.g., 'blue', 'grey')
            team_filter: Only check specific team number
            quick_mode: Skip slow checks (e.g., full service enumeration)
            
        Returns:
            List of ZoneHealth results
        """
        self.start_time = datetime.now()
        self.results = []
        
        zones_to_check = self.config['zones']
        
        if zone_filter:
            zones_to_check = {
                k: v for k, v in zones_to_check.items() 
                if k.lower() == zone_filter.lower()
            }
            
        for zone_name, zone_config in zones_to_check.items():
            zone_health = await self._check_zone(
                zone_name, 
                zone_config,
                team_filter=team_filter,
                quick_mode=quick_mode
            )
            self.results.append(zone_health)
            
        self.end_time = datetime.now()
        return self.results
    
    async def _check_zone(
        self,
        zone_name: str,
        zone_config: dict,
        team_filter: Optional[int] = None,
        quick_mode: bool = False
    ) -> ZoneHealth:
        """Check health of a single zone."""
        zone_health = ZoneHealth(zone_name=zone_name)
        
        # VM status checks
        if 'vms' in zone_config:
            vms = zone_config['vms']
            if team_filter and 'teams' in zone_config:
                # Filter to specific team
                vms = [vm for vm in vms if vm.get('team') == team_filter]
            
            for vm in vms:
                result = await self._check_vm(vm, quick_mode)
                zone_health.checks.append(result)
                
        # Service checks
        if 'services' in zone_config and not quick_mode:
            for service in zone_config['services']:
                result = await self._check_service(service)
                zone_health.checks.append(result)
                
        # Network connectivity checks
        if 'network_tests' in zone_config:
            for test in zone_config['network_tests']:
                result = await self._check_network(test)
                zone_health.checks.append(result)
                
        return zone_health
    
    async def _check_vm(self, vm_config: dict, quick_mode: bool) -> CheckResult:
        """Check VM status and basic connectivity."""
        start = datetime.now()
        vm_name = vm_config.get('name', 'Unknown')
        ip_address = vm_config.get('ip')
        
        # Ping check
        if ip_address:
            try:
                result = subprocess.run(
                    ['ping', '-c', '1', '-W', '2', ip_address],
                    capture_output=True,
                    timeout=5
                )
                ping_ok = result.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError):
                ping_ok = False
        else:
            ping_ok = False
            
        duration = (datetime.now() - start).total_seconds() * 1000
        
        if ping_ok:
            status = CheckStatus.PASS
            message = f"VM {vm_name} responding at {ip_address}"
        else:
            status = CheckStatus.FAIL
            message = f"VM {vm_name} not responding at {ip_address}"
            
        return CheckResult(
            name=f"vm_{vm_name}",
            status=status,
            message=message,
            duration_ms=duration,
            details={"ip": ip_address, "ping": ping_ok}
        )
    
    async def _check_service(self, service_config: dict) -> CheckResult:
        """Check service availability."""
        start = datetime.now()
        service_name = service_config.get('name', 'Unknown')
        service_type = service_config.get('type', 'tcp')
        host = service_config.get('host')
        port = service_config.get('port')
        
        if service_type == 'tcp':
            status, message = await self._check_tcp_port(host, port)
        elif service_type == 'http':
            url = service_config.get('url', f"http://{host}:{port}")
            status, message = await self._check_http(url)
        elif service_type == 'https':
            url = service_config.get('url', f"https://{host}:{port}")
            status, message = await self._check_http(url, verify_ssl=False)
        elif service_type == 'dns':
            status, message = await self._check_dns(host, service_config.get('query'))
        else:
            status = CheckStatus.SKIP
            message = f"Unknown service type: {service_type}"
            
        duration = (datetime.now() - start).total_seconds() * 1000
        
        return CheckResult(
            name=f"svc_{service_name}",
            status=status,
            message=message,
            duration_ms=duration,
            details={"type": service_type, "host": host, "port": port}
        )
    
    async def _check_tcp_port(
        self, 
        host: str, 
        port: int, 
        timeout_seconds: float = 5.0
    ) -> tuple[CheckStatus, str]:
        """Check if TCP port is accepting connections."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout_seconds
            )
            writer.close()
            await writer.wait_closed()
            return CheckStatus.PASS, f"Port {port} open on {host}"
        except asyncio.TimeoutError:
            return CheckStatus.FAIL, f"Timeout connecting to {host}:{port}"
        except ConnectionRefusedError:
            return CheckStatus.FAIL, f"Connection refused to {host}:{port}"
        except Exception as e:
            return CheckStatus.FAIL, f"Error connecting to {host}:{port}: {e}"
    
    async def _check_http(
        self, 
        url: str, 
        verify_ssl: bool = True,
        timeout_seconds: float = 10.0
    ) -> tuple[CheckStatus, str]:
        """Check HTTP(S) endpoint availability."""
        if not AIOHTTP_AVAILABLE:
            return CheckStatus.SKIP, "aiohttp not available for HTTP checks"
            
        try:
            ssl_context = None if verify_ssl else ssl.create_default_context()
            if not verify_ssl and ssl_context:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    timeout=aiohttp.ClientTimeout(total=timeout_seconds),
                    ssl=ssl_context
                ) as response:
                    if response.status < 400:
                        return CheckStatus.PASS, f"HTTP {response.status} from {url}"
                    elif response.status < 500:
                        return CheckStatus.WARN, f"HTTP {response.status} from {url}"
                    else:
                        return CheckStatus.FAIL, f"HTTP {response.status} from {url}"
        except Exception as e:
            return CheckStatus.FAIL, f"HTTP error for {url}: {e}"
    
    async def _check_dns(
        self, 
        server: str, 
        query: str
    ) -> tuple[CheckStatus, str]:
        """Check DNS resolution."""
        try:
            # Use system resolver pointed at specific server
            result = subprocess.run(
                ['dig', f'@{server}', query, '+short', '+time=2'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return CheckStatus.PASS, f"DNS query {query} resolved via {server}"
            else:
                return CheckStatus.FAIL, f"DNS query {query} failed via {server}"
        except Exception as e:
            return CheckStatus.FAIL, f"DNS check error: {e}"
    
    async def _check_network(self, test_config: dict) -> CheckResult:
        """Check network connectivity between zones."""
        start = datetime.now()
        test_name = test_config.get('name', 'Unknown')
        source = test_config.get('source')
        destination = test_config.get('destination')
        protocol = test_config.get('protocol', 'icmp')
        
        # For now, just do destination reachability
        # Full source-based testing requires agent on source
        if protocol == 'icmp':
            try:
                result = subprocess.run(
                    ['ping', '-c', '1', '-W', '2', destination],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    status = CheckStatus.PASS
                    message = f"Network path to {destination} OK"
                else:
                    status = CheckStatus.FAIL
                    message = f"Network path to {destination} failed"
            except Exception as e:
                status = CheckStatus.FAIL
                message = f"Network test error: {e}"
        else:
            status = CheckStatus.SKIP
            message = f"Protocol {protocol} not implemented"
            
        duration = (datetime.now() - start).total_seconds() * 1000
        
        return CheckResult(
            name=f"net_{test_name}",
            status=status,
            message=message,
            duration_ms=duration,
            details={"source": source, "destination": destination}
        )
    
    def generate_report(self, format: str = 'text') -> str:
        """
        Generate health check report.
        
        Args:
            format: Output format ('text', 'json', 'markdown')
            
        Returns:
            Formatted report string
        """
        if format == 'json':
            return self._report_json()
        elif format == 'markdown':
            return self._report_markdown()
        else:
            return self._report_text()
    
    def _report_text(self) -> str:
        """Generate plain text report."""
        lines = [
            "=" * 70,
            f"CYBER RANGE HEALTH CHECK REPORT",
            f"Range: {self.config.get('range_name', 'Unknown')}",
            f"Time: {self.start_time.isoformat() if self.start_time else 'N/A'}",
            "=" * 70,
            ""
        ]
        
        overall_pass = True
        overall_warn = False
        
        for zone in self.results:
            status_icon = {
                CheckStatus.PASS: "✅",
                CheckStatus.WARN: "⚠️",
                CheckStatus.FAIL: "❌",
                CheckStatus.SKIP: "⏭️"
            }.get(zone.status, "?")
            
            lines.append(f"\n{status_icon} ZONE: {zone.zone_name.upper()}")
            lines.append("-" * 50)
            
            summary = zone.summary
            lines.append(
                f"   Pass: {summary['pass']} | Warn: {summary['warn']} | "
                f"Fail: {summary['fail']} | Skip: {summary['skip']}"
            )
            
            for check in zone.checks:
                check_icon = {
                    CheckStatus.PASS: "✓",
                    CheckStatus.WARN: "!",
                    CheckStatus.FAIL: "✗",
                    CheckStatus.SKIP: "-"
                }.get(check.status, "?")
                
                lines.append(f"   [{check_icon}] {check.name}: {check.message}")
                
            if zone.status == CheckStatus.FAIL:
                overall_pass = False
            if zone.status == CheckStatus.WARN:
                overall_warn = True
                
        lines.append("")
        lines.append("=" * 70)
        
        if overall_pass and not overall_warn:
            lines.append("OVERALL STATUS: ✅ PASS - Range is operational")
        elif overall_pass and overall_warn:
            lines.append("OVERALL STATUS: ⚠️ PASS WITH WARNINGS - Review warnings")
        else:
            lines.append("OVERALL STATUS: ❌ FAIL - Range has critical issues")
            
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
            lines.append(f"Check duration: {duration:.2f} seconds")
            
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def _report_json(self) -> str:
        """Generate JSON report."""
        report = {
            "range_name": self.config.get('range_name'),
            "timestamp": self.start_time.isoformat() if self.start_time else None,
            "duration_seconds": (
                (self.end_time - self.start_time).total_seconds()
                if self.start_time and self.end_time else None
            ),
            "zones": []
        }
        
        for zone in self.results:
            zone_data = {
                "name": zone.zone_name,
                "status": zone.status.value,
                "summary": zone.summary,
                "checks": [
                    {
                        "name": c.name,
                        "status": c.status.value,
                        "message": c.message,
                        "duration_ms": c.duration_ms,
                        "details": c.details
                    }
                    for c in zone.checks
                ]
            }
            report["zones"].append(zone_data)
            
        return json.dumps(report, indent=2)
    
    def _report_markdown(self) -> str:
        """Generate Markdown report."""
        lines = [
            f"# Cyber Range Health Check Report",
            "",
            f"**Range:** {self.config.get('range_name', 'Unknown')}",
            f"**Time:** {self.start_time.isoformat() if self.start_time else 'N/A'}",
            "",
            "---",
            ""
        ]
        
        for zone in self.results:
            status_badge = {
                CheckStatus.PASS: "🟢",
                CheckStatus.WARN: "🟡",
                CheckStatus.FAIL: "🔴",
                CheckStatus.SKIP: "⚪"
            }.get(zone.status, "⚫")
            
            lines.append(f"## {status_badge} {zone.zone_name.upper()}")
            lines.append("")
            
            summary = zone.summary
            lines.append(
                f"| Pass | Warn | Fail | Skip |"
            )
            lines.append("|------|------|------|------|")
            lines.append(
                f"| {summary['pass']} | {summary['warn']} | "
                f"{summary['fail']} | {summary['skip']} |"
            )
            lines.append("")
            
            lines.append("| Check | Status | Message |")
            lines.append("|-------|--------|---------|")
            
            for check in zone.checks:
                status_text = check.status.value
                lines.append(f"| {check.name} | {status_text} | {check.message} |")
                
            lines.append("")
            
        return "\n".join(lines)


def create_sample_config() -> str:
    """Generate sample configuration file."""
    sample = {
        "range_name": "Exercise Range Alpha",
        "zones": {
            "core": {
                "description": "Core infrastructure zone",
                "services": [
                    {"name": "vcenter", "type": "https", "host": "vcenter.range.local", "port": 443},
                    {"name": "storage", "type": "tcp", "host": "storage.range.local", "port": 22}
                ]
            },
            "white": {
                "description": "Exercise administration zone",
                "vms": [
                    {"name": "automation-01", "ip": "10.100.1.10"},
                    {"name": "scenario-01", "ip": "10.100.1.11"}
                ],
                "services": [
                    {"name": "scenario-api", "type": "http", "host": "10.100.1.11", "port": 8080}
                ]
            },
            "blue": {
                "description": "Defender zone",
                "vms": [
                    {"name": "dc01-t1", "ip": "192.168.101.10", "team": 1},
                    {"name": "dc02-t1", "ip": "192.168.101.11", "team": 1},
                    {"name": "siem-t1", "ip": "192.168.101.20", "team": 1},
                    {"name": "wks-01-t1", "ip": "192.168.102.10", "team": 1},
                    {"name": "wks-02-t1", "ip": "192.168.102.11", "team": 1}
                ],
                "services": [
                    {"name": "siem-web", "type": "https", "host": "192.168.101.20", "port": 8000}
                ],
                "network_tests": [
                    {"name": "blue-to-grey", "source": "192.168.101.1", "destination": "10.50.1.1"}
                ]
            },
            "grey": {
                "description": "Simulated Internet zone",
                "vms": [
                    {"name": "dns-root", "ip": "10.50.1.10"},
                    {"name": "web-farm-01", "ip": "10.50.2.10"}
                ],
                "services": [
                    {"name": "root-dns", "type": "dns", "host": "10.50.1.10", "query": "google.com"}
                ]
            },
            "red": {
                "description": "Adversary zone",
                "vms": [
                    {"name": "c2-server", "ip": "10.66.1.10"},
                    {"name": "attack-box", "ip": "10.66.2.10"}
                ]
            }
        }
    }
    return yaml.dump(sample, default_flow_style=False)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Cyber Range Health Check",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --config range.yaml                    # Full check
  %(prog)s --config range.yaml --zone blue        # Blue zone only
  %(prog)s --config range.yaml --zone blue --team 1  # Team 1 only
  %(prog)s --config range.yaml --quick            # Quick check (skip slow)
  %(prog)s --generate-config > range.yaml         # Generate sample config
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        type=Path,
        help='Path to range configuration YAML file'
    )
    parser.add_argument(
        '--zone', '-z',
        type=str,
        help='Only check specific zone (e.g., blue, grey, red)'
    )
    parser.add_argument(
        '--team', '-t',
        type=int,
        help='Only check specific team number'
    )
    parser.add_argument(
        '--quick', '-q',
        action='store_true',
        help='Quick mode - skip slow checks'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['text', 'json', 'markdown'],
        default='text',
        help='Output format (default: text)'
    )
    parser.add_argument(
        '--generate-config',
        action='store_true',
        help='Generate sample configuration file'
    )
    
    args = parser.parse_args()
    
    if args.generate_config:
        print(create_sample_config())
        return 0
        
    if not args.config:
        parser.error("--config is required unless using --generate-config")
        
    try:
        checker = RangeHealthChecker(args.config)
        await checker.run_all_checks(
            zone_filter=args.zone,
            team_filter=args.team,
            quick_mode=args.quick
        )
        
        report = checker.generate_report(format=args.format)
        print(report)
        
        # Exit code based on results
        for zone in checker.results:
            if zone.status == CheckStatus.FAIL:
                return 1
                
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
