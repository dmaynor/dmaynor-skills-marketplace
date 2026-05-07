---
name: sat-analysis
description: >-
  Structured Analytic Techniques (SAT) for rigorous analysis of user-supplied
  data. Applies intelligence community cognitive discipline to technical
  problems. Use when user provides logs asking about
  breach/anomaly/incident/compromise, crash dump/stack trace asking about cause,
  code diff asking if fix is correct/complete, or claim/statement asking for
  validity assessment. Triggers on "apply SAT", "structured analysis", "generate
  hypotheses", or "why did X happen" with ambiguous causation. Modes:
  BREACH_DETECTION, CRASH_ANALYSIS, FIX_VERIFICATION, STATEMENT_ANALYSIS,
  GENERAL_HYPOTHESIS.
author: dmaynor
version: 1.1.0
date: 2026-03-29
---

# Structured Analytic Techniques (SAT) Analysis

Apply intelligence community analytic tradecraft to technical analysis problems.
Enforces cognitive discipline, generates comprehensive hypotheses, evaluates
competing explanations, and produces calibrated assessments.

## Problem

Technical analysis often suffers from confirmation bias, anchoring on the first plausible explanation, and failure to consider alternative hypotheses. Without structured cognitive discipline, analysts jump from observation to conclusion, skipping rigorous evaluation of competing explanations and producing overconfident, unfalsifiable assessments.

## Mode Selection

Auto-select based on input:

| Input Pattern | Mode |
|--------------|------|
| Logs + security question | `BREACH_DETECTION` |
| Crash/stack trace + cause question | `CRASH_ANALYSIS` |
| Code diff + fix verification | `FIX_VERIFICATION` |
| Claim/statement + validity question | `STATEMENT_ANALYSIS` |
| Ambiguous situation | `GENERAL_HYPOTHESIS` |

## Core Workflow

Every analysis follows this sequence:

### 1. Observation Extraction (O/I Separation)

**Critical**: Separate observations from interpretations FIRST.

| Test | If Yes → |
|------|----------|
| Could a camera record this exactly? | Observation |
| Requires inference or judgment? | Interpretation → becomes hypothesis |

```
BAD:  "Attacker logged in at 3am"
GOOD: "Login recorded for user X at 03:00:00 from IP Y"

BAD:  "Malicious PowerShell execution"  
GOOD: "powershell.exe spawned by winword.exe at [time]"
```

### 2. Hypothesis Generation

**Minimum 5 hypotheses before any evaluation.**

Generation methods (use ≥2):
- **Actor Enumeration**: Who could be responsible?
- **Causal Pathway**: Work backward from effect
- **Inversion**: Generate opposite of obvious hypothesis
- **Dimensional**: Break into WHO/WHAT/WHY/HOW dimensions

**Required categories** (at least one each):
- Obvious/expected explanation
- Null hypothesis (nothing is wrong)
- Uncomfortable hypothesis (challenges assumptions)

### 3. Evaluation (ACH Matrix)

Rate each evidence-hypothesis pair:

| Rating | Symbol | Meaning |
|--------|--------|---------|
| Strongly Supports | `++` | Evidence predicted by hypothesis |
| Supports | `+` | Consistent with hypothesis |
| Neutral | `N` | Neither supports nor contradicts |
| Contradicts | `-` | Inconsistent with hypothesis |
| Strongly Contradicts | `--` | Argues against hypothesis |

Score: `++`=+2, `+`=+1, `N`=0, `-`=-1, `--`=-2

### 4. Confidence Calibration

**Always provide BOTH verbal term AND numeric range:**

| Term | Range | Usage |
|------|-------|-------|
| Almost Certain | 90-99% | Overwhelming evidence, no alternatives |
| Highly Likely | 80-89% | Strong evidence, alternatives unlikely |
| Likely | 65-79% | Preponderance, alternatives possible |
| Moderate | 50-64% | Genuine uncertainty |
| Unlikely | 20-49% | Evidence against, but possible |
| Remote | 5-19% | Little support |

### 5. Document Assumptions & Falsification

Every conclusion must include:
- Explicit assumptions
- What evidence would change the conclusion
- Limitations and gaps

## Output Template

```markdown
## SAT ANALYSIS: [Title]

**Mode**: [Mode]
**Confidence**: [Term] ([X-Y%])
**Techniques**: [List]

---

### OBSERVATIONS
| ID | Observation | Source | Time |
|----|-------------|--------|------|
| O1 | [Pure data] | [Src] | [T] |

### HYPOTHESES
| ID | Hypothesis | Category | Prob |
|----|------------|----------|------|
| H1 | [desc] | [cat] | [%] |

### ACH MATRIX
| Evidence | H1 | H2 | H3 | H4 | H5 |
|----------|----|----|----|----|-----|
| O1 | [rating] | ... |
| **SCORE** | [X] | [X] | [X] | [X] | [X] |

### ASSESSMENT
**Primary**: [Conclusion with confidence]
**Alternatives**: [What else is possible]

### ASSUMPTIONS
1. [Assumption]

### FALSIFICATION
- Would be falsified by: [evidence]
- Would be strengthened by: [evidence]

### LIMITATIONS
- [Gap or caveat]
```

## Mode-Specific Guidance

### BREACH_DETECTION

Required hypothesis categories:
1. Malicious External (attacker)
2. Malicious Internal (insider)
3. Non-Malicious Authorized (legitimate unusual)
4. Non-Malicious Unauthorized (policy violation)
5. System Artifact (false positive)
6. Null (normal activity)

Map to ATT&CK/kill chain where applicable. See `references/attack_patterns.md`.

### CRASH_ANALYSIS

Hypothesis dimensions:
- Memory (heap, stack, corruption)
- Threading (race, deadlock)
- Resource (exhaustion, leak)
- Logic (null, bounds, type, state)
- External (input, dependency, environment)
- Not-a-bug (expected behavior)

Distinguish proximate cause from root cause. See `references/crash_patterns.md`.

### FIX_VERIFICATION

Hypothesis categories:
1. Complete Fix (addresses root cause)
2. Partial Fix (some vectors)
3. Symptom Fix (masks, doesn't fix)
4. Ineffective (doesn't address)
5. Regression Risk (introduces new issues)
6. Bypass Possible (can be circumvented)

Trace causal chain from issue to fix. See `references/fix_patterns.md`.

### STATEMENT_ANALYSIS

Evaluate:
- Logical validity (does conclusion follow?)
- Evidential support (does evidence support?)
- Assumption robustness (how fragile?)
- Alternative plausibility

Decompose claim → evidence → assumptions → logical structure.

## Cognitive Discipline Checklist

Before ANY output, verify:

- [ ] O/I separation complete
- [ ] ≥5 hypotheses generated
- [ ] Null hypothesis present
- [ ] Uncomfortable hypothesis present
- [ ] ≥2 generation methods used
- [ ] All assumptions explicit
- [ ] Confidence has numeric range
- [ ] Falsification criteria defined
- [ ] Limitations stated

## Confidence Adjustment Factors

**Reduce confidence**:
| Factor | Adjustment |
|--------|------------|
| Single source | -10 to -20 |
| No corroboration | -10 to -15 |
| Conflicting evidence | -15 to -25 |
| Limited analysis time | -5 to -15 |

**May increase confidence**:
| Factor | Adjustment |
|--------|------------|
| Multiple independent sources | +5 to +15 |
| Direct observation | +5 to +10 |
| Corroboration | +5 to +15 |

## User Interaction

Support iterative refinement:
- "go deeper on H3" → expand specific hypothesis
- "more hypotheses" → generate additional
- "challenge this" → apply devil's advocacy
- "brief version" → compress output
- "what am I missing" → identify blind spots

## References

For detailed guidance, see:
- `references/techniques.md` - Full technique documentation
- `references/attack_patterns.md` - Security indicator patterns
- `references/crash_patterns.md` - Crash/failure patterns
- `references/fix_patterns.md` - Fix verification patterns
- `references/cognitive_biases.md` - Bias detection

## Verification

1. Confirm the analysis produces at least 5 hypotheses, including a null hypothesis and at least one uncomfortable hypothesis that challenges assumptions.
2. Verify every confidence assessment includes both a verbal term and a numeric probability range (e.g., "Likely (65-79%)").
3. Check that every hypothesis in the ACH matrix has a falsification criterion: specific evidence that, if found, would disprove it.
4. Confirm observations and interpretations are cleanly separated -- no interpretive language appears in the Observations table.
5. Validate that the Limitations section identifies at least one concrete gap or caveat in the available evidence.

## Scripts

- `scripts/parse_logs.py` - Parse common log formats
- `scripts/timeline.py` - Build event timelines
- `scripts/ach_matrix.py` - Generate ACH matrix markdown

## PDF Deliverable Output

When the user wants the analysis as a polished PDF (briefing for leadership, audit deliverable, archive document), use the `pdf-report-formatting` skill from this marketplace. It owns layout, typography, cover pages, TOC, running headers, page numbering, and table styling — your job is just to construct the content.

**Mapping SAT sections to pdf-report-formatting blocks:**

| SAT element | Block type |
|------------|------------|
| Observations table (O1, O2, ...) | `TableBlock` with columns ID / Observation / Source |
| Key Assumptions Check | `TableBlock` with `emphasized_rows` for the load-bearing assumption |
| Hypotheses table (H1...HN, with priors) | `TableBlock` |
| ACH matrix | `TableBlock` with `emphasized_rows=[score_row_index]` for the raw-score row |
| MPCoA / MDCoA pair | 3-column `TableBlock` (Dimension / MPCoA / MDCoA) |
| Confidence calibration callout | `CalloutBlock(kind="warn", keep_with_previous=True)` after the ACH matrix |
| Falsification criteria | `BulletsBlock` |
| Numbered list of risks (Q7-style ranked output) | `OrderedListBlock` |
| Recommendation summary | `CalloutBlock(kind="warn")` |
| Kill criteria | `TableBlock` |
| Limitations | `BulletsBlock` |

**Driver pattern:**

```python
from build_pdf import (
    build_report, Section, ParaBlock, TableBlock,
    CalloutBlock, BulletsBlock, OrderedListBlock,
)

build_report(
    output_path="/path/to/sat_analysis.pdf",
    title="SAT Analysis: <subject>",
    subtitle="<one-line framing>",
    metadata={
        "Mode": "STATEMENT_ANALYSIS",  # or whichever
        "Confidence": "Likely (65–75%)",
        "Date": "<YYYY-MM-DD>",
    },
    sections=[
        Section(title="Observation / Interpretation Separation", blocks=[...]),
        Section(title="Key Assumptions Check", blocks=[...]),
        Section(title="Hypotheses", blocks=[...]),
        Section(title="ACH Matrix", blocks=[...]),
        Section(title="MPCoA / MDCoA Table", blocks=[...]),
        Section(title="Recommendation", blocks=[...]),
        Section(title="Assumptions, Falsification, Limitations", blocks=[...]),
    ],
)
```

The builder auto-generates the cover page, table of contents, running header, and "Page N of M" footer. Section numbering is automatic — do NOT prefix titles with "1.", "2.". The packing rule (a section that consumed more than half a page is followed by a fresh page for the next section, AND a section whose natural height exceeds remaining space gets a fresh page) handles layout transitions automatically.

**When NOT to use pdf-report-formatting:**

- The user wants the analysis as inline chat output (default).
- The user wants markdown for a wiki / Confluence / Notion page (use markdown directly).
- The output is a one-paragraph response (overhead not justified).
