# Fix Verification Patterns Reference

## Fix Effectiveness Categories

### Complete Fix
**Definition**: Addresses root cause, all attack vectors/failure modes closed

**Indicators**:
- Fix targets root cause, not symptoms
- All code paths to vulnerability addressed
- Edge cases considered
- Regression tests added

### Partial Fix  
**Definition**: Addresses some vectors but not all

**Indicators**:
- Some attack paths remain
- Edge cases not covered
- Works for common case, fails edge cases
- Missing validation in some paths

### Symptom Fix
**Definition**: Masks symptoms, root cause remains

**Indicators**:
- Error suppressed rather than handled
- Exception caught and ignored
- Condition checked after damage possible
- Workaround rather than fix

### Ineffective Fix
**Definition**: Does not address the issue

**Indicators**:
- Wrong variable/location modified
- Logic error in fix itself
- Fix never executes (dead code)
- Misunderstanding of root cause

### Regression Risk
**Definition**: May introduce new issues

**Indicators**:
- Behavioral change beyond fix scope
- Performance impact
- New code paths untested
- Dependency changes

### Bypass Possible
**Definition**: Fix can be circumvented

**Indicators**:
- Validation on client only
- Check can be skipped
- Alternative paths exist
- Encoding/format variations not covered

---

## Common Fix Failure Patterns

### Wrong Layer Fix
**Problem**: Fix applied at wrong abstraction level

**Example**:
```
BUG: SQL injection in web form
WRONG: Escape quotes in JavaScript (client-side)
RIGHT: Parameterized queries in database layer
```

**Detection**: Ask "Can this check be bypassed?"

### Incomplete Coverage
**Problem**: Fix covers main path but not all entry points

**Example**:
```
BUG: Path traversal in file upload
WRONG: Check only POST /upload endpoint
RIGHT: Check all file path inputs system-wide
```

**Detection**: Enumerate all paths to vulnerable code

### Type Confusion Persistence
**Problem**: Fix checks type but doesn't prevent confusion

**Example**:
```
BUG: Integer overflow in size calculation
WRONG: if (size > MAX) return error;
RIGHT: Use size_t, check before arithmetic
```

**Detection**: Trace data types through full flow

### Race Condition Window
**Problem**: Fix creates or doesn't close race window

**Example**:
```
BUG: TOCTOU in file access
WRONG: Check permissions, then open file
RIGHT: Open file, then check permissions on handle
```

**Detection**: Identify check-use gap

### Integer Issue Persistence
**Problem**: Integer overflow/underflow not fully addressed

**Example**:
```
BUG: Integer overflow in buffer allocation
WRONG: if (n * size > MAX) error;  // overflow in check!
RIGHT: if (n > MAX / size) error;  // safe check
```

**Detection**: Analyze all arithmetic operations

### Encoding Bypass
**Problem**: Validation bypassed via encoding

**Common bypasses**:
- URL encoding (%2e%2e = ..)
- Double encoding (%252e = %2e after decode)
- Unicode normalization
- Null byte injection
- Case variation

**Detection**: Test with encoded variants

### Logic Error in Fix
**Problem**: Fix logic itself is flawed

**Example**:
```
BUG: Off-by-one in loop
WRONG: for (i = 0; i <= n; i++)  // still off-by-one
RIGHT: for (i = 0; i < n; i++)
```

**Detection**: Trace fix logic carefully

### Configuration Dependency
**Problem**: Fix depends on configuration that may change

**Example**:
```
BUG: Insecure default setting
WRONG: Document that admin should change setting
RIGHT: Secure default, require explicit insecure opt-in
```

**Detection**: Check if fix survives config changes

### Version/Dependency Gap
**Problem**: Fix depends on specific version behavior

**Example**:
```
BUG: Library vulnerability
WRONG: Upgrade library (may break compatibility)
RIGHT: Upgrade + verify behavior + test
```

**Detection**: Check dependency assumptions

### Regression Introduction
**Problem**: Fix breaks existing functionality

**Types**:
- Behavioral regression (different output)
- Performance regression (slower)
- Compatibility regression (breaks clients)
- Security regression (new vulnerability)

**Detection**: Review scope of changes vs. tests

---

## Fix Verification Checklist

### Causal Chain Analysis
- [ ] Root cause identified (not just trigger)?
- [ ] Fix breaks causal chain at right point?
- [ ] All paths to root cause addressed?
- [ ] No alternative paths remain?

### Completeness Check
- [ ] All entry points covered?
- [ ] All code paths through fix exercised?
- [ ] Edge cases handled?
- [ ] Error conditions handled?

### Bypass Analysis
- [ ] Can fix be skipped (client-side only)?
- [ ] Encoding variations tested?
- [ ] Alternative input formats considered?
- [ ] Race conditions closed?

### Regression Analysis
- [ ] Existing tests still pass?
- [ ] Behavioral changes documented?
- [ ] Performance impact assessed?
- [ ] Compatibility verified?

### Defense in Depth
- [ ] Single point of failure avoided?
- [ ] Multiple layers of protection?
- [ ] Fail-secure behavior?

---

## Verification Test Categories

### Positive Tests
Verify fix works for intended cases:
- Original bug trigger → now fails/safe
- Documented attack vector → blocked
- Reported exploit → no longer works

### Negative Tests  
Verify fix doesn't break legitimate use:
- Normal operation → still works
- Valid edge cases → still handled
- Performance → acceptable

### Bypass Tests
Attempt to circumvent fix:
- Encoding variations
- Alternative paths
- Timing variations
- Unexpected input types

### Regression Tests
Ensure no new issues:
- Existing test suite passes
- Integration tests pass
- Security test suite passes

---

## Fix Quality Signals

### Strong Fix Indicators
- Addresses root cause at correct layer
- Adds defense in depth
- Includes comprehensive tests
- Documents reasoning
- Considers edge cases
- Fails securely

### Weak Fix Indicators
- Addresses symptoms only
- Single point of validation
- No new tests
- Minimal code change for complex bug
- Configuration-dependent
- Fails open

### Red Flags
- "Quick fix" or "workaround" language
- Disables security feature
- Adds exception/bypass
- Catches and ignores errors
- Client-side only validation
- "Will fix properly later"
