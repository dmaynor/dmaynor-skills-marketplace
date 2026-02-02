---
name: zig
description: "This skill should be used when the user asks to write Zig code, configure build.zig, create build.zig.zon package manifests, or work with .zig files. Triggers on: Zig syntax, allocators, comptime, error unions, defer/errdefer, slices, optionals, cross-compilation, C interop, or any request mentioning Zig explicitly. Covers build system, testing, memory management, generics via comptime, and idiomatic patterns."
version: 0.1.0
---

# Zig Programming

Systems programming language emphasizing explicit behavior, manual memory management, and compile-time metaprogramming. Target version: **0.13+** (adapt for older versions as needed).

## Additional Resources

This skill includes supplementary materials:

- **references/build-system.md** - Comprehensive build.zig and build.zig.zon guide, cross-compilation, dependency management
- **references/comptime-metaprogramming.md** - Advanced comptime techniques, generics, reflection, code generation
- **references/c-interop.md** - C library integration, FFI patterns, type conversions, exporting to C
- **scripts/scaffold_project.py** - Create new Zig projects with standard structure
- **scripts/analyze_code.py** - Static analysis tool for common Zig issues and best practices

## Core Philosophy

- No hidden control flow or memory allocations
- Allocators passed explicitly as parameters
- Errors are values, not exceptions
- `comptime` replaces macros and generics
- Direct C interoperability

## Project Structure

```
project/
├── build.zig           # Build configuration (Zig code)
├── build.zig.zon       # Package manifest (Zig Object Notation)
├── src/
│   ├── main.zig        # Entry point
│   └── lib.zig         # Library root (if library)
└── zig-out/            # Build output (gitignore)
```

## build.zig Essentials

```zig
const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const exe = b.addExecutable(.{
        .name = "myapp",
        .root_module = b.createModule(.{
            .root_source_file = b.path("src/main.zig"),
            .target = target,
            .optimize = optimize,
        }),
    });
    b.installArtifact(exe);

    const run_cmd = b.addRunArtifact(exe);
    run_cmd.step.dependOn(b.getInstallStep());
    const run_step = b.step("run", "Run the application");
    run_step.dependOn(&run_cmd.step);

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

## build.zig.zon Package Manifest

```zig
.{
    .name = "myproject",
    .version = "0.1.0",
    .dependencies = .{
        .some_dep = .{
            .url = "https://github.com/user/repo/archive/refs/tags/v1.0.0.tar.gz",
            .hash = "1220...",
        },
    },
    .paths = .{""},
}
```

Add dependencies: `zig fetch --save <url>`

Use in build.zig:
```zig
const dep = b.dependency("some_dep", .{ .target = target, .optimize = optimize });
exe.root_module.addImport("some_dep", dep.module("some_dep"));
```

## Key Types Quick Reference

| Type | Example | Notes |
|------|---------|-------|
| Integers | `i32`, `u64`, `usize` | Signed/unsigned, platform-dependent `usize` |
| Floats | `f32`, `f64` | IEEE 754 |
| Optional | `?T` | `null` or value; unwrap with `if (x) \|v\|`, `orelse`, `.?` |
| Error union | `E!T` | Error or value; handle with `try`, `catch` |
| Slice | `[]const u8` | Pointer + length; strings are `[]const u8` |
| Sentinel | `[*:0]const u8` | Null-terminated for C interop |
| Array | `[5]u8` | Fixed-size, stack-allocated |

## Memory Management

Pass allocators explicitly. Use `defer` for cleanup:

```zig
fn createBuffer(allocator: Allocator, size: usize) ![]u8 {
    return try allocator.alloc(u8, size);
}

// Usage
const buffer = try createBuffer(allocator, 100);
defer allocator.free(buffer);
```

Common allocators: `std.heap.GeneralPurposeAllocator(.{})` (debug), `std.heap.ArenaAllocator` (bulk free), `std.heap.page_allocator` (OS pages), `std.testing.allocator` (tests, detects leaks).

## Error Handling

```zig
// try: propagate errors
const file = try std.fs.cwd().openFile(path, .{});
defer file.close();

// catch: handle inline
const result = doThing() catch |err| switch (err) {
    error.NotFound => return null,
    else => return err,
};

// errdefer: cleanup only on error return
const data = try allocator.alloc(u8, 100);
errdefer allocator.free(data);
try validateData(data);
return data;
```

## Comptime (Generics & Metaprogramming)

```zig
// Generic function
fn max(comptime T: type, a: T, b: T) T {
    return if (a > b) a else b;
}

// Generic data structure
fn Stack(comptime T: type) type {
    return struct {
        items: []T,
        const Self = @This();
        pub fn push(self: *Self, item: T) !void { ... }
    };
}

// Type reflection
inline for (@typeInfo(T).@"struct".fields) |field| {
    std.debug.print("{s}\n", .{field.name});
}
```

## Testing

```zig
const std = @import("std");
const expect = std.testing.expect;
const expectEqual = std.testing.expectEqual;

test "basic test" {
    const allocator = std.testing.allocator; // Detects leaks
    const buf = try allocator.alloc(u8, 10);
    defer allocator.free(buf);
    try expectEqual(@as(usize, 10), buf.len);
}
```

Run: `zig build test` or `zig test src/main.zig`

## C Interop

```zig
const c = @cImport({
    @cInclude("stdio.h");
});

_ = c.printf("Hello from C!\n");
```

In build.zig (on the module, not the compile step):
```zig
mod.linkLibC();
mod.addIncludePath(b.path("include"));
mod.addCSourceFiles(.{
    .files = &.{"src/legacy.c"},
    .flags = &.{"-Wall", "-O2"},
});
```

## Build Commands

```bash
zig init                    # Initialize new project
zig build                   # Build project
zig build run               # Build and run
zig build test              # Run tests
zig build -Doptimize=ReleaseFast  # Release build
zig build -Dtarget=x86_64-linux-gnu  # Cross-compile
zig build -Dtarget=aarch64-macos     # Cross-compile macOS ARM
zig build -Dtarget=x86_64-windows-gnu # Cross-compile Windows
```

## Common Pitfalls

| Issue | Solution |
|-------|----------|
| Dangling pointer from slice | Copy data or ensure lifetime |
| Memory leak | Use `defer allocator.free()` immediately after alloc |
| Use after free | Careful with `errdefer` vs `defer` ordering |
| `var` when `const` works | Zig enforces `const` for non-mutated variables |
| Forgetting `try` | Compiler error: "error is ignored" |
| `std.io.getStdOut()` missing (0.15+) | Use `std.fs.File.stdout()` instead |
| `File.writer()` needs buffer (0.15+) | Pass `[]u8` buffer arg, or use `writeAll()` directly |
| Build API changed (0.15+) | Use `b.createModule()` → `b.addExecutable(.{ .root_module = mod })` |

## Additional Resources

### Reference Files

For detailed type definitions, patterns, and standard library usage:
- **`references/types-and-patterns.md`** — Complete type system (structs, enums, tagged unions, optionals, error unions), common patterns (iterator, builder, state machine), and standard library highlights (ArrayList, HashMap, File I/O, JSON, threads)
