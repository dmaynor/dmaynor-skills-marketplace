#!/usr/bin/env python3
"""
Cyber Range Reset Orchestrator

Coordinates range reset operations across multiple zones and teams.
Supports snapshot revert, VM power cycling, and service restart.

Usage:
    python reset-orchestrator.py --config range-config.yaml --level team --team 1
    python reset-orchestrator.py --config range-config.yaml --level full
    python reset-orchestrator.py --config range-config.yaml --snapshot pre-exercise
"""

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ResetLevel(Enum):
    """Scope of reset operation."""
    VM = "vm"           # Single VM
    TEAM = "team"       # All VMs in a team enclave
    ZONE = "zone"       # All VMs in a zone
    FULL = "full"       # Entire range


class ResetAction(Enum):
    """Type of reset action."""
    SNAPSHOT_REVERT = "snapshot_revert"
    POWER_CYCLE = "power_cycle"
    CHECKPOINT_RESTORE = "checkpoint_restore"
    REBUILD = "rebuild"


@dataclass
class ResetTask:
    """Individual reset task."""
    vm_name: str
    action: ResetAction
    snapshot_name: Optional[str] = None
    status: str = "pending"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None
    
    @property
    def duration_seconds(self) -> Optional[float]:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


@dataclass
class ResetOperation:
    """Complete reset operation with multiple tasks."""
    operation_id: str
    level: ResetLevel
    action: ResetAction
    tasks: list[ResetTask] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def status(self) -> str:
        if not self.tasks:
            return "empty"
        if any(t.status == "failed" for t in self.tasks):
            return "failed"
        if all(t.status == "completed" for t in self.tasks):
            return "completed"
        if any(t.status == "running" for t in self.tasks):
            return "running"
        return "pending"
    
    @property
    def progress(self) -> float:
        if not self.tasks:
            return 0.0
        completed = sum(1 for t in self.tasks if t.status == "completed")
        return completed / len(self.tasks) * 100


class VMwareAdapter:
    """
    Adapter for VMware vSphere operations.
    
    Requires pyVmomi library and vCenter credentials.
    """
    
    def __init__(self, config: dict):
        """
        Initialize VMware adapter.
        
        Args:
            config: VMware connection configuration
        """
        self.host = config.get('host')
        self.user = config.get('user')
        self.password = config.get('password')
        self.port = config.get('port', 443)
        self.si = None
        
    async def connect(self):
        """Establish vCenter connection."""
        try:
            from pyVim.connect import SmartConnect
            import ssl
            
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            self.si = SmartConnect(
                host=self.host,
                user=self.user,
                pwd=self.password,
                port=self.port,
                sslContext=context
            )
            logger.info(f"Connected to vCenter: {self.host}")
        except ImportError:
            raise RuntimeError("pyVmomi not installed - cannot use VMware adapter")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to vCenter: {e}")
    
    async def disconnect(self):
        """Close vCenter connection."""
        if self.si:
            from pyVim.connect import Disconnect
            Disconnect(self.si)
            logger.info("Disconnected from vCenter")
    
    async def revert_snapshot(self, vm_name: str, snapshot_name: str) -> bool:
        """
        Revert VM to named snapshot.
        
        Args:
            vm_name: Name of the VM
            snapshot_name: Name of the snapshot to revert to
            
        Returns:
            True if successful
        """
        from pyVmomi import vim
        
        vm = self._find_vm(vm_name)
        if not vm:
            raise ValueError(f"VM not found: {vm_name}")
            
        snapshot = self._find_snapshot(vm, snapshot_name)
        if not snapshot:
            raise ValueError(f"Snapshot not found: {snapshot_name} on {vm_name}")
            
        task = snapshot.RevertToSnapshot_Task()
        self._wait_for_task(task)
        
        logger.info(f"Reverted {vm_name} to snapshot {snapshot_name}")
        return True
    
    async def power_cycle(self, vm_name: str) -> bool:
        """
        Power cycle a VM (reset).
        
        Args:
            vm_name: Name of the VM
            
        Returns:
            True if successful
        """
        from pyVmomi import vim
        
        vm = self._find_vm(vm_name)
        if not vm:
            raise ValueError(f"VM not found: {vm_name}")
            
        if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
            task = vm.ResetVM_Task()
            self._wait_for_task(task)
        else:
            task = vm.PowerOnVM_Task()
            self._wait_for_task(task)
            
        logger.info(f"Power cycled {vm_name}")
        return True
    
    def _find_vm(self, vm_name: str):
        """Find VM by name."""
        from pyVmomi import vim
        
        content = self.si.RetrieveContent()
        container = content.rootFolder
        view_type = [vim.VirtualMachine]
        recursive = True
        
        container_view = content.viewManager.CreateContainerView(
            container, view_type, recursive
        )
        
        for vm in container_view.view:
            if vm.name == vm_name:
                return vm
        return None
    
    def _find_snapshot(self, vm, snapshot_name: str):
        """Find snapshot by name on VM."""
        if not vm.snapshot:
            return None
            
        def find_in_tree(snapshots, name):
            for snapshot in snapshots:
                if snapshot.name == name:
                    return snapshot.snapshot
                if snapshot.childSnapshotList:
                    result = find_in_tree(snapshot.childSnapshotList, name)
                    if result:
                        return result
            return None
            
        return find_in_tree(vm.snapshot.rootSnapshotList, snapshot_name)
    
    def _wait_for_task(self, task):
        """Wait for vSphere task to complete."""
        from pyVmomi import vim
        
        while task.info.state not in [
            vim.TaskInfo.State.success,
            vim.TaskInfo.State.error
        ]:
            asyncio.sleep(1)
            
        if task.info.state == vim.TaskInfo.State.error:
            raise RuntimeError(f"Task failed: {task.info.error}")


class ProxmoxAdapter:
    """
    Adapter for Proxmox VE operations.
    
    Uses Proxmox API for VM management.
    """
    
    def __init__(self, config: dict):
        """
        Initialize Proxmox adapter.
        
        Args:
            config: Proxmox connection configuration
        """
        self.host = config.get('host')
        self.user = config.get('user')
        self.password = config.get('password')
        self.token_name = config.get('token_name')
        self.token_value = config.get('token_value')
        self.verify_ssl = config.get('verify_ssl', False)
        
    async def connect(self):
        """Establish Proxmox API connection."""
        try:
            from proxmoxer import ProxmoxAPI
            
            if self.token_name and self.token_value:
                self.api = ProxmoxAPI(
                    self.host,
                    user=self.user,
                    token_name=self.token_name,
                    token_value=self.token_value,
                    verify_ssl=self.verify_ssl
                )
            else:
                self.api = ProxmoxAPI(
                    self.host,
                    user=self.user,
                    password=self.password,
                    verify_ssl=self.verify_ssl
                )
            logger.info(f"Connected to Proxmox: {self.host}")
        except ImportError:
            raise RuntimeError("proxmoxer not installed - cannot use Proxmox adapter")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Proxmox: {e}")
    
    async def disconnect(self):
        """Close Proxmox connection."""
        logger.info("Disconnected from Proxmox")
    
    async def revert_snapshot(
        self, 
        vm_name: str, 
        snapshot_name: str,
        node: str = None
    ) -> bool:
        """
        Rollback VM to snapshot.
        
        Args:
            vm_name: Name or VMID of the VM
            snapshot_name: Name of the snapshot
            node: Proxmox node (if not specified, will search)
            
        Returns:
            True if successful
        """
        vmid, node = self._find_vm(vm_name, node)
        if not vmid:
            raise ValueError(f"VM not found: {vm_name}")
            
        self.api.nodes(node).qemu(vmid).snapshot(snapshot_name).rollback.post()
        logger.info(f"Reverted {vm_name} to snapshot {snapshot_name}")
        return True
    
    async def power_cycle(self, vm_name: str, node: str = None) -> bool:
        """
        Reset VM.
        
        Args:
            vm_name: Name or VMID of the VM
            node: Proxmox node
            
        Returns:
            True if successful
        """
        vmid, node = self._find_vm(vm_name, node)
        if not vmid:
            raise ValueError(f"VM not found: {vm_name}")
            
        self.api.nodes(node).qemu(vmid).status.reset.post()
        logger.info(f"Power cycled {vm_name}")
        return True
    
    def _find_vm(self, vm_name: str, node: str = None):
        """Find VM by name or VMID."""
        for pve_node in self.api.nodes.get():
            if node and pve_node['node'] != node:
                continue
            for vm in self.api.nodes(pve_node['node']).qemu.get():
                if str(vm['vmid']) == str(vm_name) or vm.get('name') == vm_name:
                    return vm['vmid'], pve_node['node']
        return None, None


class DryRunAdapter:
    """
    Dry-run adapter that simulates operations without executing.
    
    Useful for testing and validation.
    """
    
    def __init__(self, config: dict):
        self.delay_seconds = config.get('delay_seconds', 0.5)
        
    async def connect(self):
        logger.info("[DRY RUN] Simulating connection")
        
    async def disconnect(self):
        logger.info("[DRY RUN] Simulating disconnection")
        
    async def revert_snapshot(self, vm_name: str, snapshot_name: str) -> bool:
        await asyncio.sleep(self.delay_seconds)
        logger.info(f"[DRY RUN] Would revert {vm_name} to snapshot {snapshot_name}")
        return True
        
    async def power_cycle(self, vm_name: str) -> bool:
        await asyncio.sleep(self.delay_seconds)
        logger.info(f"[DRY RUN] Would power cycle {vm_name}")
        return True


class ResetOrchestrator:
    """
    Orchestrates range reset operations.
    
    Coordinates parallel reset tasks across multiple VMs
    while respecting dependencies and resource limits.
    """
    
    def __init__(self, config_path: Path):
        """
        Initialize orchestrator with configuration.
        
        Args:
            config_path: Path to range configuration YAML file
        """
        self.config = self._load_config(config_path)
        self.adapter = None
        self.operation: Optional[ResetOperation] = None
        
    def _load_config(self, config_path: Path) -> dict:
        """Load configuration file."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    async def initialize_adapter(self, dry_run: bool = False):
        """
        Initialize hypervisor adapter based on configuration.
        
        Args:
            dry_run: If True, use dry-run adapter
        """
        if dry_run:
            self.adapter = DryRunAdapter({})
        else:
            platform = self.config.get('platform', {})
            platform_type = platform.get('type', 'vmware')
            
            if platform_type == 'vmware':
                self.adapter = VMwareAdapter(platform)
            elif platform_type == 'proxmox':
                self.adapter = ProxmoxAdapter(platform)
            else:
                raise ValueError(f"Unsupported platform: {platform_type}")
                
        await self.adapter.connect()
    
    async def close(self):
        """Clean up resources."""
        if self.adapter:
            await self.adapter.disconnect()
    
    def plan_reset(
        self,
        level: ResetLevel,
        action: ResetAction,
        snapshot_name: Optional[str] = None,
        zone: Optional[str] = None,
        team: Optional[int] = None,
        vm_name: Optional[str] = None
    ) -> ResetOperation:
        """
        Plan reset operation.
        
        Args:
            level: Scope of reset
            action: Type of reset action
            snapshot_name: Snapshot name for revert operations
            zone: Zone filter (for ZONE level)
            team: Team filter (for TEAM level)
            vm_name: VM name (for VM level)
            
        Returns:
            Planned ResetOperation
        """
        operation_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.operation = ResetOperation(
            operation_id=operation_id,
            level=level,
            action=action
        )
        
        # Collect VMs based on level
        vms_to_reset = []
        
        for zone_name, zone_config in self.config.get('zones', {}).items():
            if level == ResetLevel.ZONE and zone and zone_name != zone:
                continue
                
            for vm in zone_config.get('vms', []):
                if level == ResetLevel.VM and vm.get('name') != vm_name:
                    continue
                if level == ResetLevel.TEAM and team and vm.get('team') != team:
                    continue
                    
                vms_to_reset.append({
                    'name': vm.get('name'),
                    'zone': zone_name,
                    'team': vm.get('team')
                })
        
        # Create tasks
        for vm in vms_to_reset:
            task = ResetTask(
                vm_name=vm['name'],
                action=action,
                snapshot_name=snapshot_name
            )
            self.operation.tasks.append(task)
            
        logger.info(
            f"Planned {len(self.operation.tasks)} reset tasks "
            f"(level={level.value}, action={action.value})"
        )
        
        return self.operation
    
    async def execute(
        self,
        parallel: int = 5,
        progress_callback: Optional[Callable[[ResetOperation], None]] = None
    ) -> ResetOperation:
        """
        Execute planned reset operation.
        
        Args:
            parallel: Maximum concurrent operations
            progress_callback: Called after each task completion
            
        Returns:
            Completed ResetOperation
        """
        if not self.operation:
            raise RuntimeError("No operation planned - call plan_reset first")
            
        self.operation.start_time = datetime.now()
        
        semaphore = asyncio.Semaphore(parallel)
        
        async def execute_task(task: ResetTask):
            async with semaphore:
                task.status = "running"
                task.start_time = datetime.now()
                
                try:
                    if task.action == ResetAction.SNAPSHOT_REVERT:
                        await self.adapter.revert_snapshot(
                            task.vm_name,
                            task.snapshot_name
                        )
                    elif task.action == ResetAction.POWER_CYCLE:
                        await self.adapter.power_cycle(task.vm_name)
                    else:
                        raise ValueError(f"Unsupported action: {task.action}")
                        
                    task.status = "completed"
                    
                except Exception as e:
                    task.status = "failed"
                    task.error = str(e)
                    logger.error(f"Task failed for {task.vm_name}: {e}")
                    
                finally:
                    task.end_time = datetime.now()
                    
                if progress_callback:
                    progress_callback(self.operation)
        
        # Execute all tasks
        await asyncio.gather(*[execute_task(t) for t in self.operation.tasks])
        
        self.operation.end_time = datetime.now()
        
        return self.operation
    
    def generate_report(self, format: str = 'text') -> str:
        """Generate execution report."""
        if not self.operation:
            return "No operation to report"
            
        if format == 'json':
            return self._report_json()
        else:
            return self._report_text()
    
    def _report_text(self) -> str:
        """Generate plain text report."""
        op = self.operation
        
        lines = [
            "=" * 60,
            "RANGE RESET OPERATION REPORT",
            "=" * 60,
            f"Operation ID: {op.operation_id}",
            f"Level: {op.level.value}",
            f"Action: {op.action.value}",
            f"Status: {op.status.upper()}",
            f"Progress: {op.progress:.1f}%",
            "",
            f"Started: {op.start_time.isoformat() if op.start_time else 'N/A'}",
            f"Ended: {op.end_time.isoformat() if op.end_time else 'N/A'}",
            "",
            "-" * 60,
            "TASKS:",
            "-" * 60,
        ]
        
        for task in op.tasks:
            status_icon = {
                "completed": "✅",
                "failed": "❌",
                "running": "🔄",
                "pending": "⏳"
            }.get(task.status, "?")
            
            duration = f"{task.duration_seconds:.1f}s" if task.duration_seconds else "N/A"
            
            lines.append(f"  {status_icon} {task.vm_name} - {task.status} ({duration})")
            if task.error:
                lines.append(f"      Error: {task.error}")
                
        lines.append("")
        lines.append("=" * 60)
        
        # Summary
        completed = sum(1 for t in op.tasks if t.status == "completed")
        failed = sum(1 for t in op.tasks if t.status == "failed")
        
        lines.append(f"SUMMARY: {completed} completed, {failed} failed, {len(op.tasks)} total")
        
        if op.start_time and op.end_time:
            duration = (op.end_time - op.start_time).total_seconds()
            lines.append(f"Total duration: {duration:.1f} seconds")
            
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _report_json(self) -> str:
        """Generate JSON report."""
        op = self.operation
        
        report = {
            "operation_id": op.operation_id,
            "level": op.level.value,
            "action": op.action.value,
            "status": op.status,
            "progress": op.progress,
            "start_time": op.start_time.isoformat() if op.start_time else None,
            "end_time": op.end_time.isoformat() if op.end_time else None,
            "tasks": [
                {
                    "vm_name": t.vm_name,
                    "action": t.action.value,
                    "snapshot_name": t.snapshot_name,
                    "status": t.status,
                    "duration_seconds": t.duration_seconds,
                    "error": t.error
                }
                for t in op.tasks
            ]
        }
        
        return json.dumps(report, indent=2)


def progress_printer(operation: ResetOperation):
    """Print progress updates."""
    completed = sum(1 for t in operation.tasks if t.status == "completed")
    total = len(operation.tasks)
    print(f"\rProgress: {completed}/{total} ({operation.progress:.1f}%)", end="", flush=True)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Cyber Range Reset Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --config range.yaml --level full --snapshot pre-exercise
  %(prog)s --config range.yaml --level team --team 1 --action power_cycle
  %(prog)s --config range.yaml --level zone --zone blue --snapshot baseline
  %(prog)s --config range.yaml --level vm --vm dc01-t1 --action snapshot_revert
  %(prog)s --config range.yaml --level full --dry-run
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        type=Path,
        required=True,
        help='Path to range configuration YAML file'
    )
    parser.add_argument(
        '--level', '-l',
        type=str,
        choices=['vm', 'team', 'zone', 'full'],
        required=True,
        help='Reset scope level'
    )
    parser.add_argument(
        '--action', '-a',
        type=str,
        choices=['snapshot_revert', 'power_cycle'],
        default='snapshot_revert',
        help='Reset action type (default: snapshot_revert)'
    )
    parser.add_argument(
        '--snapshot', '-s',
        type=str,
        help='Snapshot name for revert operations'
    )
    parser.add_argument(
        '--zone', '-z',
        type=str,
        help='Zone name (for zone-level reset)'
    )
    parser.add_argument(
        '--team', '-t',
        type=int,
        help='Team number (for team-level reset)'
    )
    parser.add_argument(
        '--vm',
        type=str,
        help='VM name (for vm-level reset)'
    )
    parser.add_argument(
        '--parallel', '-p',
        type=int,
        default=5,
        help='Maximum parallel operations (default: 5)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate operations without executing'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )
    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Skip confirmation prompt'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    level = ResetLevel(args.level)
    action = ResetAction(args.action)
    
    if action == ResetAction.SNAPSHOT_REVERT and not args.snapshot:
        parser.error("--snapshot is required for snapshot_revert action")
        
    if level == ResetLevel.TEAM and args.team is None:
        parser.error("--team is required for team-level reset")
        
    if level == ResetLevel.ZONE and not args.zone:
        parser.error("--zone is required for zone-level reset")
        
    if level == ResetLevel.VM and not args.vm:
        parser.error("--vm is required for vm-level reset")
    
    try:
        orchestrator = ResetOrchestrator(args.config)
        
        # Plan operation
        operation = orchestrator.plan_reset(
            level=level,
            action=action,
            snapshot_name=args.snapshot,
            zone=args.zone,
            team=args.team,
            vm_name=args.vm
        )
        
        if not operation.tasks:
            print("No VMs matched the specified criteria")
            return 1
            
        # Confirmation
        if not args.yes and not args.dry_run:
            print(f"\nPlanned operation:")
            print(f"  Level: {level.value}")
            print(f"  Action: {action.value}")
            print(f"  VMs to reset: {len(operation.tasks)}")
            print(f"  VMs: {', '.join(t.vm_name for t in operation.tasks[:5])}", end="")
            if len(operation.tasks) > 5:
                print(f" ... and {len(operation.tasks) - 5} more")
            else:
                print()
            
            confirm = input("\nProceed? [y/N] ")
            if confirm.lower() != 'y':
                print("Aborted")
                return 0
        
        # Initialize adapter
        await orchestrator.initialize_adapter(dry_run=args.dry_run)
        
        # Execute
        print("\nExecuting reset operation...")
        await orchestrator.execute(
            parallel=args.parallel,
            progress_callback=progress_printer
        )
        print()  # New line after progress
        
        # Report
        report = orchestrator.generate_report(format=args.format)
        print(report)
        
        # Cleanup
        await orchestrator.close()
        
        # Exit code
        return 0 if operation.status == "completed" else 1
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
