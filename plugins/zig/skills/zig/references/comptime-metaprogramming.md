# Comptime & Metaprogramming in Zig

Zig's compile-time evaluation (`comptime`) replaces traditional macros, templates, and generics.

## Generic Functions

```zig
fn max(comptime T: type, a: T, b: T) T {
    return if (a > b) a else b;
}

const result1 = max(i32, 10, 20);     // T is i32
const result2 = max(f64, 3.14, 2.71); // T is f64

// Type inference
fn min(comptime T: type, a: T, b: T) T {
    return if (a < b) a else b;
}

const val = min(u32, 5, 10); // Explicit
```

## Generic Data Structures

### Generic List

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

        pub fn deinit(self: *Self) void {
            if (self.capacity > 0) {
                self.allocator.free(self.items.ptr[0..self.capacity]);
            }
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
            const new_memory = try self.allocator.alloc(T, new_cap);
            if (self.capacity > 0) {
                @memcpy(new_memory[0..self.items.len], self.items);
                self.allocator.free(self.items.ptr[0..self.capacity]);
            }
            self.items.ptr = new_memory.ptr;
            self.capacity = new_cap;
        }
    };
}

// Usage
var list = ArrayList(u32).init(allocator);
defer list.deinit();
try list.append(42);
```

### Generic HashMap

```zig
fn HashMap(comptime K: type, comptime V: type) type {
    return struct {
        const Self = @This();
        const Entry = struct {
            key: K,
            value: V,
            hash: u64,
            used: bool,
        };

        entries: []Entry,
        count: usize,
        allocator: Allocator,

        pub fn init(allocator: Allocator, capacity: usize) !Self {
            const entries = try allocator.alloc(Entry, capacity);
            @memset(entries, .{ .key = undefined, .value = undefined, .hash = 0, .used = false });
            return Self{
                .entries = entries,
                .count = 0,
                .allocator = allocator,
            };
        }

        pub fn deinit(self: *Self) void {
            self.allocator.free(self.entries);
        }

        pub fn put(self: *Self, key: K, value: V) !void {
            const hash = self.hash(key);
            var idx = hash % self.entries.len;
            
            while (self.entries[idx].used) {
                if (self.entries[idx].hash == hash and 
                    std.meta.eql(self.entries[idx].key, key)) {
                    self.entries[idx].value = value;
                    return;
                }
                idx = (idx + 1) % self.entries.len;
            }
            
            self.entries[idx] = .{
                .key = key,
                .value = value,
                .hash = hash,
                .used = true,
            };
            self.count += 1;
        }

        fn hash(self: Self, key: K) u64 {
            _ = self;
            var hasher = std.hash.Wyhash.init(0);
            std.hash.autoHash(&hasher, key);
            return hasher.final();
        }
    };
}
```

## anytype Parameter

Accepts any type, with type checking at compile time:

```zig
fn debugPrint(value: anytype) void {
    const T = @TypeOf(value);
    const info = @typeInfo(T);
    
    switch (info) {
        .pointer => std.debug.print("pointer to {s}\n", .{@typeName(std.meta.Child(T))}),
        .int => std.debug.print("integer: {d}\n", .{value}),
        .float => std.debug.print("float: {d}\n", .{value}),
        .@"struct" => std.debug.print("struct: {s}\n", .{@typeName(T)}),
        else => std.debug.print("{any}\n", .{value}),
    }
}

debugPrint(42);        // integer: 42
debugPrint(3.14);      // float: 3.14
debugPrint("hello");   // pointer to u8
```

## Compile-Time Computation

### Compile-Time Constants

```zig
fn fibonacci(comptime n: u32) u32 {
    if (n < 2) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

const fib_10 = comptime fibonacci(10);  // Computed at compile time: 55
const fib_20 = fibonacci(20);           // Also comptime if used as comptime value

// Array sized by comptime calculation
const buffer: [fibonacci(10)]u8 = undefined;  // Array of 55 elements
```

### Compile-Time String Operations

```zig
fn typeName(comptime T: type) []const u8 {
    return @typeName(T);
}

const name = typeName(i32);  // "i32"

// Concatenation
fn concat(comptime a: []const u8, comptime b: []const u8) []const u8 {
    return a ++ b;
}

const greeting = comptime concat("Hello, ", "World!");
```

### Compile-Time Assertions

```zig
fn validateConfig(comptime config: struct {
    max_size: usize,
    max_connections: u32,
}) void {
    if (config.max_size > 1024 * 1024) {
        @compileError("max_size too large (> 1MB)");
    }
    if (config.max_connections == 0) {
        @compileError("max_connections must be greater than 0");
    }
}

const Config = struct {
    max_size: usize = 1024,
    max_connections: u32 = 100,
};

comptime validateConfig(Config{});  // Validates at compile time
```

## Type Reflection

### Struct Field Iteration

```zig
fn printFields(comptime T: type) void {
    const info = @typeInfo(T);
    
    switch (info) {
        .@"struct" => |s| {
            std.debug.print("Struct {s} has {} fields:\n", .{ @typeName(T), s.fields.len });
            inline for (s.fields) |field| {
                std.debug.print("  - {s}: {s}", .{
                    field.name,
                    @typeName(field.type),
                });
                if (field.default_value) |default| {
                    std.debug.print(" = {any}", .{default});
                }
                std.debug.print("\n", .{});
            }
        },
        else => @compileError("Expected struct type"),
    }
}

const Point = struct {
    x: f32,
    y: f32 = 0.0,
};

comptime printFields(Point);
```

### Generic Serialization

```zig
fn serialize(writer: anytype, value: anytype) !void {
    const T = @TypeOf(value);
    const info = @typeInfo(T);
    
    switch (info) {
        .int, .float => try writer.print("{d}", .{value}),
        .bool => try writer.print("{}", .{value}),
        .pointer => |ptr| {
            if (ptr.size == .Slice) {
                if (ptr.child == u8) {
                    try writer.print("\"{s}\"", .{value});
                } else {
                    try writer.print("[", .{});
                    for (value, 0..) |item, i| {
                        if (i > 0) try writer.print(",", .{});
                        try serialize(writer, item);
                    }
                    try writer.print("]", .{});
                }
            }
        },
        .@"struct" => |s| {
            try writer.print("{{", .{});
            inline for (s.fields, 0..) |field, i| {
                if (i > 0) try writer.print(",", .{});
                try writer.print("\"{s}\":", .{field.name});
                try serialize(writer, @field(value, field.name));
            }
            try writer.print("}}", .{});
        },
        else => @compileError("Unsupported type: " ++ @typeName(T)),
    }
}
```

### Enum Utilities

```zig
fn enumValues(comptime E: type) []const E {
    const info = @typeInfo(E);
    if (info != .@"enum") @compileError("Expected enum type");
    
    const fields = info.@"enum".fields;
    comptime var values: [fields.len]E = undefined;
    inline for (fields, 0..) |field, i| {
        values[i] = @enumFromInt(field.value);
    }
    return &values;
}

fn enumFromString(comptime E: type, str: []const u8) ?E {
    inline for (enumValues(E)) |value| {
        if (std.mem.eql(u8, @tagName(value), str)) {
            return value;
        }
    }
    return null;
}

const Color = enum { red, green, blue };

const all_colors = comptime enumValues(Color);  // [.red, .green, .blue]
const color = enumFromString(Color, "green");   // .green
```

## Mixin Pattern

```zig
fn Comparable(comptime T: type) type {
    return struct {
        pub fn lessThan(a: T, b: T) bool {
            return a.compare(b) < 0;
        }

        pub fn greaterThan(a: T, b: T) bool {
            return a.compare(b) > 0;
        }

        pub fn equals(a: T, b: T) bool {
            return a.compare(b) == 0;
        }
    };
}

const Person = struct {
    name: []const u8,
    age: u32,

    pub fn compare(self: Person, other: Person) i32 {
        return @as(i32, self.age) - @as(i32, other.age);
    }

    pub usingnamespace Comparable(@This());
};

// Usage
const p1 = Person{ .name = "Alice", .age = 30 };
const p2 = Person{ .name = "Bob", .age = 25 };
const is_less = Person.lessThan(p1, p2);  // false
```

## Inline Loops

Process collections at compile time:

```zig
fn processTypes(comptime types: []const type) void {
    inline for (types) |T| {
        std.debug.print("Type: {s}, size: {d}\n", .{
            @typeName(T),
            @sizeOf(T),
        });
    }
}

comptime {
    processTypes(&.{ i32, f64, bool, []const u8 });
}
```

## Compile-Time Code Generation

```zig
fn generateGetters(comptime T: type) type {
    const info = @typeInfo(T).@"struct";
    
    return struct {
        pub usingnamespace T;

        // Generate getter for each field
        comptime {
            for (info.fields) |field| {
                const getter_name = "get" ++ capitalize(field.name);
                @compileLog("Generating:", getter_name);
            }
        }
    };
}

fn capitalize(comptime str: []const u8) []const u8 {
    var result: [str.len]u8 = undefined;
    @memcpy(&result, str);
    if (result.len > 0) {
        result[0] = std.ascii.toUpper(result[0]);
    }
    return &result;
}
```

## Best Practices

1. **Use `comptime` parameters for types**: `comptime T: type`
2. **Use `inline for` for compile-time iteration**: Unrolls loops
3. **Prefer compile-time errors**: `@compileError()` over runtime panics
4. **Keep comptime functions simple**: Complex logic can slow compilation
5. **Use `@typeInfo()` for reflection**: Inspect types at compile time
6. **Document generic constraints**: Make expectations clear

## Common Patterns

### Type-Safe Builder

```zig
fn Builder(comptime T: type) type {
    return struct {
        const Self = @This();
        data: T,

        pub fn init() Self {
            return .{ .data = std.mem.zeroes(T) };
        }

        pub fn set(self: *Self, comptime field: []const u8, value: anytype) *Self {
            @field(self.data, field) = value;
            return self;
        }

        pub fn build(self: Self) T {
            return self.data;
        }
    };
}

// Usage
const Config = struct { port: u16, host: []const u8 };
var builder = Builder(Config).init();
const config = builder.set("port", 8080).set("host", "localhost").build();
```

### Type-Safe Event System

```zig
fn EventHandler(comptime EventType: type) type {
    return struct {
        const Self = @This();
        const HandlerFn = *const fn (EventType) void;

        handlers: std.ArrayList(HandlerFn),

        pub fn init(allocator: Allocator) Self {
            return .{
                .handlers = std.ArrayList(HandlerFn).init(allocator),
            };
        }

        pub fn subscribe(self: *Self, handler: HandlerFn) !void {
            try self.handlers.append(handler);
        }

        pub fn emit(self: Self, event: EventType) void {
            for (self.handlers.items) |handler| {
                handler(event);
            }
        }
    };
}
```
