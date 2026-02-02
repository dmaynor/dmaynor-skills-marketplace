# SAT Techniques Reference

## Generation Techniques

### Hypothesis Saturation Drill

Generate maximum quantity before quality filtering. Quantity enables quality.

**Process**:
1. Set minimum target (simple: 5, moderate: 10, complex: 15)
2. Apply ≥3 generation methods
3. Check category coverage
4. Quality filter AFTER generation complete

**Methods**:

#### Dimensional Decomposition
Break into independent dimensions:
- WHO: Actors (external/internal/system/environmental)
- WHAT: Events (what actually occurred)
- WHY: Motivations (malicious/accidental/legitimate)
- HOW: Mechanisms (technical methods)
- WHEN: Timeline (immediate/staged/dormant)

#### Causal Pathway Enumeration
Work backward from observed effect:
```
EFFECT → What directly caused this?
       → What caused that?
       → Continue to initiating events
```

#### Actor Enumeration
| Category | Examples |
|----------|----------|
| External Malicious | APT, criminal, competitor |
| Internal Malicious | Insider, disgruntled |
| External Non-Malicious | Vendor, partner, researcher |
| Internal Non-Malicious | Employee, IT, security team |
| System/Automated | Software bug, hardware failure |
| Environmental | Power, network, physical |

#### Inversion/Negation
For each obvious hypothesis, generate opposite:
- "Attacker did X" → "No attacker, system did X"
- "Bug caused crash" → "Crash is expected behavior"
- "Malicious" → "Legitimate but unusual"

#### Devil's Hypothesis Injection
Force uncomfortable hypotheses:
- What would embarrass the organization?
- What would challenge stakeholder assumptions?
- What do we NOT want to be true?

### Required Categories Checklist
- [ ] Obvious/Expected
- [ ] Null (nothing wrong)
- [ ] Uncomfortable (challenges assumptions)
- [ ] Low-probability/High-impact
- [ ] Combined (multiple factors)

---

## Evaluation Techniques

### Analysis of Competing Hypotheses (ACH)

Systematic evaluation against evidence using consistency matrix.

**When to use**: 3+ hypotheses, multiple evidence items, confirmation bias risk

**Process**:
1. List hypotheses as columns (3-7 optimal, max 10)
2. List evidence as rows (atomic facts)
3. Rate each cell for consistency
4. Sum scores
5. Identify discriminating evidence
6. Perform sensitivity analysis

**Rating Scale**:
```
++  Strongly Supports    (+2)  Evidence predicted by hypothesis
+   Supports             (+1)  Consistent with hypothesis
N   Neutral              (0)   Neither supports nor contradicts
-   Contradicts          (-1)  Inconsistent with hypothesis
--  Strongly Contradicts (-2)  Argues against hypothesis
```

**Rating Rules**:
- Rate DIAGNOSTICITY, not just consistency
- Ask: "If H is true, would I expect E?"
- Consider: "Does E distinguish between hypotheses?"
- Neutral is valid—don't force ratings

**Sensitivity Analysis**:
Remove most influential evidence item. Does conclusion change?
- Yes → Single-point dependency (vulnerability)
- No → Robust conclusion

**Interpretation**:
- ACH shows CONSISTENCY, not truth
- High score ≠ high probability (missing evidence possible)
- Low score = strong argument against
- Multiple high scores = genuine uncertainty

### Weighted Ranking Matrix

Prioritize options across multiple criteria.

**When to use**: Comparing options, prioritization needed, criteria vary in importance

**Process**:
1. Define criteria
2. Assign weights (must sum to 100%)
3. Score each option on each criterion (1-5)
4. Calculate weighted scores
5. Sensitivity test weights

### Falsification Testing

Actively seek evidence that would disprove hypothesis.

**Process**:
1. For top hypothesis, ask: "What evidence would prove this wrong?"
2. Search for that evidence
3. If found → reduce confidence significantly
4. If searched and not found → may increase confidence slightly
5. If unable to search → note gap

---

## Cognitive Discipline Techniques

### Observation/Interpretation Separation

**The O/I Test**:
1. Could a camera record this exactly? → Observation
2. Requires inference or judgment? → Interpretation
3. Could reasonable people disagree? → Interpretation

**Common Violations**:
| Interpretation | Pure Observation |
|----------------|------------------|
| "Attacker logged in" | "Login for user X from IP Y at time T" |
| "Malicious beacon" | "HTTP POST to [domain] every 60s" |
| "Data exfiltration" | "500MB transferred to [IP] over 3 hours" |
| "Brute force attack" | "53 failed password attempts in 3 minutes" |
| "Memory leak" | "Memory usage increased 500MB over 4 hours" |

**Red Flag Words** (indicate interpretation):
- Causal: "caused", "resulted in", "led to"
- Intent: "tried to", "attempted", "wanted"
- Classification: "malicious", "suspicious", "legitimate"
- Certainty: "clearly", "obviously", "definitely"
- Labels: "attacker", "victim", "insider"

### Confidence Calibration

**Scale with Practical Meaning**:
| Term | Range | Practical Test |
|------|-------|----------------|
| Almost Certain | 90-99% | Would bet heavily; alternatives nearly impossible |
| Highly Likely | 80-89% | Strong confidence; meaningful wrong chance |
| Likely | 65-79% | More likely than not; alternatives credible |
| Moderate | 50-64% | Toss-up; wouldn't be surprised either way |
| Unlikely | 20-49% | Probably not, but possible |
| Remote | 5-19% | Surprised, but not shocked |
| Almost None | 1-4% | Would require extraordinary evidence |

**Rules**:
1. Always pair verbal AND numeric
2. Use ranges, not points
3. Calibrate to evidence, not feeling
4. Check for overconfidence signals

**Overconfidence Signals**:
- Confidence >80% with limited evidence
- Cannot articulate what would change mind
- Dismissing alternatives quickly
- Using certainty language
- Anchored on first hypothesis

### Assumption Breaks

Identify conditions that invalidate conclusions.

**Process**:
1. List all assumptions (stated and unstated)
2. For each: How critical? What would break it?
3. Document: "If [condition], then [conclusion changes to]"

**Common Hidden Assumptions**:
- Logs are authentic and complete
- Timestamps are synchronized
- No authorized testing was occurring
- Actor is rational by our definition
- Tools behave as documented

### Pre-Mortem Analysis

Assume conclusion is WRONG. Why did it fail?

**Process**:
1. Assume your top hypothesis is proven wrong in 6 months
2. Write the story of why it failed
3. Identify vulnerabilities in your analysis
4. Strengthen weak points or reduce confidence
