# Zig Build System Reference

## build.zig Structure

The build system is written in Zig itself, providing full programmatic control.

### Basic build.zig Template

```zig
const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // Executable
    const exe = b.addExecutable(.{
        .name = "myapp",
        .root_module = b.createModule(.{
            .root_source_file = b.path("src/main.zig"),
            .target = target,
            .optimize = optimize,
        }),
    });
    b.installArtifact(exe);

    // Run step
    const run_cmd = b.addRunArtifact(exe);
    run_cmd.step.dependOn(b.getInstallStep());
    const run_step = b.step("run", "Run the application");
    run_step.dependOn(&run_cmd.step);

    // Tests
    const tests = b.addTest(.{
        .root_module = b.createModule(.{
            .root_source_file = b.path("src/main.zig"),
            .target = target,
            .optimize = optimize,
        }),
    });
    const run_tests = b.addRunArtifact(tests);
    const test_step = b.step("test", "Run unit tests");
    test_step.dependOn(&run_tests.step);
}
```

### Library Configuration

```zig
// Static library
const lib = b.addStaticLibrary(.{
    .name = "mylib",
    .root_module = b.createModule(.{
        .root_source_file = b.path("src/lib.zig"),
        .target = target,
        .optimize = optimize,
    }),
});

// Shared library
const shared_lib = b.addSharedLibrary(.{
    .name = "mylib",
    .root_module = b.createModule(.{
        .root_source_file = b.path("src/lib.zig"),
        .target = target,
        .optimize = optimize,
    }),
});
```

### Adding Dependencies

```zig
// From build.zig.zon
const dep = b.dependency("some_dep", .{
    .target = target,
    .optimize = optimize,
});
exe.root_module.addImport("some_dep", dep.module("some_dep"));

// C library
exe.linkLibC();
exe.linkSystemLibrary("sqlite3");

// Include paths
exe.addIncludePath(b.path("include"));

// C source files
exe.addCSourceFiles(.{
    .files = &.{"src/legacy.c", "src/utils.c"},
    .flags = &.{"-Wall", "-O2"},
});
```

### Cross-Compilation

```bash
# List available targets
zig targets

# Build for specific target
zig build -Dtarget=x86_64-linux-gnu
zig build -Dtarget=aarch64-macos
zig build -Dtarget=x86_64-windows-gnu
zig build -Dtarget=wasm32-freestanding
```

### Optimization Modes

```bash
zig build -Doptimize=Debug          # Default, includes debug info
zig build -Doptimize=ReleaseSafe    # Optimized with safety checks
zig build -Doptimize=ReleaseFast    # Maximum speed
zig build -Doptimize=ReleaseSmall   # Minimize binary size
```

## build.zig.zon (Package Manifest)

```zig
.{
    .name = "myproject",
    .version = "0.1.0",
    .minimum_zig_version = "0.13.0",
    .dependencies = .{
        .some_dep = .{
            .url = "https://github.com/user/repo/archive/refs/tags/v1.0.0.tar.gz",
            .hash = "1220...",  // Use any hash, zig will show correct one
        },
        .git_dep = .{
            .url = "git+https://github.com/user/repo#main",
            .hash = "1220...",
        },
    },
    .paths = .{
        "build.zig",
        "build.zig.zon",
        "src",
        "README.md",
        "LICENSE",
    },
}
```

### Dependency Management

```bash
# Add dependency
zig fetch --save https://github.com/user/repo/archive/v1.0.0.tar.gz
zig fetch --save git+https://github.com/user/repo#main

# Update dependencies
zig build --fetch

# Use local path for development
# In build.zig.zon:
.local_dep = .{
    .path = "../local-package",
},
```

## Custom Build Steps

```zig
// Custom step
const custom_step = b.step("custom", "Run custom command");
const custom_cmd = b.addSystemCommand(&.{"python3", "scripts/generate.py"});
custom_step.dependOn(&custom_cmd.step);

// Generate files before build
const codegen = b.addSystemCommand(&.{"python3", "codegen.py"});
exe.step.dependOn(&codegen.step);

// Install additional files
b.installFile("config/default.cfg", "bin/config.cfg");
b.installDirectory(.{
    .source_dir = b.path("assets"),
    .install_dir = .prefix,
    .install_subdir = "assets",
});
```

## Build Options

```zig
// Define build options
const enable_logging = b.option(bool, "enable-logging", "Enable debug logging") orelse false;
const max_clients = b.option(u32, "max-clients", "Maximum concurrent clients") orelse 100;

const options = b.addOptions();
options.addOption(bool, "enable_logging", enable_logging);
options.addOption(u32, "max_clients", max_clients);

exe.root_module.addOptions("config", options);
```

Use in code:
```zig
const config = @import("config");

if (config.enable_logging) {
    std.debug.print("Logging enabled\n", .{});
}
```

## Common Build Patterns

### Multiple Executables

```zig
const executables = [_]struct {
    name: []const u8,
    src: []const u8,
}{
    .{ .name = "server", .src = "src/server.zig" },
    .{ .name = "client", .src = "src/client.zig" },
    .{ .name = "admin", .src = "src/admin.zig" },
};

for (executables) |spec| {
    const exe = b.addExecutable(.{
        .name = spec.name,
        .root_module = b.createModule(.{
            .root_source_file = b.path(spec.src),
            .target = target,
            .optimize = optimize,
        }),
    });
    b.installArtifact(exe);
}
```

### Conditional Compilation

```zig
// Platform-specific source
if (target.result.os.tag == .windows) {
    exe.addCSourceFile(.{
        .file = b.path("src/platform_windows.c"),
        .flags = &.{"-DWINDOWS"},
    });
} else {
    exe.addCSourceFile(.{
        .file = b.path("src/platform_unix.c"),
        .flags = &.{"-DUNIX"},
    });
}
```

## Testing Configuration

```zig
// Test with different settings
const test_filters = b.option([]const []const u8, "test-filter", "Test name filter");

const tests = b.addTest(.{
    .root_module = b.createModule(.{
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
    }),
});

if (test_filters) |filters| {
    for (filters) |filter| {
        tests.filters = try std.mem.concat(
            b.allocator,
            []const u8,
            &.{ tests.filters, &.{filter} },
        );
    }
}

const run_tests = b.addRunArtifact(tests);
const test_step = b.step("test", "Run unit tests");
test_step.dependOn(&run_tests.step);
```

## Common Commands

```bash
zig init                      # Initialize new project
zig build                     # Build project
zig build run                 # Build and run
zig build test                # Run tests
zig build install             # Install to prefix
zig build --help              # Show available options
zig build --verbose           # Verbose output
zig build --summary all       # Show build summary
```
