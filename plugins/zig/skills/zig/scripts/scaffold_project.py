#!/usr/bin/env python3
"""
Scaffold a new Zig project with common structure and configurations.
"""

import os
import sys
from pathlib import Path

GITIGNORE_TEMPLATE = """# Zig build artifacts
zig-cache/
zig-out/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
"""

BUILD_ZIG_TEMPLATE = """const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const exe = b.addExecutable(.{{
        .name = "{name}",
        .root_module = b.createModule(.{{
            .root_source_file = b.path("src/main.zig"),
            .target = target,
            .optimize = optimize,
        }}),
    }});

    b.installArtifact(exe);

    const run_cmd = b.addRunArtifact(exe);
    run_cmd.step.dependOn(b.getInstallStep());
    if (b.args) |args| {{
        run_cmd.addArgs(args);
    }}

    const run_step = b.step("run", "Run the application");
    run_step.dependOn(&run_cmd.step);

    const tests = b.addTest(.{{
        .root_module = b.createModule(.{{
            .root_source_file = b.path("src/main.zig"),
            .target = target,
            .optimize = optimize,
        }}),
    }});

    const run_tests = b.addRunArtifact(tests);
    const test_step = b.step("test", "Run unit tests");
    test_step.dependOn(&run_tests.step);
}}
"""

BUILD_ZIG_ZON_TEMPLATE = """.{{
    .name = "{name}",
    .version = "0.1.0",
    .minimum_zig_version = "0.13.0",
    
    .dependencies = .{{}},
    
    .paths = .{{
        "build.zig",
        "build.zig.zon",
        "src",
        "README.md",
        "LICENSE",
    }},
}}
"""

MAIN_ZIG_TEMPLATE = """const std = @import("std");

pub fn main() !void {{
    const stdout = std.io.getStdOut().writer();
    try stdout.print("Hello from {name}!\\n", .{{}});
}}

test "basic test" {{
    const expect = std.testing.expect;
    try expect(2 + 2 == 4);
}}
"""

README_TEMPLATE = """# {name}

A Zig project.

## Building

```bash
zig build
```

## Running

```bash
zig build run
```

## Testing

```bash
zig build test
```

## Requirements

- Zig 0.13.0 or later
"""

LICENSE_MIT_TEMPLATE = """MIT License

Copyright (c) {year} {author}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def create_file(path: Path, content: str):
    """Create a file with the given content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)
    print(f"Created: {path}")


def scaffold_project(name: str, author: str = ""):
    """Create a new Zig project structure."""
    from datetime import datetime
    
    project_dir = Path(name)
    
    if project_dir.exists():
        print(f"Error: Directory '{name}' already exists")
        sys.exit(1)
    
    print(f"Creating Zig project: {name}")
    
    # Create directory structure
    (project_dir / "src").mkdir(parents=True)
    
    # Create files
    year = datetime.now().year
    
    create_file(
        project_dir / ".gitignore",
        GITIGNORE_TEMPLATE
    )
    
    create_file(
        project_dir / "build.zig",
        BUILD_ZIG_TEMPLATE.format(name=name)
    )
    
    create_file(
        project_dir / "build.zig.zon",
        BUILD_ZIG_ZON_TEMPLATE.format(name=name)
    )
    
    create_file(
        project_dir / "src" / "main.zig",
        MAIN_ZIG_TEMPLATE.format(name=name)
    )
    
    create_file(
        project_dir / "README.md",
        README_TEMPLATE.format(name=name)
    )
    
    if author:
        create_file(
            project_dir / "LICENSE",
            LICENSE_MIT_TEMPLATE.format(year=year, author=author)
        )
    
    print(f"\n✓ Project '{name}' created successfully!")
    print(f"\nNext steps:")
    print(f"  cd {name}")
    print(f"  zig build run")


def main():
    if len(sys.argv) < 2:
        print("Usage: scaffold_project.py <project-name> [author-name]")
        sys.exit(1)
    
    name = sys.argv[1]
    author = sys.argv[2] if len(sys.argv) > 2 else ""
    
    scaffold_project(name, author)


if __name__ == "__main__":
    main()
