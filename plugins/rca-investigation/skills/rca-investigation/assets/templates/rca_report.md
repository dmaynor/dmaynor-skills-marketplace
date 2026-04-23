# RCA Investigation Report Template

## RCA INVESTIGATION: {{TITLE}}

**Mode**: {{MODE}}
**Date**: {{DATE}}
**Root Cause Layer**: L{{N}} — {{LAYER_NAME}}
**Confidence**: {{CONFIDENCE_TERM}} ({{CONFIDENCE_RANGE}})

---

## EXECUTIVE SUMMARY

{{ONE_PARAGRAPH_SUMMARY}}

---

## TIMELINE

| Time | Event | Source | Layer |
|------|-------|--------|-------|
| {{TIME}} | {{EVENT}} | {{SOURCE}} | L{{N}} |

---

## FAILURE TAXONOMY WALKTHROUGH

| Layer | Checked | Finding | Evidence |
|-------|---------|---------|----------|
| L1: External Infrastructure | {{✓/✗}} | {{Clear/Suspect/Ruled Out}} | {{EVIDENCE}} |
| L2: Local Infrastructure | {{✓/✗}} | {{STATUS}} | {{EVIDENCE}} |
| L3: Environment | {{✓/✗}} | {{STATUS}} | {{EVIDENCE}} |
| L4: Tooling | {{✓/✗}} | {{STATUS}} | {{EVIDENCE}} |
| L5: Application Logic | {{✓/✗}} | {{STATUS}} | {{EVIDENCE}} |
| L6: Process/Human | {{✓/✗}} | {{STATUS}} | {{EVIDENCE}} |

---

## CAUSAL CHAIN

```
ROOT CAUSE (L{{N}}): {{ROOT_CAUSE}}
  → PROXIMATE CAUSE: {{PROXIMATE}}
    → SYMPTOM: {{SYMPTOM}}
      → OBSERVED EFFECT: {{EFFECT}}
```

---

## CONTRIBUTING FACTORS

| Factor | Layer | Made it worse how? | Independently fixable? |
|--------|-------|-------------------|----------------------|
| {{FACTOR}} | L{{N}} | {{IMPACT}} | {{YES/NO}} |

---

## ROOT CAUSE STATEMENT

{{DETAILED_ROOT_CAUSE_WITH_EVIDENCE}}

---

## CORRECTIVE ACTIONS

| # | Action | Targets Layer | Layer Match? | Proportional? | Overcorrection Test |
|---|--------|--------------|-------------|---------------|-------------------|
| 1 | {{ACTION}} | L{{N}} | {{YES/NO}} | {{YES/NO}} | {{PASS/FAIL}} |

---

## WHAT WOULD NOT HAVE HELPED

| Rejected Action | Why Not | Anti-Pattern |
|----------------|---------|-------------|
| {{ACTION}} | {{REASON}} | {{PATTERN_NAME}} |

---

## ASSUMPTIONS

| ID | Assumption | Criticality | Testable? |
|----|------------|-------------|----------|
| A1 | {{ASSUMPTION}} | {{HIGH/MED/LOW}} | {{YES/NO}} |

---

## OPEN QUESTIONS

- {{QUESTION}}

---

## COGNITIVE DISCIPLINE CHECKLIST

- [{{X}}] Timeline reconstructed with sources
- [{{X}}] All 6 layers checked or ruled out with evidence
- [{{X}}] Root cause layer identified with evidence
- [{{X}}] Causal chain separated (≥3 levels)
- [{{X}}] Contributing factors distinguished from root cause
- [{{X}}] Corrective actions target root cause layer
- [{{X}}] Overcorrection test applied to each action
- [{{X}}] Confidence has numeric range
- [{{X}}] Open questions documented
- [{{X}}] Anti-patterns checked

---

*Analysis performed using RCA Investigation methodology.*
*Root cause isolated to Layer {{N}} with {{CONFIDENCE}} confidence.*
