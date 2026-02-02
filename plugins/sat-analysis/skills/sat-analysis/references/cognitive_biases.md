# Cognitive Biases in Analysis

## High-Impact Biases

### Confirmation Bias
**Definition**: Seeking/favoring evidence supporting existing beliefs

**In Analysis**:
- Searching for evidence that confirms initial hypothesis
- Interpreting ambiguous evidence as supporting preferred conclusion
- Discounting contradictory evidence as "noise"
- Stopping search once confirming evidence found

**Mitigation**:
- Generate hypotheses BEFORE examining evidence
- Actively seek disconfirming evidence
- Use ACH to force consideration of alternatives
- Ask "What would prove me wrong?"

### Anchoring
**Definition**: Over-relying on first piece of information

**In Analysis**:
- First hypothesis becomes "default"
- Initial probability estimate persists despite new evidence
- Early evidence weighted more than later evidence
- First impression of actor/motive dominates

**Mitigation**:
- Generate multiple hypotheses before evaluating
- Explicitly re-estimate after each evidence piece
- Consider: "If I saw this evidence first, what would I conclude?"
- Use structured evaluation (ACH) to force equal treatment

### Availability Heuristic
**Definition**: Judging likelihood by ease of recall

**In Analysis**:
- Recent incidents seem more likely
- Dramatic scenarios overweighted
- Familiar patterns seen everywhere
- Rare but memorable events overestimated

**Mitigation**:
- Use base rates when available
- Don't let recent news drive assessment
- Consider: "Is this common or just memorable?"
- Calibrate against historical frequency

### Hindsight Bias
**Definition**: "Knew it all along" after outcome known

**In Analysis**:
- Post-incident: indicators seem obvious
- Overestimate past predictability
- Underestimate genuine uncertainty at time
- Leads to unfair blame/unrealistic expectations

**Mitigation**:
- Document reasoning AT TIME of analysis
- Pre-mortem analysis before outcomes
- Acknowledge what was genuinely unknowable
- Distinguish luck from skill

---

## Analysis-Specific Biases

### Mirror Imaging
**Definition**: Assuming others think/act like you

**In Analysis**:
- "Attacker wouldn't do that, it's inefficient"
- "No rational actor would..."
- Assuming shared values/logic/constraints
- Missing cultural/organizational differences

**Mitigation**:
- Explicitly model actor's perspective
- Consider different value systems
- Research actor's actual past behavior
- Ask "What if they don't think like me?"

### Clientism
**Definition**: Shaping analysis to please consumer

**In Analysis**:
- Softening bad news
- Emphasizing what stakeholders want to hear
- Avoiding conclusions that create work
- Downplaying threats to preferred projects

**Mitigation**:
- Separate analysis from recommendations
- Document confidence levels explicitly
- Present alternatives stakeholders may not like
- Maintain analytical independence

### Groupthink
**Definition**: Conformity pressure suppresses dissent

**In Analysis**:
- Team converges on consensus too quickly
- Dissenting views not voiced
- "We all agree" without rigorous debate
- Pressure to support team conclusion

**Mitigation**:
- Assign devil's advocate role
- Solicit written opinions before discussion
- Encourage and reward dissent
- Separate idea generation from evaluation

### Layering
**Definition**: Treating previous analysis as ground truth

**In Analysis**:
- Prior report conclusions become facts
- Inherited assumptions not questioned
- "We already know X" without re-verification
- Building on potentially flawed foundation

**Mitigation**:
- Trace conclusions to primary evidence
- Question inherited assumptions
- Verify key facts independently
- Note when relying on prior analysis

---

## Evidence Evaluation Biases

### Vividness Bias
**Definition**: Vivid evidence overweighted vs. statistical

**In Analysis**:
- Single dramatic example > aggregate data
- Testimony > statistics
- Concrete detail > abstract pattern
- Narrative > probability

**Mitigation**:
- Explicitly weight evidence types
- Don't let good storytelling drive conclusions
- Ask "What does the aggregate data show?"
- Balance anecdote with statistics

### Source Bias
**Definition**: Over/under-trusting based on source

**In Analysis**:
- Trusted source → uncritical acceptance
- Distrusted source → automatic rejection
- Prestigious source → assumed accuracy
- Technical source → assumed correctness

**Mitigation**:
- Evaluate evidence independent of source
- Consider: "Would I accept this from another source?"
- Verify key claims regardless of source
- Document source reliability separately from content

### Absent Evidence Blindness
**Definition**: Failing to notice missing evidence

**In Analysis**:
- Focusing on what IS there
- Not asking "What should be here but isn't?"
- Missing significance of gaps
- Incomplete coverage unnoticed

**Mitigation**:
- Explicitly list expected evidence
- Note what's missing, not just present
- Ask "What would complete picture look like?"
- Consider absence as potential evidence

---

## Probability Biases

### Overconfidence
**Definition**: Excessive certainty in judgments

**In Analysis**:
- Confidence exceeds accuracy
- Narrow probability ranges
- Underestimating uncertainty
- "I'm 90% sure" when should be 60%

**Mitigation**:
- Use calibration training
- Widen probability ranges
- Consider what would make you wrong
- Track historical accuracy

### Base Rate Neglect
**Definition**: Ignoring prior probabilities

**In Analysis**:
- APT attack! (ignoring 99.9% are commodity)
- Insider threat! (ignoring base rate)
- Rare event assumed without base rate check
- Diagnostic evidence without prior

**Mitigation**:
- Start with base rate
- Update based on evidence
- Ask "How common is this generally?"
- Use Bayesian reasoning

### Conjunction Fallacy
**Definition**: P(A and B) judged > P(A) alone

**In Analysis**:
- Detailed scenario seems more likely
- Adding specifics increases perceived probability
- Complex narrative beats simple
- "APT from China targeting finance" > "APT"

**Mitigation**:
- Break scenarios into components
- Multiply probabilities (they decrease)
- Simpler explanations often more likely
- Question detailed scenarios

---

## Debiasing Checklist

Before finalizing analysis:

- [ ] Did I generate hypotheses before looking at evidence?
- [ ] Did I actively seek disconfirming evidence?
- [ ] Am I anchored on my first hypothesis?
- [ ] Would I accept this evidence from a different source?
- [ ] What evidence is MISSING that should be here?
- [ ] Am I overconfident? Would I bet money at these odds?
- [ ] Am I assuming the actor thinks like me?
- [ ] Is my conclusion what stakeholders want to hear?
- [ ] Did the team converge too quickly?
- [ ] Am I building on verified facts or prior conclusions?
- [ ] What base rate applies here?
- [ ] Is my detailed scenario really more likely than simpler one?

---

## Red Flags in Your Own Analysis

| Signal | Potential Bias |
|--------|---------------|
| "Obviously..." | Confirmation, Anchoring |
| "Everyone knows..." | Groupthink, Layering |
| "No rational actor would..." | Mirror Imaging |
| "This is definitely..." | Overconfidence |
| "Just like last time..." | Availability |
| "The evidence clearly shows..." | Confirmation |
| "We've always assumed..." | Layering |
| "They would never..." | Mirror Imaging |
| "It's unlikely but..." | Base Rate Neglect |
| Quick consensus | Groupthink |
