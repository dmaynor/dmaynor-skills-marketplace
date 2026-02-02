# Zig Types, Patterns, and Standard Library Reference

## Types

### Primitives

```zig
const a: i32 = -42;           // Signed integers: i8, i16, i32, i64, i128
const b: u64 = 42;            // Unsigned: u8, u16, u32, u64, u128
const c: f32 = 3.14;          // Floats: f16, f32, f64, f128
const d: bool = true;
const e: usize = @sizeOf(u64); // Platform-dependent size
const f: comptime_int = 100;   // Arbitrary precision at comptime
```

### Optionals

```zig
var maybe: ?i32 = null;
maybe = 42;

if (maybe) |value| {
    // value is i32, unwrapped
}

const val = maybe orelse 0;           // Default value
const val2 = maybe orelse return;     // Early return
const val3 = maybe.?;                 // Assert non-null (panic if null)
```

### Error Unions

```zig
const FileError = error{ NotFound, PermissionDenied };

fn openFile(path: []const u8) FileError!std.fs.File {
    return error.NotFound;
}

const file = openFile("test.txt") catch |err| {
    std.debug.print("Error: {}\n", .{err});
    return err;
};

const file2 = try openFile("test.txt");
```

### Error Sets

```zig
const ReadError = error{ EndOfStream, Timeout };
const WriteError = error{ BrokenPipe, DiskFull };
const IoError = ReadError || WriteError;  // Merge error sets

// Inferred error set with !
fn process() !void {
    try read();
    try write();
}
```

### Slices and Arrays

```zig
const array: [5]u8 = .{ 1, 2, 3, 4, 5 };  // Fixed-size array
const slice: []const u8 = array[1..4];     // Slice (pointer + length)
const str: []const u8 = "hello";           // String literal is []const u8
const c_str: [*:0]const u8 = "hello";      // Null-terminated for C interop
```

### Structs

```zig
const Point = struct {
    x: f32,
    y: f32 = 0.0,  // Default value

    const Self = @This();

    pub fn init(x: f32, y: f32) Self {
        return .{ .x = x, .y = y };
    }

    pub fn distance(self: Self, other: Self) f32 {
        const dx = self.x - other.x;
        const dy = self.y - other.y;
        return @sqrt(dx * dx + dy * dy);
    }
};

const p = Point.init(3.0, 4.0);
const p2 = Point{ .x = 0.0 };  // y defaults to 0.0
```

### Enums and Tagged Unions

```zig
const Color = enum { red, green, blue };

const Value = union(enum) {
    int: i32,
    float: f64,
    none,

    pub fn format(self: Value) []const u8 {
        return switch (self) {
            .int => "integer",
            .float => "float",
            .none => "none",
        };
    }
};

var v: Value = .{ .int = 42 };
switch (v) {
    .int => |n| std.debug.print("{d}\n", .{n}),
    .float => |f| std.debug.print("{d}\n", .{f}),
    .none => {},
}
```

## Memory Management Details

### Allocator Pattern

```zig
const std = @import("std");
const Allocator = std.mem.Allocator;

fn createBuffer(allocator: Allocator, size: usize) ![]u8 {
    return try allocator.alloc(u8, size);
}

pub fn main() !void {
    var gpa: std.heap.GeneralPurposeAllocator(.{}) = .{};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const buffer = try createBuffer(allocator, 100);
    defer allocator.free(buffer);

    // Arena allocator (bulk free)
    var arena: std.heap.ArenaAllocator = .init(allocator);
    defer arena.deinit();
    const arena_alloc = arena.allocator();
    _ = arena_alloc;
}
```

### Common Allocators

```zig
std.heap.page_allocator         // Direct OS pages
std.heap.c_allocator            // libc malloc/free
std.heap.GeneralPurposeAllocator(.{})  // Debug-friendly
std.heap.ArenaAllocator         // Bulk allocation/deallocation
std.heap.FixedBufferAllocator   // Stack-based, no heap
std.testing.allocator           // For tests (detects leaks)
```

## Comptime Details

### Generic Data Structures

```zig
fn ArrayList(comptime T: type) type {
    return struct {
        items: []T,
        capacity: usize,
        allocator: Allocator,

        const Self = @This();

        pub fn init(allocator: Allocator) Self {
            return .{
                .items = &.{},
                .capacity = 0,
                .allocator = allocator,
            };
        }

        pub fn append(self: *Self, item: T) !void {
            if (self.items.len >= self.capacity) {
                try self.grow();
            }
            self.items.len += 1;
            self.items[self.items.len - 1] = item;
        }

        fn grow(self: *Self) !void {
            const new_cap = if (self.capacity == 0) 8 else self.capacity * 2;
            self.items = try self.allocator.realloc(self.items, new_cap);
            self.capacity = new_cap;
        }

        pub fn deinit(self: *Self) void {
            self.allocator.free(self.items.ptr[0..self.capacity]);
        }
    };
}
```

### anytype Parameter

```zig
fn debugPrint(value: anytype) void {
    const T = @TypeOf(value);
    if (@typeInfo(T) == .pointer) {
        std.debug.print("pointer to {}\n", .{@typeName(std.meta.Child(T))});
    } else {
        std.debug.print("{any}\n", .{value});
    }
}
```

### Compile-Time Computation

```zig
fn fibonacci(comptime n: u32) u32 {
    if (n < 2) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

const fib_10 = comptime fibonacci(10);  // Computed at compile time
```

### Type Reflection

```zig
fn printFields(comptime T: type) void {
    const info = @typeInfo(T);
    switch (info) {
        .@"struct" => |s| {
            inline for (s.fields) |field| {
                std.debug.print("field: {s}, type: {s}\n", .{
                    field.name,
                    @typeName(field.type),
                });
            }
        },
        else => @compileError("Expected struct type"),
    }
}
```

## Common Patterns

### Iterator Pattern

```zig
fn tokenize(input: []const u8, delimiter: u8) TokenIterator {
    return .{ .buffer = input, .delimiter = delimiter, .index = 0 };
}

const TokenIterator = struct {
    buffer: []const u8,
    delimiter: u8,
    index: usize,

    pub fn next(self: *TokenIterator) ?[]const u8 {
        if (self.index >= self.buffer.len) return null;

        const start = self.index;
        while (self.index < self.buffer.len and
               self.buffer[self.index] != self.delimiter) {
            self.index += 1;
        }

        const result = self.buffer[start..self.index];
        if (self.index < self.buffer.len) self.index += 1;
        return result;
    }
};

// Usage
var iter = tokenize("a,b,c", ',');
while (iter.next()) |token| {
    std.debug.print("{s}\n", .{token});
}
```

### Builder Pattern

```zig
const RequestBuilder = struct {
    method: []const u8 = "GET",
    path: []const u8 = "/",
    headers: std.StringHashMap([]const u8),

    pub fn init(allocator: Allocator) RequestBuilder {
        return .{ .headers = std.StringHashMap([]const u8).init(allocator) };
    }

    pub fn setMethod(self: *RequestBuilder, method: []const u8) *RequestBuilder {
        self.method = method;
        return self;
    }

    pub fn setPath(self: *RequestBuilder, path: []const u8) *RequestBuilder {
        self.path = path;
        return self;
    }

    pub fn addHeader(self: *RequestBuilder, key: []const u8, value: []const u8) !*RequestBuilder {
        try self.headers.put(key, value);
        return self;
    }
};
```

### State Machine

```zig
const State = enum { idle, running, paused, stopped };

const Machine = struct {
    state: State = .idle,

    pub fn start(self: *Machine) !void {
        switch (self.state) {
            .idle, .paused => self.state = .running,
            .running => return error.AlreadyRunning,
            .stopped => return error.CannotRestart,
        }
    }

    pub fn pause(self: *Machine) !void {
        if (self.state != .running) return error.NotRunning;
        self.state = .paused;
    }
};
```

## Standard Library Highlights

```zig
// ArrayList
var list = std.ArrayList(u8).init(allocator);
defer list.deinit();
try list.append(42);
try list.appendSlice("hello");

// HashMap
var map = std.StringHashMap(i32).init(allocator);
defer map.deinit();
try map.put("key", 42);
const val = map.get("key");

// File I/O
const file = try std.fs.cwd().openFile("test.txt", .{});
defer file.close();
const content = try file.readToEndAlloc(allocator, 1024 * 1024);
defer allocator.free(content);

// JSON
const parsed = try std.json.parseFromSlice(MyStruct, allocator, json_str, .{});
defer parsed.deinit();

// Formatting
const str = try std.fmt.allocPrint(allocator, "Value: {d}", .{42});
defer allocator.free(str);

// Threads
const thread = try std.Thread.spawn(.{}, workerFn, .{arg});
thread.join();
```

## Testing Extended

```zig
const std = @import("std");
const expect = std.testing.expect;
const expectEqual = std.testing.expectEqual;
const expectError = std.testing.expectError;

test "basic arithmetic" {
    const result = 2 + 2;
    try expectEqual(@as(i32, 4), result);
}

test "memory allocation" {
    const allocator = std.testing.allocator;
    const buffer = try allocator.alloc(u8, 10);
    defer allocator.free(buffer);
    try expect(buffer.len == 10);
}

test "expected error" {
    const result = failingFunction();
    try expectError(error.SomeError, result);
}

test "skip test" {
    if (builtin.os.tag == .windows) {
        return error.SkipZigTest;
    }
}
```
