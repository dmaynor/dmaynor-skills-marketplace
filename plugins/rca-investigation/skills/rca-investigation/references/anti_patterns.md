# RCA Anti-Patterns Reference

## Common RCA Mistakes

### 1. Layer Skip
**What it looks like:** Jumping straight to "the process was wrong" or "the code had a bug" without checking infrastructure.

**Why it happens:** Application and process layers are cognitively accessible — you can reason about them without checking external systems. Infrastructure failures require investigation.

**Fix:** Mandate the taxonomy walkthrough. Every layer gets a row in the table, even if the finding is "Ruled out — no evidence."

**Classic example:** "We shouldn't use agents for complex tasks" when the API was having an outage. The fix targeted L4 (tooling) when the failure was L1 (external infrastructure).

### 2. Narrative Fallacy
**What it looks like:** The RCA reads like a story with a clear beginning, middle, end, and moral. Everything fits too neatly.

**Why it happens:** Humans are storytelling machines. We instinctively construct coherent narratives, pruning inconvenient evidence.

**Fix:** Check if any evidence was ignored because it didn't fit the narrative. List evidence that contradicts the conclusion.

### 3. Hindsight Bias
**What it looks like:** "We should have seen this coming" or "Obviously X was going to fail."

**Why it happens:** Knowing the outcome makes prior signals seem more significant than they were at the time.

**Fix:** Ask "What signals were actually available at decision time?" and "What was the base rate for this type of failure?"

### 4. Single Cause Fixation
**What it looks like:** "It was X" with no alternatives considered.

**Why it happens:** Finding one plausible cause satisfies the need for an explanation. Generating alternatives feels like wasted effort.

**Fix:** Require ≥3 candidate causes before selecting one. Use SAT-style hypothesis generation if needed.

### 5. Overcorrection
**What it looks like:** The corrective action is disproportionate to the failure. Banning an entire approach because it failed once.

**Why it happens:** Recency bias amplifies the most recent failure. The emotional response to failure drives larger-than-necessary changes.

**Fix:** Apply the overcorrection test: "Would I propose this change if the failure hadn't happened?" If no, you're reacting, not reasoning.

### 6. Blame Assignment
**What it looks like:** The RCA identifies a person rather than a system gap.

**Why it happens:** Identifying a responsible individual feels like resolution. "Bob caused it" is simpler than "The system allowed an error."

**Fix:** For every person-blame, ask "What system allowed this to happen? What guardrail was missing?"

### 7. Symptom Treatment
**What it looks like:** The fix addresses the visible failure but not its cause. The same failure recurs in a different form.

**Why it happens:** Symptoms are immediately visible and feel urgent. Root causes require investigation.

**Fix:** Trace the causal chain. If your fix targets anything after the first "→", you're treating a symptom.

### 8. Survivorship Bias
**What it looks like:** "This approach always works" based on times it succeeded, ignoring silent failures.

**Why it happens:** Successes are visible and memorable. Failures that didn't cause visible damage are forgotten.

**Fix:** Ask "How would I know if this had failed silently?" Check for evidence of near-misses.

### 9. Availability Bias
**What it looks like:** Attributing the failure to whatever you were recently thinking about or recently read about.

**Why it happens:** Recently encountered information is more cognitively available and feels more probable.

**Fix:** Generate causes from the taxonomy, not from memory. The taxonomy forces consideration of all layers regardless of what's top-of-mind.

### 10. Premature Closure
**What it looks like:** Stopping the investigation as soon as any cause is found, without checking if it's THE cause.

**Why it happens:** Investigation is costly. Finding a cause reduces uncertainty and feels like progress.

**Fix:** After finding a cause, ask "Does this explain ALL the evidence?" If anything is unexplained, keep going.
