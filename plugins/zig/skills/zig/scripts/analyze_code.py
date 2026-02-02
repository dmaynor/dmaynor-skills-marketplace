#!/usr/bin/env python3
"""
Analyze Zig source files for common issues and provide suggestions.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

class ZigLintIssue:
    def __init__(self, file: str, line: int, severity: str, message: str):
        self.file = file
        self.line = line
        self.severity = severity
        self.message = message
    
    def __str__(self):
        return f"{self.file}:{self.line}: [{self.severity}] {self.message}"


def check_allocator_leaks(content: str, filename: str) -> List[ZigLintIssue]:
    """Check for potential memory leaks from missing defer after alloc."""
    issues = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        # Look for allocator.alloc or allocator.create
        if re.search(r'\.alloc\(|\.create\(', line):
            # Check if there's a defer in the next few lines
            has_defer = False
            for j in range(i, min(i + 5, len(lines))):
                if 'defer' in lines[j]:
                    has_defer = True
                    break
            
            if not has_defer:
                issues.append(ZigLintIssue(
                    filename, i, "warning",
                    "Allocation without defer - potential memory leak"
                ))
    
    return issues


def check_error_handling(content: str, filename: str) -> List[ZigLintIssue]:
    """Check for missing error handling."""
    issues = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        # Look for function calls that might return errors without try/catch
        if re.search(r'\w+\(.*\)[^;]*;', line):
            if '!' in line and 'try' not in line and 'catch' not in line:
                # Might be an error union without handling
                if not line.strip().startswith('//'):
                    issues.append(ZigLintIssue(
                        filename, i, "info",
                        "Consider using 'try' or 'catch' for error handling"
                    ))
    
    return issues


def check_undefined_variables(content: str, filename: str) -> List[ZigLintIssue]:
    """Check for use of undefined variables without initialization."""
    issues = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        # Look for 'var x: Type = undefined;' followed by immediate use
        if 'undefined' in line and 'var' in line:
            var_match = re.search(r'var\s+(\w+)', line)
            if var_match:
                var_name = var_match.group(1)
                # Check next few lines for use before assignment
                for j in range(i, min(i + 3, len(lines))):
                    next_line = lines[j]
                    if var_name in next_line and '=' not in next_line:
                        issues.append(ZigLintIssue(
                            filename, i, "warning",
                            f"Variable '{var_name}' may be used before initialization"
                        ))
                        break
    
    return issues


def check_comptime_opportunities(content: str, filename: str) -> List[ZigLintIssue]:
    """Suggest places where comptime could be used."""
    issues = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        # Look for function parameters that might benefit from comptime
        if re.search(r'fn\s+\w+\([^)]*type[^)]*\)', line):
            if 'comptime' not in line:
                issues.append(ZigLintIssue(
                    filename, i, "info",
                    "Consider using 'comptime' for type parameters"
                ))
    
    return issues


def check_naming_conventions(content: str, filename: str) -> List[ZigLintIssue]:
    """Check Zig naming conventions."""
    issues = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        # Check for camelCase types (should be PascalCase)
        type_match = re.search(r'const\s+([a-z]\w*)\s*=\s*struct', line)
        if type_match:
            issues.append(ZigLintIssue(
                filename, i, "style",
                f"Type '{type_match.group(1)}' should use PascalCase"
            ))
        
        # Check for PascalCase variables (should be camelCase)
        var_match = re.search(r'(var|const)\s+([A-Z]\w*)\s*:', line)
        if var_match and 'struct' not in line and 'enum' not in line:
            issues.append(ZigLintIssue(
                filename, i, "style",
                f"Variable '{var_match.group(2)}' should use camelCase"
            ))
    
    return issues


def check_slice_bounds(content: str, filename: str) -> List[ZigLintIssue]:
    """Check for potential slice bounds issues."""
    issues = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        # Look for slice operations with hardcoded indices
        if re.search(r'\[\d+\.\.\]|\[\.\.\d+\]', line):
            issues.append(ZigLintIssue(
                filename, i, "info",
                "Consider bounds checking for slice operation"
            ))
    
    return issues


def analyze_file(filepath: Path) -> List[ZigLintIssue]:
    """Analyze a single Zig file."""
    try:
        content = filepath.read_text()
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return []
    
    issues = []
    filename = str(filepath)
    
    issues.extend(check_allocator_leaks(content, filename))
    issues.extend(check_error_handling(content, filename))
    issues.extend(check_undefined_variables(content, filename))
    issues.extend(check_comptime_opportunities(content, filename))
    issues.extend(check_naming_conventions(content, filename))
    issues.extend(check_slice_bounds(content, filename))
    
    return issues


def analyze_directory(directory: Path) -> List[ZigLintIssue]:
    """Analyze all Zig files in a directory."""
    issues = []
    
    for zig_file in directory.rglob("*.zig"):
        # Skip build artifacts
        if 'zig-cache' in str(zig_file) or 'zig-out' in str(zig_file):
            continue
        
        issues.extend(analyze_file(zig_file))
    
    return issues


def main():
    if len(sys.argv) < 2:
        print("Usage: analyze_code.py <file-or-directory>")
        sys.exit(1)
    
    path = Path(sys.argv[1])
    
    if not path.exists():
        print(f"Error: {path} does not exist")
        sys.exit(1)
    
    if path.is_file():
        issues = analyze_file(path)
    else:
        issues = analyze_directory(path)
    
    if not issues:
        print("✓ No issues found!")
        return
    
    # Group by severity
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    infos = [i for i in issues if i.severity == "info"]
    styles = [i for i in issues if i.severity == "style"]
    
    for issue in errors + warnings + infos + styles:
        print(issue)
    
    print(f"\nSummary: {len(errors)} errors, {len(warnings)} warnings, "
          f"{len(infos)} suggestions, {len(styles)} style issues")
    
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
