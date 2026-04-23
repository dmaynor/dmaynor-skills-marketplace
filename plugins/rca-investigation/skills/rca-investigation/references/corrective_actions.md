# Corrective Action Validation Reference

## The Five Tests

Every corrective action must pass all five:

### 1. Layer Match Test
> Does this action target the same layer as the identified root cause?

| Root Cause Layer | Good Action | Bad Action |
|-----------------|-------------|-----------|
| L1 (API outage) | Add retry with backoff | Stop using the API |
| L2 (Disk full) | Add disk monitoring | Rewrite the application |
| L3 (Wrong config) | Fix the config, add validation | Redesign the system |
| L4 (Bad tool choice) | Choose better tool | Abandon all automation |
| L5 (Code bug) | Fix the bug, add test | "Be more careful" |
| L6 (Bad priority) | Add priority framework | "Try harder" |

### 2. Proportionality Test
> Is the cost/disruption of this fix proportional to the impact of the failure?

Red flags:
- Banning an entire approach after a single failure
- Adding a new system/process to prevent a rare event
- Requiring approval for something that worked 99 times out of 100
- Refactoring a codebase because of one bug

Green flags:
- Adding a check that catches the specific failure mode
- Documenting a non-obvious diagnostic step
- Adjusting a parameter (timeout, retry count, threshold)

### 3. Side Effect Test
> Does this fix break something that was working?

Check:
- Does it slow down the success path?
- Does it add cognitive overhead to future work?
- Does it prevent approaches that worked fine in other contexts?
- Does it create new failure modes?

### 4. Verifiability Test
> Can you prove this fix would have prevented the original failure?

Methods:
- Replay: Re-run the scenario with the fix in place
- Logic: Trace the causal chain and show the fix interrupts it
- Negative: Show the failure mechanism still exists without the fix

If you can't verify → the fix is speculative, not evidence-based.

### 5. Overcorrection Test
> Would you propose this change if the failure hadn't happened?

If yes → It's a genuine improvement you discovered through the failure.
If no → You're reacting emotionally to the failure, not reasoning about it.

## Action Categories

### Prevent (stop it from happening)
- Fix the root cause directly
- Add validation/guard at the root cause layer
- Remove the precondition that enables the failure

### Detect (catch it faster)
- Add monitoring at the failure layer
- Add alerting for leading indicators
- Add diagnostic output for faster triage

### Recover (reduce impact when it happens)
- Add retry/fallback logic
- Add checkpoint/resume capability
- Reduce blast radius (isolation, circuit breakers)

### Accept (consciously decide not to fix)
- Failure is rare and low-impact
- Fix cost exceeds failure cost
- Fix introduces worse risks
- Document the known risk and move on

## Common Overcorrections

| Failure | Overcorrection | Right-Sized Fix |
|---------|---------------|-----------------|
| Agent timed out once | "Never use agents for X" | Add retry, check status page |
| Script had a bug | "Rewrite the script" | Fix the bug |
| Missed a priority | "Add a priority framework" | Check priorities each iteration |
| Tool gave wrong output | "Don't use that tool" | Fix the prompt or input |
| Process took too long | "Redesign the process" | Identify the bottleneck |
