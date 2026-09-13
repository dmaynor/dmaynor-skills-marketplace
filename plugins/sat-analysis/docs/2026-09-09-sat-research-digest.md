# SAT Research Digest — load-bearing facts for the v2.0 research-integration amendment

**Date:** 2026-09-09
**Purpose:** The facts, formulas, and scales that `2026-09-09-research-integration-amendment.md` cites by section. The full research report (taxonomy catalog, per-technique entries, IARPA CREATE, full evidence discussion) lives in the conversation that produced it; this digest carries only what the tasks need. Section letters match that report.

**Labeling:** `[Verified — primary]` = drawn from an official document or peer-reviewed paper that was accessed. `[Unverified]` = plausible, secondary. `[Speculative]` = inference.

---

## A.5 — MLCOA / MDCOA lineage `[Verified — primary]`

Most Likely / Most Dangerous Course of Action is US Army IPB doctrine (ATP 2-01.3, *Intelligence Preparation of the Battlefield*, 2019, Step 4 "Determine Threat Courses of Action"). It is a hypothesis-generation-and-ranking device from a separate lineage than SATs. Its value here is decision logic: rank on most likely, **act** on most dangerous when the cost asymmetry warrants. Belongs on the decision card, not in the analytic method.

## B.1 — Heuer's eight ACH steps `[Verified — primary: Psychology of Intelligence Analysis, ch. 8]`

1. Identify all reasonable hypotheses (ideally mutually exclusive).
2. List significant evidence and arguments for and against each.
3. Matrix: hypotheses as columns, evidence as rows; rate each cell.
4. Refine: delete evidence with no diagnostic value; reconsider hypotheses.
5. Draw tentative conclusions working down columns; **seek to disprove, not prove** — the hypothesis with the *least* inconsistent evidence is provisionally most likely.
6. Analyze sensitivity to a few critical items.
7. Report conclusions including the relative likelihood of **all** hypotheses.
8. Identify milestones/indicators for future observation.

## B.2 — Why symmetric summing rewards vague hypotheses `[Verified — primary: Mandel, Karvetski & Dhami 2018]`

Only inconsistency counts in Heuer's rule; evidence consistent with all hypotheses "has no diagnostic value" (Primer, fn. 5). A hypothesis vague enough to be consistent with everything accrues zero inconsistency and wins. Mandel et al.'s worked example: A rated {2,2,2,2,−2}, B rated {0,0,1,0,−1} → ACH ranks B above A (inconsistency −1 vs −2) despite A's overwhelming support. Symmetric +/− summing discards exactly the disconfirmation logic that defines the method.

## B.3 — PARC ACH 2.0 weighted inconsistency `[Verified — primary: PARC ACH0 Technical Description 2004; Karvetski & Mandel 2020 Table 2; SANS ISC #22470]`

```
base  = {"II": -2, "I": -1, "N": 0, "C": 0, "CC": 0}     # at Medium/Medium
mult  = {"L": 0.707, "M": 1.0, "H": 1.414}               # = {1/√2, 1, √2}
cell  = base[consistency] * mult[credibility] * mult[relevance]
score = Σ cell over evidence rows                          # ≤ 0; closest to 0 = least inconsistent
```

PARC (2004): "a consistency entry of 'I' counts −1 against the corresponding hypothesis and an entry of 'II' counts −2 ... (All other entries are ignored.)" The default weight table has (High/Medium) = (Medium/Low), hence the √2 sequence. A **different, additive** variant (I = 1, II = 2 points, ±0.3–0.8 credibility adjustments) appears in Dhami, Belton & Mandel (2019) — that is the Heuer & Pherson / Pherson Associates tool, not PARC. The two accounts describe two tools; they do not conflict.

## B.4 — Bayesian variants `[Verified — peer-reviewed]`

Karvetski, Olson, Gantz & Cross (2013), *EURO J. Decision Processes* — Bayesian-network ACH; Pope & Jøsang (2005) — subjective-logic ACH; IARPA CREATE → BARD (Bayesian Argumentation via Delphi), large effects vs business-as-usual in the developers' study, IARPA's own test collapsed from attrition. Common finding: a probabilistic backbone beats ordinal inconsistency counting. Deferred to Phase 10.

## B.5 — Empirical record on ACH `[Verified — peer-reviewed primary]`

| Study | N / sample | Finding |
|---|---|---|
| Lehner, Adelman, Cheikes & Brown 2008, *IEEE SMC* (MITRE 2004 precursor) | non-analysts and analysts | ACH reduced confirmation bias in non-analysts; **no effect on experienced analysts** |
| Dhami, Belton & Mandel 2019, *Appl. Cogn. Psych.* | 50 UK analysts | ACH users skipped steps (esp. step 5); "ACH may increase judgement inconsistency and error"; 9/25 vs 8/24 chose the correct H |
| Mandel, Karvetski & Dhami 2018, *JDM* 13(6):607–621 | analysts | Control slightly more accurate and coherent than ACH; ACH worsened additivity violations. **Coherentize + aggregate cut MAE 61%.** Normalization beat CAP (MAE .13 vs .15); equal-weight aggregation matched coherence-weighting |
| Karvetski & Mandel 2020, *JDM* 15(6):939–958 | 227 | No coherence advantage; ACH slightly less reliable (MAD .22 vs .18, d = 0.20); **pseudo-diagnostic weighting** — non-diagnostic evidence pulled ~32% as hard as diagnostic |
| Whitesmith 2019, *Intell. & Nat. Sec.* 34(2) | | ACH "no statistically significant mitigative impact" on serial-position effects or confirmation bias |
| Chang, Berdini, Mandel & Tetlock 2018, *Intell. & Nat. Sec.* 33(3) | critique | SATs treat bipolar biases as unipolar (over-correction risk); decomposition assumed sound without evidence |
| Coulthart 2017, *IJIC* 30(2) | methods synthesis | The positive outlier; a research-quality review, not an accuracy experiment. Mandel et al. call its ACH conclusion "unwarranted" |
| Artner, Girven & Bruce 2016, RAND RR-1408 | IC product review | The IC does not systematically evaluate SATs; SAT mention rare (40% / 29% / 21% of sampled CIA / NIC / DIA products) |

**Weight of evidence:** ACH does not reliably reduce confirmation bias, improve accuracy, or improve coherence in controlled tests. What does: coherentization, small-group aggregation, calibration training/recalibration, Bayesian structuring, forecasting-tournament practice.

**Caveats:** dominated by one research group; N modest; tasks "neater" than real problems; transfer to technical analysis unmeasured → Phase 9.

## C.1 — ICD 203 (2015, revalidated June 2023) `[Verified — primary: intelligence.gov PDF]`

**Five Analytic Standards:** objective; independent of political consideration; timely; based on all available sources; implements the nine Analytic Tradecraft Standards.

**Nine tradecraft standards, §D.6.e.(1)–(9):** (1) properly describes quality and credibility of underlying sources, data, and methodologies; (2) properly expresses and explains uncertainties associated with major analytic judgments; (3) properly distinguishes between underlying intelligence information and analysts' assumptions and judgments; (4) incorporates analysis of alternatives; (5) demonstrates customer relevance and addresses implications; (6) uses clear and logical argumentation; (7) explains change to or consistency of analytic judgments; (8) makes accurate judgments and assessments; (9) incorporates effective visual information where appropriate.

**Likelihood ladder, §D.6.e.(2)(a)** — "strongly encouraged not to mix terms from different rows":

| almost no chance | very unlikely | unlikely | roughly even chance | likely | very likely | almost certain(ly) |
|---|---|---|---|---|---|---|
| remote | highly improbable | improbable | roughly even odds | probable | highly probable | nearly certain |
| 01–05% | 05–20% | 20–45% | 45–55% | 55–80% | 80–95% | 95–99% |

**Likelihood/confidence rule, §D.6.e.(2)(b), verbatim:** products that express confidence using a confidence level "must not combine a confidence level and a degree of likelihood, which refers to an event or development, in the same sentence." Confidence "may be based on the logic and evidentiary base that underpin it, including the quantity and quality of source material, and their understanding of the topic."

**Indicators / implications:** std (2) "identify indicators that would alter the levels of uncertainty"; std (3) "indicators that, if detected, would alter judgments"; std (4) indicators affecting the likelihood of alternatives; std (5) address implications and customer relevance.

**Correction to the spec:** the pinpoint is §D.6.e.(2)(b), not "§c.6"; the spec's "§c.4" and "§c.7" do not match the document's structure (source quality = std (1); assumptions vs judgments = std (3)). Confirm against the 2023-revalidated PDF during enrichment before marking `verified`.

**ICD 206 (2015)** `[Verified — primary: fas.org]`: source reference citations, source descriptors, and source summary statements covering accuracy/completeness, D&D, currency, access, validation, motivation, bias, expertise. ICS 206-01 updated Dec 2024 for OSINT.

## C.3 — Comparison scales

**UK PHIA Probability Yardstick** `[Verified — primary: College of Policing / gov.uk]` — ≤5% remote chance; 10–20% highly unlikely; 25–35% unlikely; 40–<50% realistic possibility; 55–75% likely/probably; 80–90% highly likely; ≥95% almost certain. Gaps between bands are deliberate (Omand): they prevent arguments at a boundary.

**NATO Admiralty Code (AJP-2.1 under STANAG 2511)** `[Verified — corroborated; primary AJP-2.1 text not fetched]` — assessed **in isolation**:

| Source reliability | Information credibility |
|---|---|
| A completely reliable | 1 confirmed by other sources |
| B usually reliable | 2 probably true |
| C fairly reliable | 3 possibly true |
| D not usually reliable | 4 doubtful |
| E unreliable | 5 improbable |
| F reliability cannot be judged | 6 truth cannot be judged |

`F` and `6` are unjudged states, not "low."

## C.5 — Likelihood vs confidence, operationalized `[Verified — Irwin & Mandel 2023, Risk Analysis 43(5)]`

Likelihood = probability the judgment is true. Confidence = strength of the evidentiary/logical basis. Experts and non-experts routinely conflate them; ~one-fourth of experts gave incoherent numeric translations of *likely*/*unlikely*. Report numeric probability and confidence **separately**. Format: "We assess X is likely (55–80%)." / "Confidence: moderate, based on …"

## D.1 — Scoring rule to implement

PARC weighted inconsistency (B.3); least-inconsistent wins; zero-diagnostic rows listed, not ranked on; leave-one-out sensitivity on the top weighted items; vague-hypothesis guard; ties surfaced, never resolved by a consistency sum.

## D.2 — Coherence layer to implement

For a MECE set require Σp = 1. Coherentize by normalization (record raw, coherent, and IM = ‖raw − coherent‖₂). Aggregate 2–5 elicitations by equal-weight averaging of coherentized vectors. Prior and posterior are separate coherent vectors. `[Speculative]`: whether independent LLM elicitation runs are independent enough for the human aggregation gain to transfer — measure it.

## D.7 — Anti-pattern catalog `[synthesized from B.5 sources]`

False precision (ordinal −1/−2 as measurement) · box-checking / ACH theater (skipped step 5) · anchoring on the matrix · the hypothesis that explains everything · incoherent probabilities · symmetric +/− summing · technique as substitute for domain expertise · groupthink in team techniques · unipolar over-correction · pseudo-diagnostic weighting · claiming ACH removed bias.

---

## Sources

- *A Tradecraft Primer: Structured Analytic Techniques for Improving Intelligence Analysis*, US Government/CIA, 2009 — https://www.cia.gov/resources/csi/static/Tradecraft-Primer-apr09.pdf
- Heuer, *Psychology of Intelligence Analysis*, CIA CSI, 1999 — https://archive.org/details/PsychologyOfIntelligenceAnalysis
- Heuer & Pherson, *Structured Analytic Techniques for Intelligence Analysis*, 3rd ed., SAGE/CQ Press, 2019/2020
- ICD 203, *Analytic Standards*, ODNI, 2015 (revalidated 2023) — https://www.intelligence.gov/assets/documents/intelligence-community-directives/ICD_203.pdf
- ICD 206, *Sourcing Requirements for Disseminated Analytic Products*, ODNI, 2015 — https://irp.fas.org/dni/icd/icd-206.pdf
- Mandel, Karvetski & Dhami, "Boosting intelligence analysts' judgment accuracy: What works, what fails?", *JDM* 13(6):607–621, 2018
- Karvetski & Mandel, "Coherence of probability judgments from uncertain evidence: Does ACH help?", *JDM* 15(6):939–958, 2020 — https://jbaron.org/journal/20/200430/jdm200430.html
- Dhami, Belton & Mandel, "The 'analysis of competing hypotheses' in intelligence analysis", *Applied Cognitive Psychology* 33(6), 2019 — https://strathprints.strath.ac.uk/69049/
- Whitesmith, "The efficacy of ACH in mitigating serial position effects and confirmation bias…", *Intelligence and National Security* 34(2), 2019 — https://www.tandfonline.com/doi/full/10.1080/02684527.2018.1534640
- Chang, Berdini, Mandel & Tetlock, "Restructuring structured analytic techniques in intelligence", *Intelligence and National Security* 33(3), 2018
- Coulthart, "An Evidence-Based Evaluation of 12 Core Structured Analytic Techniques", *IJIC* 30(2), 2017
- Artner, Girven & Bruce, *Assessing the Value of Structured Analytic Techniques in the U.S. Intelligence Community*, RAND RR-1408, 2016 — https://www.rand.org/pubs/research_reports/RR1408.html
- Karvetski, Olson, Gantz & Cross, "Structuring and analyzing competing hypotheses with Bayesian networks", *EURO J. Decision Processes*, 2013
- Lehner, Adelman, Cheikes & Brown, "Confirmation Bias in Complex Analyses", *IEEE Trans. SMC* 38(3), 2008
- Irwin & Mandel, "Communicating uncertainty in national security intelligence…", *Risk Analysis* 43(5), 2023
- PARC ACH0 Technical Description, 2004 — https://www.cse.sc.edu/~mgv/BNSeminar/ACHAlgorithms-v12.pdf ; SANS ISC Diary #22470 — https://isc.sans.edu/diary/22470
- BARD / IARPA CREATE — https://ar5iv.labs.arxiv.org/html/2003.01207 ; https://www.iarpa.gov/research-programs/create
- UK PHIA Probability Yardstick — https://www.college.police.uk/app/intelligence-management/analysis/delivering-effective-analysis
- ATP 2-01.3, *Intelligence Preparation of the Battlefield*, US Army, 2019
