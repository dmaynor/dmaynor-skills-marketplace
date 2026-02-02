#!/usr/bin/env python3
"""
AD Population Component Generator

Generates PowerShell scripts and CSV data for populating Active Directory
with realistic organizational structure based on context.

Usage:
    python gen_ad_population.py --context org-context.yaml --output ./ad-population/
"""

import argparse
import csv
import random
import string
from datetime import datetime
from pathlib import Path
from typing import List

import yaml

FIRST_NAMES = [
    'James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda',
    'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica',
    'Thomas', 'Sarah', 'Charles', 'Karen', 'Christopher', 'Lisa', 'Daniel', 'Nancy',
    'Matthew', 'Betty', 'Anthony', 'Margaret', 'Mark', 'Sandra', 'Donald', 'Ashley',
    'Wei', 'Priya', 'Mohammed', 'Fatima', 'Carlos', 'Maria', 'Andrei', 'Yuki',
    'Raj', 'Aisha', 'Jin', 'Mei', 'Ahmed', 'Sofia', 'Viktor', 'Anna',
]

LAST_NAMES = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
    'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
    'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Perez', 'Thompson',
    'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson', 'Walker',
    'Chen', 'Patel', 'Kim', 'Singh', 'Kumar', 'Zhang', 'Wang', 'Ivanov', 'Müller',
]

JOB_TITLES = {
    'Executive': ['CEO', 'CFO', 'CTO', 'COO', 'CISO', 'VP', 'SVP', 'Director'],
    'Technology': ['Software Engineer', 'DevOps Engineer', 'Systems Administrator', 
                   'Network Engineer', 'Security Analyst', 'IT Support', 'DBA'],
    'Finance': ['Financial Analyst', 'Accountant', 'Controller', 'Auditor', 'Tax Specialist'],
    'Operations': ['Operations Manager', 'Project Manager', 'Business Analyst', 'QA'],
    'Human Resources': ['HR Manager', 'Recruiter', 'HR Generalist', 'Benefits Admin'],
    'default': ['Manager', 'Analyst', 'Specialist', 'Coordinator', 'Associate'],
}


def load_context(context_path: Path) -> dict:
    with open(context_path, 'r') as f:
        return yaml.safe_load(f)


def generate_username(first: str, last: str, existing: set) -> str:
    base = (first[0] + last).lower()[:20]
    username = base
    counter = 1
    while username in existing:
        username = f"{base}{counter}"
        counter += 1
    return username


def generate_password() -> str:
    upper = random.choice(string.ascii_uppercase)
    lower = ''.join(random.choices(string.ascii_lowercase, k=6))
    digit = ''.join(random.choices(string.digits, k=2))
    special = random.choice('!@#$%^&*')
    chars = list(upper + lower + digit + special + random.choice(string.ascii_letters))
    random.shuffle(chars)
    return ''.join(chars)


def generate_users(context: dict) -> List[dict]:
    org = context['organization']
    departments = org.get('structure', {}).get('departments', [])
    internal_domain = org.get('internal_domain', 'corp.local')
    dc_parts = internal_domain.replace('.', ',DC=')
    
    users = []
    usernames = set()
    
    for dept in departments:
        dept_name = dept['name']
        headcount = dept.get('headcount', 10)
        prefix = dept.get('prefix', dept_name[:4].upper())
        titles = JOB_TITLES.get(dept_name, JOB_TITLES['default'])
        
        for i in range(headcount):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            username = generate_username(first, last, usernames)
            usernames.add(username)
            
            if i == 0:
                title = f"{dept_name} Director"
            elif i < headcount * 0.1:
                title = f"Senior {random.choice(titles)}"
            else:
                title = random.choice(titles)
            
            users.append({
                'username': username,
                'first_name': first,
                'last_name': last,
                'display_name': f"{first} {last}",
                'email': f"{username}@{org['domain']}",
                'upn': f"{username}@{internal_domain}",
                'department': dept_name,
                'title': title,
                'ou': f"OU={dept_name},OU=Users,DC={dc_parts}",
                'password': generate_password(),
                'employee_id': f"{prefix}{str(i+1).zfill(4)}",
                'manager': '',
            })
    
    # Assign managers
    for dept in departments:
        dept_users = [u for u in users if u['department'] == dept['name']]
        if len(dept_users) > 1:
            director = dept_users[0]
            for user in dept_users[1:]:
                user['manager'] = director['username']
    
    return users


def generate_groups(context: dict, users: List[dict]) -> List[dict]:
    org = context['organization']
    departments = org.get('structure', {}).get('departments', [])
    internal_domain = org.get('internal_domain', 'corp.local')
    dc_parts = internal_domain.replace('.', ',DC=')
    
    groups = []
    
    for dept in departments:
        members = [u['username'] for u in users if u['department'] == dept['name']]
        groups.append({
            'name': f"GRP_{dept['prefix']}_Users",
            'description': f"All users in {dept['name']}",
            'ou': f"OU=Groups,DC={dc_parts}",
            'members': ';'.join(members),
            'type': 'Security',
            'scope': 'Global',
        })
    
    # Global groups
    groups.append({
        'name': 'GRP_All_Employees',
        'description': 'All employees',
        'ou': f"OU=Groups,DC={dc_parts}",
        'members': ';'.join(u['username'] for u in users),
        'type': 'Security',
        'scope': 'Global',
    })
    
    vpn_users = random.sample([u['username'] for u in users], k=min(len(users)//3, len(users)))
    groups.append({
        'name': 'GRP_VPN_Users',
        'description': 'VPN access authorized',
        'ou': f"OU=Groups,DC={dc_parts}",
        'members': ';'.join(vpn_users),
        'type': 'Security',
        'scope': 'Global',
    })
    
    return groups


def generate_powershell(users: List[dict], groups: List[dict], context: dict) -> str:
    org = context['organization']
    internal_domain = org.get('internal_domain', 'corp.local')
    dc_parts = internal_domain.replace('.', ',DC=')
    departments = org.get('structure', {}).get('departments', [])
    
    script = f'''#Requires -Modules ActiveDirectory
<#
.SYNOPSIS
    Populates AD with organizational structure for {org['name']}
.NOTES
    Generated: {datetime.now().isoformat()}
    Run as Domain Admin on domain controller
#>

param([switch]$WhatIf)

$ErrorActionPreference = "Stop"

Write-Host "=== AD Population for {org['name']} ===" -ForegroundColor Cyan

# Create OUs
Write-Host "`n[1/3] Creating OUs..." -ForegroundColor Yellow
$baseOU = "DC={dc_parts}"

$ous = @("Users", "Groups", "Computers", "Service Accounts")
foreach ($ou in $ous) {{
    $path = "OU=$ou,$baseOU"
    if (-not (Get-ADOrganizationalUnit -Filter "DistinguishedName -eq '$path'" -EA SilentlyContinue)) {{
        if ($WhatIf) {{ Write-Host "  [WhatIf] Create OU: $ou" }}
        else {{ New-ADOrganizationalUnit -Name $ou -Path $baseOU; Write-Host "  Created: $ou" -ForegroundColor Green }}
    }}
}}

# Department OUs
$depts = @({', '.join(f'"{d["name"]}"' for d in departments)})
foreach ($dept in $depts) {{
    $path = "OU=$dept,OU=Users,$baseOU"
    if (-not (Get-ADOrganizationalUnit -Filter "DistinguishedName -eq '$path'" -EA SilentlyContinue)) {{
        if ($WhatIf) {{ Write-Host "  [WhatIf] Create OU: $dept" }}
        else {{ New-ADOrganizationalUnit -Name $dept -Path "OU=Users,$baseOU"; Write-Host "  Created: $dept" -ForegroundColor Green }}
    }}
}}

# Create Users
Write-Host "`n[2/3] Creating Users..." -ForegroundColor Yellow
$users = Import-Csv "$PSScriptRoot\\users.csv"
$created = 0

foreach ($user in $users) {{
    if (Get-ADUser -Filter "SamAccountName -eq '$($user.username)'" -EA SilentlyContinue) {{ continue }}
    
    if ($WhatIf) {{ Write-Host "  [WhatIf] Create: $($user.username)" }}
    else {{
        $pwd = ConvertTo-SecureString $user.password -AsPlainText -Force
        New-ADUser -SamAccountName $user.username -UserPrincipalName $user.upn `
            -Name $user.display_name -GivenName $user.first_name -Surname $user.last_name `
            -EmailAddress $user.email -Department $user.department -Title $user.title `
            -EmployeeID $user.employee_id -Path $user.ou -AccountPassword $pwd -Enabled $true
        $created++
    }}
}}
Write-Host "  Created $created users" -ForegroundColor Green

# Set managers
foreach ($user in $users) {{
    if ($user.manager -and -not $WhatIf) {{
        $mgr = (Get-ADUser $user.manager).DistinguishedName
        Set-ADUser $user.username -Manager $mgr
    }}
}}

# Create Groups
Write-Host "`n[3/3] Creating Groups..." -ForegroundColor Yellow
$groups = Import-Csv "$PSScriptRoot\\groups.csv"

foreach ($grp in $groups) {{
    if (Get-ADGroup -Filter "Name -eq '$($grp.name)'" -EA SilentlyContinue) {{ continue }}
    
    if ($WhatIf) {{ Write-Host "  [WhatIf] Create: $($grp.name)" }}
    else {{
        New-ADGroup -Name $grp.name -GroupScope $grp.scope -GroupCategory $grp.type `
            -Description $grp.description -Path $grp.ou
        
        $members = $grp.members -split ";"
        foreach ($m in $members) {{ if ($m) {{ Add-ADGroupMember $grp.name -Members $m }} }}
        Write-Host "  Created: $($grp.name) ($($members.Count) members)" -ForegroundColor Green
    }}
}}

Write-Host "`n=== Complete ===" -ForegroundColor Cyan
'''
    return script


def main():
    parser = argparse.ArgumentParser(description="Generate AD population component")
    parser.add_argument('--context', '-c', type=Path, required=True)
    parser.add_argument('--output', '-o', type=Path, default=Path('./ad-population'))
    args = parser.parse_args()
    
    context = load_context(args.context)
    org = context['organization']
    
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    
    users = generate_users(context)
    groups = generate_groups(context, users)
    
    # Write CSVs
    with open(output / 'users.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=users[0].keys())
        writer.writeheader()
        writer.writerows(users)
    
    with open(output / 'groups.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=groups[0].keys())
        writer.writeheader()
        writer.writerows(groups)
    
    # Write PowerShell
    with open(output / 'Populate-AD.ps1', 'w') as f:
        f.write(generate_powershell(users, groups, context))
    
    print(f"Generated AD population: {output}")
    print(f"  Organization: {org['name']}")
    print(f"  Users: {len(users)}")
    print(f"  Groups: {len(groups)}")


if __name__ == "__main__":
    main()
