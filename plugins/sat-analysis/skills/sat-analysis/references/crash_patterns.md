# Crash, hang, and resource-failure analysis

Establish the exact failure type, binary/build, relevant environment, inputs, and
available capture. Separate the instruction or subsystem detecting the fault from
the earlier state transition that made it possible. A trace alone may establish
the failure site without establishing the root cause.

| Observation | Mechanisms to consider | Discriminating evidence and limits |
|---|---|---|
| Access fault at a low address | Null-derived access, corrupted pointer, invalid mapping or permissions | Inspect the faulting instruction, registers, access type, and mapping. The address alone does not identify pointer provenance. |
| Access fault in heap storage | Stale reference, out-of-bounds access, corrupted pointer, concurrency, inaccessible mapping | Link allocation, lifetime, and access histories. A heap address alone does not establish use-after-free. |
| Allocator or canary reports corruption | Earlier invalid write, lifetime error, stack damage | Identify which invariant was detected and when it could first have been violated. Detection location is often downstream. |
| Intermittent failure affected by scheduling | Shared-state race, lifetime issue, timeout, external dependency, nondeterministic input | Identify competing accesses and synchronization, instrument the relevant state transition, and compare controlled runs. Timing sensitivity alone does not prove a race. |
| Hang with waiting threads | Lock cycle, external wait, starvation, missed wakeup, intentional wait | Inspect all relevant waits, ownership and progress over time. Idle CPU does not prove deadlock; starvation and deadlock differ. |
| Allocation failure or process termination | Limit reached, memory pressure, fragmentation, retained data, leak, oversized request | Use exact runtime failure semantics, process/cgroup limits, allocator results, and termination evidence. Memory growth alone does not establish a leak. |
| File/socket operation fails with exhaustion | Per-process or system limit, leak, bounded peak demand, unavailable external resource | Inspect the actual error and resource lifecycle. Count and classify the resource under the applicable limit. |
| Unexpected size, index, or state assertion | Arithmetic error, conversion, contract violation, earlier corruption, concurrency | Trace operand ranges and types or the state transition; verify language and build semantics before classifying. |
| Failure after a dependency call | Invalid return handling, API mismatch, unavailable dependency, unrelated earlier damage | Link the return/result to the failing path. Temporal adjacency alone does not establish causation. |

## Respect implementation semantics

- Match source and debug symbols to the actual executable. Optimized code,
  inlining, missing symbols, and corrupted unwind data limit a stack's precision.
- Identify the allocator, runtime, and diagnostic mode before interpreting memory
  fill patterns. Repeated hex values are not universal evidence of allocation state.
- Keep C allocation failure, ordinary throwing C++ allocation, explicit nothrow
  allocation, runtime-managed exceptions, and operating-system termination distinct.
  Verify the relevant platform behavior rather than treating all failures as null.
- Distinguish a race condition in a multi-step operation from a language-defined
  data race. Concurrency failures do not all have the same synchronization remedy.
- Treat a returned reference to expired stack storage as a lifetime issue; do not
  mislabel every dangling reference as freed heap memory.
- Verify signedness, width, conversion, overflow behavior, and zero cases before
  recommending arithmetic checks. An unsigned type alone does not prevent overflow.

## Design a useful reproduction or check

Preserve the observed build/input/environment before varying a suspected cause.
Specify the expected difference under the main competing explanations and the
time or input coverage needed for a meaningful negative result. Instrumentation
can change timing, memory layout, and workload; record those changes.

Sanitizer findings can establish specific violations in the exercised execution;
a clean run does not establish absence outside supported instrumentation and paths.
One successful rerun does not eliminate an intermittent problem. Avoid a sequence
of simultaneous changes that makes recovery causally uninterpretable.

When choosing mitigation, separate reduced impact from confirmed repair. State the
workload and duration covered, the burden of monitoring or restarting, and an
early trigger to change course. If containment interrupts evidence collection,
explain that tradeoff when it matters to the pending decision.
