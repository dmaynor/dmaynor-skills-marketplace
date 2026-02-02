# C Interoperability in Zig

Zig provides seamless interoperability with C libraries and can be used as a better C compiler.

## Importing C Headers

### Basic @cImport

```zig
const c = @cImport({
    @cInclude("stdio.h");
    @cInclude("stdlib.h");
    @cInclude("string.h");
});

pub fn main() void {
    _ = c.printf("Hello from C!\n");
    
    const ptr = c.malloc(100);
    defer c.free(ptr);
}
```

### With Defines and Configuration

```zig
const c = @cImport({
    @cDefine("_GNU_SOURCE", "1");
    @cDefine("DEBUG", {});
    @cInclude("pthread.h");
    @cInclude("unistd.h");
});
```

## Build Configuration for C

### In build.zig

```zig
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

    // Link libc
    exe.linkLibC();

    // Link system library
    exe.linkSystemLibrary("sqlite3");
    exe.linkSystemLibrary("curl");

    // Add include paths
    exe.addIncludePath(b.path("include"));
    exe.addIncludePath(b.path("vendor/include"));

    // Add C source files
    exe.addCSourceFiles(.{
        .files = &.{
            "src/legacy.c",
            "src/utils.c",
            "vendor/lib.c",
        },
        .flags = &.{
            "-Wall",
            "-Wextra",
            "-O2",
            "-std=c11",
        },
    });

    // Link static library
    exe.addObjectFile(b.path("lib/libfoo.a"));

    b.installArtifact(exe);
}
```

## Type Conversions

### Zig to C Types

| Zig Type | C Type | Notes |
|----------|--------|-------|
| `i8`, `i16`, `i32`, `i64` | `int8_t`, `int16_t`, `int32_t`, `int64_t` | Signed integers |
| `u8`, `u16`, `u32`, `u64` | `uint8_t`, `uint16_t`, `uint32_t`, `uint64_t` | Unsigned integers |
| `f32`, `f64` | `float`, `double` | Floating point |
| `bool` | `bool` (C99) | Boolean (0 or 1) |
| `*T` | `T*` | Pointer |
| `[*]T` | `T*` | Many-item pointer (no length) |
| `[*:0]const u8` | `const char*` | Null-terminated string |
| `?*T` | `T*` | Optional pointer (nullable) |
| `extern struct` | `struct` | C-compatible struct |

### String Conversions

```zig
// Zig string to C string (must be null-terminated)
const zig_str: []const u8 = "hello";
const c_str: [*:0]const u8 = @ptrCast(zig_str.ptr);  // Unsafe!

// Safe conversion using sentinel
const zig_str_z: [:0]const u8 = "hello";  // Sentinel-terminated slice
const c_str_safe: [*:0]const u8 = zig_str_z.ptr;

// C string to Zig slice
const c_string: [*:0]const u8 = c.some_c_function();
const zig_slice: []const u8 = std.mem.span(c_string);

// Allocate null-terminated copy
const allocator = std.heap.page_allocator;
const c_allocated = try std.fmt.allocPrintZ(allocator, "{s}", .{"hello"});
defer allocator.free(c_allocated);
_ = c.printf("%s\n", c_allocated.ptr);
```

## Calling C Functions

### Basic Function Calls

```zig
const c = @cImport({
    @cInclude("math.h");
});

pub fn main() void {
    const x: f64 = 2.0;
    const result = c.sqrt(x);
    std.debug.print("sqrt({d}) = {d}\n", .{ x, result });
}
```

### Functions with Pointers

```zig
const c = @cImport({
    @cInclude("string.h");
});

pub fn copyString(dest: [*]u8, src: [*:0]const u8, n: usize) void {
    _ = c.strncpy(dest, src, n);
}

pub fn compareStrings(s1: [*:0]const u8, s2: [*:0]const u8) i32 {
    return c.strcmp(s1, s2);
}
```

### Error Handling with C Functions

```zig
const c = @cImport({
    @cInclude("errno.h");
    @cInclude("string.h");
    @cInclude("stdio.h");
});

pub fn openFileC(path: [*:0]const u8) !*c.FILE {
    const file = c.fopen(path, "r");
    if (file == null) {
        const err = c.errno;
        std.debug.print("Error: {s}\n", .{c.strerror(err)});
        return error.OpenFailed;
    }
    return file.?;
}
```

## C Structs

### Defining C-Compatible Structs

```zig
// C struct definition
const CPoint = extern struct {
    x: f64,
    y: f64,
};

// With C alignment
const CBuffer = extern struct {
    data: [*]u8,
    size: usize,
    capacity: usize,
};

// Packed struct (no padding)
const CFlags = packed struct {
    read: bool,
    write: bool,
    execute: bool,
    _padding: u5 = 0,
};
```

### Using C Structs

```zig
const c = @cImport({
    @cInclude("time.h");
});

pub fn getCurrentTime() i64 {
    var ts: c.timespec = undefined;
    _ = c.clock_gettime(c.CLOCK_REALTIME, &ts);
    return ts.tv_sec;
}

pub fn sleepMilliseconds(ms: u64) void {
    var ts: c.timespec = .{
        .tv_sec = @intCast(ms / 1000),
        .tv_nsec = @intCast((ms % 1000) * 1_000_000),
    };
    _ = c.nanosleep(&ts, null);
}
```

## C Callbacks

### Function Pointers

```zig
const c = @cImport({
    @cInclude("stdlib.h");
});

// Zig function callable from C
export fn compare_fn(a: ?*const anyopaque, b: ?*const anyopaque) callconv(.C) c_int {
    const x: *const i32 = @ptrCast(@alignCast(a.?));
    const y: *const i32 = @ptrCast(@alignCast(b.?));
    return @as(c_int, x.*) - @as(c_int, y.*);
}

pub fn sortArray(arr: []i32) void {
    c.qsort(
        arr.ptr,
        arr.len,
        @sizeOf(i32),
        compare_fn,
    );
}
```

### Thread Callbacks

```zig
const c = @cImport({
    @cInclude("pthread.h");
});

const ThreadContext = struct {
    value: i32,
};

export fn thread_function(arg: ?*anyopaque) callconv(.C) ?*anyopaque {
    const ctx: *ThreadContext = @ptrCast(@alignCast(arg.?));
    std.debug.print("Thread value: {d}\n", .{ctx.value});
    return null;
}

pub fn spawnThread(ctx: *ThreadContext) !void {
    var thread: c.pthread_t = undefined;
    const result = c.pthread_create(&thread, null, thread_function, ctx);
    if (result != 0) return error.ThreadCreateFailed;
    _ = c.pthread_join(thread, null);
}
```

## Exporting Functions to C

### Creating a C Library

```zig
// lib.zig
export fn add(a: i32, b: i32) i32 {
    return a + b;
}

export fn multiply(a: i32, b: i32) i32 {
    return a * b;
}

export fn process_string(str: [*:0]const u8) usize {
    const slice = std.mem.span(str);
    return slice.len;
}

// Complex type export
pub const CResult = extern struct {
    success: bool,
    value: i32,
    error_message: [*:0]const u8,
};

export fn calculate(a: i32, b: i32) CResult {
    if (b == 0) {
        return .{
            .success = false,
            .value = 0,
            .error_message = "Division by zero",
        };
    }
    return .{
        .success = true,
        .value = @divTrunc(a, b),
        .error_message = "",
    };
}
```

### Generating Header File

```zig
// In build.zig
const lib = b.addSharedLibrary(.{
    .name = "mylib",
    .root_module = b.createModule(.{
        .root_source_file = b.path("src/lib.zig"),
        .target = target,
        .optimize = optimize,
    }),
});

// Generate header
const header = b.addInstallFileWithDir(
    lib.getEmittedH(),
    .header,
    "mylib.h",
);
b.getInstallStep().dependOn(&header.step);
```

## Working with C Macros

### Function-Like Macros

```c
// In header.h
#define MAX(a, b) ((a) > (b) ? (a) : (b))
#define BUFFER_SIZE 1024
```

```zig
const c = @cImport({
    @cInclude("header.h");
});

// Access as constants
const buffer: [c.BUFFER_SIZE]u8 = undefined;

// Function-like macros become functions
const result = c.MAX(10, 20);
```

### Conditional Compilation

```c
// In header.h
#ifdef DEBUG
#define LOG(msg) printf("DEBUG: %s\n", msg)
#else
#define LOG(msg)
#endif
```

```zig
const c = @cImport({
    @cDefine("DEBUG", "1");
    @cInclude("header.h");
});

pub fn logMessage(msg: [*:0]const u8) void {
    c.LOG(msg);
}
```

## Variadic Functions

```zig
const c = @cImport({
    @cInclude("stdio.h");
    @cInclude("stdarg.h");
});

// Calling C variadic functions
pub fn printFormatted() void {
    _ = c.printf("Number: %d, String: %s\n", 42, "hello");
}

// Creating Zig variadic function for C
export fn zig_printf(format: [*:0]const u8, ...) callconv(.C) c_int {
    var args: @cVaList = @cVaStart();
    defer @cVaEnd(&args);
    return c.vprintf(format, args);
}
```

## Memory Management Between C and Zig

```zig
const c = @cImport({
    @cInclude("stdlib.h");
});

// Allocate with C, free with C
pub fn useCSlloc() !void {
    const ptr: [*]u8 = @ptrCast(c.malloc(100) orelse return error.OutOfMemory);
    defer c.free(ptr);
    
    // Use ptr
}

// Allocate with Zig, pass to C
pub fn passZigMemoryToC(allocator: std.mem.Allocator) !void {
    const buffer = try allocator.alloc(u8, 100);
    defer allocator.free(buffer);
    
    // C function expecting pointer
    c.process_buffer(@ptrCast(buffer.ptr), buffer.len);
}

// C allocates, Zig owns
pub fn takeOwnershipFromC(allocator: std.mem.Allocator) ![]u8 {
    const c_ptr: [*]u8 = @ptrCast(c.malloc(100) orelse return error.OutOfMemory);
    const c_data = c_ptr[0..100];
    
    // Copy to Zig-managed memory
    const zig_data = try allocator.dupe(u8, c_data);
    c.free(c_ptr);
    
    return zig_data;
}
```

## Common Pitfalls

1. **Null Termination**: C strings must be null-terminated
   ```zig
   // Wrong
   const str: []const u8 = "hello";
   _ = c.printf("%s\n", str.ptr);  // May not be null-terminated!
   
   // Right
   const str: [:0]const u8 = "hello";
   _ = c.printf("%s\n", str.ptr);
   ```

2. **Pointer Alignment**: C pointers may have different alignment
   ```zig
   const ptr: *anyopaque = c.get_pointer();
   const typed: *MyStruct = @ptrCast(@alignCast(ptr));
   ```

3. **Memory Ownership**: Be clear about who owns memory
   ```zig
   // C owns the returned pointer, don't free it
   const c_string = c.get_static_string();
   
   // Zig owns this, must free it
   const zig_string = try allocator.dupe(u8, std.mem.span(c_string));
   defer allocator.free(zig_string);
   ```

4. **Error Values**: C uses special values (null, -1, etc.), Zig uses error unions
   ```zig
   const result = c.some_function();
   if (result < 0) return error.CFunctionFailed;
   ```

## Best Practices

1. **Wrap C APIs**: Create Zig-friendly wrappers
   ```zig
   pub fn openFile(path: []const u8) !std.fs.File {
       const c_path = try std.os.toPosixPath(path);
       const fd = c.open(&c_path, c.O_RDONLY);
       if (fd < 0) return error.OpenFailed;
       return std.fs.File{ .handle = fd };
   }
   ```

2. **Use `extern struct`**: For ABI compatibility
3. **Document Memory Ownership**: Make it clear in comments
4. **Minimize C Surface Area**: Keep C code isolated
5. **Prefer Zig Standard Library**: When possible, use Zig's cross-platform APIs
