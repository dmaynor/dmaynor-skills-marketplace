# SAT Analysis Assessment Template

## SAT ANALYSIS: {{TITLE}}

**Mode**: {{MODE}}
**Date**: {{DATE}}
**Analyst**: {{ANALYST}}
**Confidence**: {{CONFIDENCE_TERM}} ({{CONFIDENCE_RANGE}})
**Techniques Applied**: {{TECHNIQUES}}

---

## EXECUTIVE SUMMARY

{{EXECUTIVE_SUMMARY}}

---

## OBSERVATIONS

### Data Sources Analyzed
| Source | Type | Time Range | Quality |
|--------|------|------------|---------|
| {{SOURCE}} | {{TYPE}} | {{RANGE}} | {{QUALITY}} |

### Extracted Observations (O/I Separated)
| ID | Timestamp | Observation | Source |
|----|-----------|-------------|--------|
| O1 | {{TIME}} | {{PURE_OBSERVATION}} | {{SOURCE}} |
| O2 | {{TIME}} | {{PURE_OBSERVATION}} | {{SOURCE}} |

### Data Gaps
- {{GAP_DESCRIPTION}}

---

## HYPOTHESES

### Generation Summary
- **Target**: {{MINIMUM}} | **Achieved**: {{ACTUAL}}
- **Methods Used**: {{METHODS}}

### Hypothesis List
| ID | Hypothesis | Category | Initial Prob |
|----|------------|----------|--------------|
| H1 | {{DESCRIPTION}} | {{CATEGORY}} | {{PROB}}% |
| H2 | {{DESCRIPTION}} | {{CATEGORY}} | {{PROB}}% |
| H3 | {{DESCRIPTION}} | {{CATEGORY}} | {{PROB}}% |
| H4 | {{DESCRIPTION}} | {{CATEGORY}} | {{PROB}}% |
| H5 | {{DESCRIPTION}} | {{CATEGORY}} | {{PROB}}% |

### Coverage Check
- ✓ Obvious/Expected: {{H_ID}}
- ✓ Null: {{H_ID}}
- ✓ Uncomfortable: {{H_ID}}
- ✓ Low-prob/High-impact: {{H_ID}}

---

## EVALUATION

### ACH Consistency Matrix

| Evidence | H1 | H2 | H3 | H4 | H5 |
|----------|----|----|----|----|-----|
| O1: {{DESC}} | {{RATING}} | {{RATING}} | {{RATING}} | {{RATING}} | {{RATING}} |
| O2: {{DESC}} | {{RATING}} | {{RATING}} | {{RATING}} | {{RATING}} | {{RATING}} |
| **SCORE** | **{{SCORE}}** | **{{SCORE}}** | **{{SCORE}}** | **{{SCORE}}** | **{{SCORE}}** |

### Results
- **Most Consistent**: {{H_ID}} ({{SCORE}})
- **Least Consistent**: {{H_ID}} ({{SCORE}})

### Key Discriminating Evidence
1. {{EVIDENCE_ID}}: {{WHY_DISCRIMINATING}}
2. {{EVIDENCE_ID}}: {{WHY_DISCRIMINATING}}

### Sensitivity Check
{{SENSITIVITY_RESULT}}

---

## ASSESSMENT

### Primary Judgment
{{PRIMARY_JUDGMENT}}

**Confidence**: {{CONFIDENCE_TERM}} ({{CONFIDENCE_RANGE}})

### Supporting Evidence
- {{EVIDENCE_SUMMARY}}

### Key Uncertainties
- {{UNCERTAINTY}}

### Alternatives Not Ruled Out
| Hypothesis | Probability | Why Still Possible |
|------------|-------------|--------------------|
| {{H_ID}} | {{PROB}}% | {{REASON}} |

---

## ASSUMPTIONS

| ID | Assumption | Criticality | Testable |
|----|------------|-------------|----------|
| A1 | {{ASSUMPTION}} | {{HIGH/MED/LOW}} | {{YES/NO}} |
| A2 | {{ASSUMPTION}} | {{HIGH/MED/LOW}} | {{YES/NO}} |

### Assumption Breaks
- If {{CONDITION}}, then {{CONSEQUENCE}}

---

## FALSIFICATION CRITERIA

### Would Falsify (confidence drops to <50%)
- {{EVIDENCE_THAT_WOULD_FALSIFY}}

### Would Strengthen (confidence rises to >85%)
- {{EVIDENCE_THAT_WOULD_STRENGTHEN}}

---

## LIMITATIONS

1. {{LIMITATION}}
2. {{LIMITATION}}
3. {{LIMITATION}}

---

## RECOMMENDATIONS

### Immediate Actions
1. {{ACTION}}

### Further Investigation
1. {{INVESTIGATION}}

### Mitigation/Response
1. {{MITIGATION}}

---

## COGNITIVE DISCIPLINE CHECKLIST

- [{{X}}] Observations separated from interpretations
- [{{X}}] ≥5 hypotheses generated before evaluation
- [{{X}}] Null hypothesis included
- [{{X}}] Uncomfortable hypothesis included
- [{{X}}] ≥2 generation methods used
- [{{X}}] All assumptions explicit
- [{{X}}] Confidence includes numeric range
- [{{X}}] Falsification criteria defined
- [{{X}}] Limitations stated

---

*Analysis performed using Structured Analytic Techniques.*
*Confidence calibrated to available evidence.*
