# Infrastructure Sizing Calculator

Guidance for sizing cyber range compute, storage, and network resources.

## Compute Sizing

### VM Resource Profiles

| Profile | vCPU | RAM (GB) | Disk (GB) | Use Case |
|---------|------|----------|-----------|----------|
| Micro | 1 | 1 | 20 | DNS, lightweight services |
| Small | 2 | 4 | 40 | Workstations, basic services |
| Medium | 4 | 8 | 80 | Application servers, DC |
| Large | 8 | 16 | 160 | SIEM, heavy workloads |
| XLarge | 16 | 32 | 320 | Splunk indexers, large DBs |
| GPU | 8+ | 32+ | 500+ | ML/AI workloads, rendering |

### Reference Configurations by Scale

#### Small Training Range (10-50 participants)

```yaml
range_profile: training_small
total_vms: 50-100

vm_distribution:
  blue_zone:
    domain_controllers: 2      # Medium profile
    file_servers: 1            # Medium profile
    application_servers: 3     # Medium profile
    siem: 1                    # Large profile
    edr_console: 1             # Medium profile
    workstations: 20           # Small profile
    
  grey_zone:
    dns_servers: 3             # Micro profile
    web_servers: 5             # Small profile
    routers: 2                 # Micro profile
    
  red_zone:
    c2_servers: 2              # Medium profile
    attack_boxes: 5            # Medium profile
    
  white_zone:
    automation_server: 1       # Medium profile
    portal_server: 1           # Medium profile
    
  access_zone:
    guacamole: 1               # Medium profile
    
compute_totals:
  vcpu: 200-300
  ram_gb: 400-600
  
host_requirements:
  # Assuming 3:1 consolidation ratio
  hosts: 2-3
  per_host_vcpu: 32+
  per_host_ram: 256+ GB
```

#### Medium Exercise Range (50-200 participants)

```yaml
range_profile: exercise_medium
total_vms: 200-500
teams: 4-8

vm_distribution_per_team:
  blue_zone:
    domain_controllers: 2
    file_servers: 2
    application_servers: 5
    siem: 1
    edr_console: 1
    vulnerability_scanner: 1
    workstations: 30
    
shared_infrastructure:
  grey_zone:
    dns_servers: 5
    web_servers: 20
    mail_relay: 2
    routers: 5
    
  red_zone:
    c2_servers: 4
    attack_boxes: 10
    redirectors: 6
    
  white_zone:
    automation_cluster: 3
    
  access_zone:
    guacamole_cluster: 3
    
  metrics_zone:
    scoring_engine: 2
    analytics: 1
    
compute_totals:
  vcpu: 1000-2000
  ram_gb: 2000-4000
  
host_requirements:
  hosts: 8-12
  per_host_vcpu: 64+
  per_host_ram: 512+ GB
```

#### Large Enterprise Range (200-500 participants)

```yaml
range_profile: enterprise_large
total_vms: 500-2000
teams: 10-20

vm_distribution_per_team:
  blue_zone:
    domain_controllers: 3
    file_servers: 3
    application_servers: 10
    database_servers: 3
    siem: 2
    edr_console: 2
    vulnerability_scanner: 2
    proxy_servers: 2
    workstations: 50
    
shared_infrastructure:
  grey_zone:
    dns_hierarchy: 10
    web_farms: 50
    mail_infrastructure: 5
    isp_simulation: 10
    cdn_nodes: 20
    
  red_zone:
    c2_infrastructure: 10
    attack_platforms: 20
    redirectors: 15
    phishing_infrastructure: 5
    
  white_zone:
    automation_cluster: 5
    scenario_engine: 3
    
  access_zone:
    guacamole_cluster: 10
    file_transfer: 3
    
  metrics_zone:
    scoring_cluster: 5
    analytics_cluster: 3
    dashboards: 2
    
  identity_zone:
    idp_servers: 3
    ca_servers: 4
    mfa_servers: 2
    
compute_totals:
  vcpu: 4000-8000
  ram_gb: 8000-16000
  
host_requirements:
  hosts: 25-40
  per_host_vcpu: 128+
  per_host_ram: 1024+ GB
```

### Consolidation Ratios

| Workload Type | vCPU:pCPU Ratio | Notes |
|---------------|-----------------|-------|
| General servers | 4:1 - 6:1 | Standard consolidation |
| Domain controllers | 2:1 - 4:1 | CPU-sensitive |
| SIEM/Analytics | 2:1 - 3:1 | I/O and CPU intensive |
| Workstations (NPC) | 8:1 - 10:1 | Mostly idle |
| Attack boxes | 2:1 - 4:1 | Burst CPU usage |

### Memory Overcommit Guidelines

| Scenario | Overcommit Ratio | Risk |
|----------|------------------|------|
| Conservative | 1:1 (none) | Low - guaranteed performance |
| Moderate | 1.25:1 | Low - minimal ballooning |
| Aggressive | 1.5:1 | Medium - possible swapping |
| Not recommended | >1.5:1 | High - performance degradation |

**Recommendation**: For cyber exercises, use 1:1 or 1.25:1 maximum to avoid performance issues during high-activity periods.

## Storage Sizing

### Storage Tier Allocation

```yaml
storage_tiers:
  tier_hot:
    technology: NVMe SSD
    use_case: Active VM disks, snapshots
    iops_target: 100000+
    latency_target: <1ms
    allocation_percentage: 30-40%
    
  tier_warm:
    technology: SSD or hybrid
    use_case: Golden images, recent backups
    iops_target: 10000-50000
    latency_target: <5ms
    allocation_percentage: 30-40%
    
  tier_cold:
    technology: HDD or object storage
    use_case: Archives, long-term retention
    iops_target: 1000-5000
    latency_target: <50ms
    allocation_percentage: 20-30%
```

### Storage Capacity Calculator

```python
def calculate_storage(num_teams: int, 
                      vms_per_team: int,
                      avg_vm_size_gb: float = 60,
                      snapshot_factor: float = 2.0,
                      golden_image_count: int = 20,
                      golden_image_size_gb: float = 50) -> dict:
    """
    Calculate storage requirements for a cyber range.
    
    Args:
        num_teams: Number of team enclaves
        vms_per_team: VMs per team (blue zone)
        avg_vm_size_gb: Average VM disk size
        snapshot_factor: Multiplier for snapshot overhead
        golden_image_count: Number of unique base images
        golden_image_size_gb: Average size of golden images
    
    Returns:
        Storage breakdown by tier
    """
    
    # Calculate VM storage
    team_vm_storage = num_teams * vms_per_team * avg_vm_size_gb
    
    # Shared infrastructure (grey, red, white, access, metrics)
    # Typically 20-30% of team storage
    shared_storage = team_vm_storage * 0.25
    
    # Total active VM storage
    active_storage = team_vm_storage + shared_storage
    
    # Snapshot overhead
    snapshot_storage = active_storage * (snapshot_factor - 1)
    
    # Golden images (linked clones can share base)
    golden_storage = golden_image_count * golden_image_size_gb
    
    # Archive/backup (1 full backup + incrementals)
    archive_storage = active_storage * 1.5
    
    return {
        "tier_hot_tb": round((active_storage + snapshot_storage) / 1024, 1),
        "tier_warm_tb": round((golden_storage + active_storage * 0.5) / 1024, 1),
        "tier_cold_tb": round(archive_storage / 1024, 1),
        "total_tb": round((active_storage + snapshot_storage + 
                          golden_storage + archive_storage) / 1024, 1),
        "breakdown": {
            "active_vms_gb": active_storage,
            "snapshots_gb": snapshot_storage,
            "golden_images_gb": golden_storage,
            "archives_gb": archive_storage
        }
    }

# Example calculations
print("Small range (2 teams, 50 VMs/team):")
print(calculate_storage(2, 50))

print("\nMedium range (8 teams, 50 VMs/team):")
print(calculate_storage(8, 50))

print("\nLarge range (20 teams, 75 VMs/team):")
print(calculate_storage(20, 75))
```

### Storage Reference Sizing

| Range Scale | Hot (TB) | Warm (TB) | Cold (TB) | Total (TB) |
|-------------|----------|-----------|-----------|------------|
| Small (2 teams) | 8-12 | 4-6 | 6-10 | 18-28 |
| Medium (8 teams) | 30-50 | 15-25 | 25-40 | 70-115 |
| Large (20 teams) | 80-120 | 40-60 | 60-90 | 180-270 |

### IOPS Requirements

| Component | Read IOPS | Write IOPS | Notes |
|-----------|-----------|------------|-------|
| Windows workstation (idle) | 10-50 | 5-20 | NPC activity |
| Windows workstation (active) | 100-500 | 50-200 | User simulation |
| Domain controller | 500-2000 | 200-500 | Authentication bursts |
| SIEM indexer | 1000-5000 | 2000-10000 | Write-heavy |
| Database server | 1000-5000 | 500-2000 | Varies by load |
| Range reset (snapshot revert) | 50000+ | N/A | Burst during reset |

## Network Sizing

### Bandwidth Requirements

| Traffic Type | Per-VM Bandwidth | Notes |
|--------------|------------------|-------|
| NPC web browsing | 1-5 Mbps | Bursty |
| NPC file access | 5-20 Mbps | Bursty |
| Domain auth | 0.1-1 Mbps | Low but latency-sensitive |
| SIEM log forwarding | 0.5-5 Mbps | Steady |
| VM console access | 2-10 Mbps | Per active user |
| C2 traffic | 0.1-2 Mbps | Depends on implant |
| Data exfiltration (exercise) | 10-100 Mbps | Simulated |

### Network Infrastructure Sizing

```yaml
small_range:
  core_switches:
    count: 2
    ports: 48
    speed: 10Gbps
    features: [L3, VLAN]
    
  hypervisor_connectivity:
    links_per_host: 2
    speed: 10Gbps
    bonding: LACP
    
  storage_network:
    type: dedicated
    speed: 10Gbps or 25Gbps
    
  total_vlans: 50-100

medium_range:
  core_switches:
    count: 2
    ports: 96+
    speed: 25Gbps
    features: [L3, VLAN, EVPN-VXLAN optional]
    
  spine_switches:
    count: 2
    ports: 32
    speed: 100Gbps
    
  hypervisor_connectivity:
    links_per_host: 4
    speed: 25Gbps
    bonding: LACP
    
  storage_network:
    type: dedicated fabric
    speed: 25Gbps or NVMe-oF
    
  total_vlans: 200-500

large_range:
  spine_layer:
    count: 4
    ports: 64
    speed: 100Gbps
    
  leaf_layer:
    count: 8-16
    ports: 48
    speed: 25Gbps
    uplinks: 4x100Gbps
    
  hypervisor_connectivity:
    links_per_host: 4
    speed: 25Gbps or 100Gbps
    bonding: LACP with load balancing
    
  storage_network:
    type: dedicated FC or NVMe-oF
    speed: 32Gbps FC or 100Gbps Ethernet
    
  total_vlans: 1000-4000
```

### VLAN Capacity Planning

| Component | VLANs Required | Formula |
|-----------|----------------|---------|
| Team enclaves | 4-6 per team | teams × 5 |
| Shared grey zone | 5-10 | Fixed |
| Red zone | 3-5 | Fixed |
| White/Access/Metrics | 5-10 | Fixed |
| Management | 3-5 | Fixed |
| Reserve | 20% of total | Buffer for expansion |

**Example**: 20 teams = (20 × 5) + 10 + 5 + 10 + 5 + 20% = 156 VLANs

## Cloud Cost Estimation

### AWS Reference Pricing (us-east-1, 2024)

| Resource | Type | Hourly Rate | Notes |
|----------|------|-------------|-------|
| Compute | m5.xlarge (4 vCPU, 16GB) | $0.192 | General purpose |
| Compute | m5.2xlarge (8 vCPU, 32GB) | $0.384 | SIEM, heavy workloads |
| Compute | c5.2xlarge (8 vCPU, 16GB) | $0.340 | Compute-optimized |
| Storage | gp3 SSD | $0.08/GB/mo | Standard performance |
| Storage | io2 SSD | $0.125/GB/mo | High IOPS |
| Network | Data transfer out | $0.09/GB | First 10TB/month |

### Monthly Cost Calculator

```python
def calculate_cloud_cost(
    num_vms: int,
    hours_per_day: float,
    days_per_month: int,
    avg_instance_hourly: float = 0.25,
    storage_gb: int = 5000,
    storage_rate_gb_month: float = 0.08,
    egress_gb: int = 500,
    egress_rate: float = 0.09
) -> dict:
    """
    Calculate monthly cloud costs for a cyber range.
    
    Args:
        num_vms: Number of VMs
        hours_per_day: Operating hours per day
        days_per_month: Operating days per month
        avg_instance_hourly: Average instance cost per hour
        storage_gb: Total storage in GB
        storage_rate_gb_month: Storage cost per GB per month
        egress_gb: Expected egress in GB
        egress_rate: Cost per GB egress
    
    Returns:
        Cost breakdown
    """
    
    compute_hours = num_vms * hours_per_day * days_per_month
    compute_cost = compute_hours * avg_instance_hourly
    
    storage_cost = storage_gb * storage_rate_gb_month
    
    egress_cost = egress_gb * egress_rate
    
    # Additional costs (load balancers, IPs, etc.) ~10%
    overhead = (compute_cost + storage_cost + egress_cost) * 0.10
    
    total = compute_cost + storage_cost + egress_cost + overhead
    
    return {
        "compute": round(compute_cost, 2),
        "storage": round(storage_cost, 2),
        "egress": round(egress_cost, 2),
        "overhead": round(overhead, 2),
        "total_monthly": round(total, 2),
        "cost_per_vm_month": round(total / num_vms, 2)
    }

# Example: 8-hour exercise days, 5 days/week
print("Training range (100 VMs, 8h/day, 20 days/month):")
print(calculate_cloud_cost(100, 8, 20))

print("\nExercise range (300 VMs, 12h/day, 10 days/month):")
print(calculate_cloud_cost(300, 12, 10, storage_gb=15000, egress_gb=2000))

print("\nPersistent range (500 VMs, 24/7):")
print(calculate_cloud_cost(500, 24, 30, storage_gb=30000, egress_gb=5000))
```

### Cost Optimization Strategies

| Strategy | Savings | Trade-off |
|----------|---------|-----------|
| Spot/Preemptible instances | 60-90% | Can be terminated |
| Reserved instances (1-year) | 30-40% | Commitment required |
| Auto-scaling | Variable | Complexity |
| Scheduled shutdown | Linear | Availability |
| Right-sizing | 20-40% | Ongoing analysis |
| Storage tiering | 20-30% | Performance tiers |

## Capacity Planning Formula

### Quick Sizing Formula

```
Hosts Required = (Total vCPU × Overcommit) / (Cores per Host × Threads)

Example:
- 2000 vCPU required
- 4:1 overcommit ratio
- 32-core hosts with HT (64 threads)

Hosts = (2000 / 4) / 64 = 7.8 → 8 hosts (round up)

Add 1-2 hosts for:
- N+1 redundancy
- Maintenance headroom
- Growth buffer

Final: 10 hosts recommended
```

### Memory-Based Sizing (Often the Constraint)

```
Hosts Required = Total RAM Required / (RAM per Host × Overcommit)

Example:
- 4000 GB RAM required
- 512 GB per host
- 1.25:1 overcommit

Hosts = 4000 / (512 × 1.25) = 6.25 → 7 hosts

With N+1: 8 hosts
```

### Storage IOPS Validation

```
Total IOPS Required = Σ(VM Count × IOPS per VM Profile)

Example:
- 100 workstations × 50 IOPS = 5,000
- 50 servers × 500 IOPS = 25,000
- 5 SIEM × 5000 IOPS = 25,000
- Reset burst allowance = 50,000

Total = 105,000 IOPS minimum

Storage system must support 105K+ IOPS sustained.
```
