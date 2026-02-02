# Crash Patterns Reference

## Memory Corruption

### Null Pointer Dereference
**Indicators**:
- SIGSEGV / Access Violation
- Fault address is 0x0 or small offset (0x8, 0x10)
- Stack shows pointer variable usage
- Recent pointer assignment or return value

**Root Causes**:
- Uninitialized pointer
- Failed allocation not checked (`malloc` returned NULL)
- Pointer cleared/freed then used
- Function returned NULL, caller didn't check

**Distinguishing Questions**:
- Was pointer ever assigned?
- Was allocation checked?
- Did function return NULL?
- Race condition (sometimes null)?

### Use After Free
**Indicators**:
- SIGSEGV with heap address
- Address was previously valid
- Memory shows freed pattern (0xdeadbeef, 0xfeeefeee)
- Crash location differs from bug location

**Root Causes**:
- Explicit free then use
- Double free
- Return of stack/local variable
- Object lifecycle error (destructor then use)

**Distinguishing Questions**:
- When was memory freed?
- What's the object lifecycle?
- Is there a dangling pointer?
- Heap state analysis?

### Buffer Overflow
**Indicators**:
- Stack smashing / canary failure
- Return address overwritten
- Adjacent memory corrupted
- Crash after array/buffer operation

**Root Causes**:
- Unbounded copy (`strcpy`, `sprintf`, `gets`)
- Off-by-one in loop bounds
- Integer overflow affecting buffer size
- Missing bounds check

**Distinguishing Questions**:
- What buffer was written?
- Intended size vs actual?
- Source of size value?
- Integer arithmetic involved?

### Heap Corruption
**Indicators**:
- Crash in malloc/free/new/delete
- Heap metadata corruption
- glibc: "corrupted double-linked list"
- Crash location varies

**Root Causes**:
- Heap buffer overflow
- Use after free
- Double free
- Uninitialized heap memory

---

## Threading Issues

### Race Condition
**Indicators**:
- Intermittent crash (non-deterministic)
- State inconsistency
- Works single-threaded, fails multi-threaded
- Timing-dependent failure

**Root Causes**:
- Missing lock
- Lock ordering violation
- Need atomic operation
- TOCTOU (time-of-check vs time-of-use)

**Distinguishing Questions**:
- Multiple threads accessing same data?
- Locking discipline followed?
- Reproducible with sleep() injection?
- Thread sanitizer output?

### Deadlock
**Indicators**:
- Application hangs (not crash)
- Multiple threads waiting
- Locks held in cross order
- No progress, CPU idle

**Root Causes**:
- Lock order inversion (A→B, B→A)
- Self-deadlock (non-recursive lock)
- Resource starvation
- Signal handler lock acquisition

**Distinguishing Questions**:
- What locks are held?
- What locks are waited for?
- Expected lock order?
- Thread stack traces?

### Data Race
**Indicators**:
- Intermittent wrong results
- Memory corruption symptoms
- Thread sanitizer errors
- Unpredictable state

**Root Causes**:
- Concurrent read/write without sync
- Partial writes visible
- Compiler reordering
- CPU memory ordering

---

## Resource Exhaustion

### Memory Exhaustion (OOM)
**Indicators**:
- `malloc`/`new` returns NULL
- OOM killer invoked
- Memory growing over time
- Crash after prolonged runtime

**Root Causes**:
- Memory leak (allocate, never free)
- Unbounded growth (cache, queue, buffer)
- Single large allocation
- Memory fragmentation

**Distinguishing Questions**:
- Memory usage over time?
- What objects accumulating?
- Leak detected (valgrind, ASAN)?
- What triggered final failure?

### File Descriptor Exhaustion
**Indicators**:
- "Too many open files"
- Socket/file operations fail
- ulimit reached
- FD count growing

**Root Causes**:
- FD leak (open, never close)
- Connection pool failure
- Unbounded connection acceptance
- Fork without FD management

**Distinguishing Questions**:
- FD count over time?
- What's in `/proc/pid/fd`?
- Resources closed in error paths?
- Exception handling cleanup?

### Thread Exhaustion
**Indicators**:
- Thread creation fails
- "Resource temporarily unavailable"
- Thread count growing
- Stack space exhausted

**Root Causes**:
- Thread leak (create, never join)
- Thread pool not bounded
- Recursive thread creation
- Stack size too large

---

## Logic Errors

### State Machine Error
**Indicators**:
- "Invalid state" assertion
- Operation in wrong state
- Inconsistent object state
- State transition error

**Root Causes**:
- Missing state transition
- Wrong state check
- Concurrent state modification
- State corruption

**Distinguishing Questions**:
- Expected state vs found?
- What caused state change?
- State machine logic correct?
- Race on state variable?

### Integer Overflow/Underflow
**Indicators**:
- Unexpectedly large/small value
- Negative where positive expected
- Huge allocation size
- Loop runs wrong iterations

**Root Causes**:
- Arithmetic overflow
- Sign confusion (signed/unsigned)
- Truncation (64→32 bit)
- Unchecked arithmetic

**Distinguishing Questions**:
- What arithmetic produced value?
- Types involved?
- Input value ranges?
- Overflow checks present?

### Assertion Failure
**Indicators**:
- `assert()` triggered
- Precondition violated
- Invariant broken
- SIGABRT

**Root Causes**:
- Caller violated contract
- Implementation bug
- Corrupted state
- Missing error handling

---

## External/Input Issues

### Invalid Input
**Indicators**:
- Crash on specific input
- Format parsing failure
- Unexpected input values
- Malformed data handling

**Root Causes**:
- Missing input validation
- Parser bug
- Type confusion
- Encoding issues

### Dependency Failure
**Indicators**:
- Crash after external call
- Network/IPC error handling
- Missing dependency
- Version mismatch

**Root Causes**:
- Unhandled error return
- Timeout not handled
- Dependency unavailable
- API change

### Environment Issue
**Indicators**:
- Works in dev, fails in prod
- Configuration dependent
- OS/library version dependent
- Resource limit related

**Root Causes**:
- Missing environment variable
- Different library version
- Resource limits different
- Permissions different

---

## Quick Diagnosis Guide

| Symptom | First Check | Likely Pattern |
|---------|-------------|----------------|
| SIGSEGV at 0x0 | Pointer initialization | Null deref |
| SIGSEGV at heap addr | Free/use timeline | Use-after-free |
| "stack smashing" | Buffer operations | Buffer overflow |
| Intermittent crash | Threading | Race condition |
| Hang, CPU idle | Lock state | Deadlock |
| "Out of memory" | Memory growth | Leak/exhaustion |
| "Invalid state" | State transitions | State machine |
| Huge allocation | Size arithmetic | Integer overflow |
| Crash in malloc/free | Heap operations | Heap corruption |

---

## Analysis Artifacts

### Stack Trace Analysis
```
#0  0x... in crash_function() at file.c:123     ← Crash location
#1  0x... in caller_function() at file.c:456    ← Call chain
#2  0x... in main() at main.c:789               ← Entry point
```

**Key questions**:
- Is crash location the bug location? (Often not for corruption)
- What arguments were passed?
- What's the call chain context?

### Memory State
| Pattern | Meaning |
|---------|---------|
| 0x0 | Null pointer |
| 0xcdcdcdcd | MSVC uninitialized heap |
| 0xcccccccc | MSVC uninitialized stack |
| 0xdddddddd | MSVC freed heap |
| 0xfeeefeee | MSVC freed heap (HeapFree) |
| 0xdeadbeef | Common freed/poison pattern |
| 0xbaadf00d | MSVC LocalAlloc uninitialized |

### Core Dump Checklist
- [ ] Get stack trace (all threads)
- [ ] Check register values
- [ ] Examine memory at fault address
- [ ] Check heap state
- [ ] Review nearby memory
- [ ] Check thread states
