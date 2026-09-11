# Research port onto the 3.x engine (skill 3.1.0, engine 1.1.0)

**Date:** 2026-09-11 · **Branch:** `sat-analysis/3.1-research-port` (rebased on master 15ba6d9)
**Base:** `feat/sat-engine-redesign` (skill 3.0.0, engine 1.0.0), chosen over the parallel
`sat-analysis/research-integration-2026-09` branch because its delivery layer, provenance
discipline, and no-computed-winner stance are the better-evidenced foundation. Sources for
every added rule: `2026-09-09-sat-research-digest.md`.

## Ported (additive; 3.0.0 contracts unchanged except where noted)

| Item | Where | Notes |
|---|---|---|
| ICD 203 likelihood ladder, band check | `sat_engine/uncertainty.py`, `ICD203-LIKELIHOOD-TERMS` | Rejects off-ladder terms and value/band mismatch |
| Likelihood/confidence same-sentence prohibition, D.6.e.(2)(b) | `sat_engine/uncertainty.py`, `ICD203-LIKELIHOOD-CONFIDENCE-SENTENCE` | Checked on summary, basis, reasoning, implications |
| Coherentize / incoherence metric / aggregate | `sat_engine/coherence.py`, `sat coherentize` | Analyst pre-step; the boundary's strict sum-to-one contract is kept |
| `posterior_probability` | hypothesis schema, `ach.py`, `models.py` | Same coherence contract as `initial_probability` |
| Trace `coherence` block | `pipeline.py`, `analytic_trace.v1.json`, trace template | Sums, metrics, posterior vs heuristic leaders, `posterior_leaders_disagree` diagnostic. **Contract change → engine 1.1.0, goldens regenerated via `tests/fixtures/engine/regenerate_expected.py`; structural diff showed only the added block and dependent hashes** |
| Research rules | catalog 1.1.0 | `MANDEL-COHERENTIZE`, `KM2020-PSEUDODIAGNOSTIC`, `EVID-ACH-NOT-A-DEBIASER`, `NATO-INFORMATION-CREDIBILITY` |
| Opt-in PARC descriptive ranking | `sat_engine/parc.py` | Explicit per-evidence weights; never called by the pipeline; harness only |
| Ranking baselines harness | `evaluations/ranking_baselines.py`, `evaluations/ranking_corpus/` | Advisory; synthetic corpus |
| Skill/reference text | SKILL.md, techniques.md, doctrine.md, engine.md, evaluation.md | Partition guidance, two-sentence rule, coherentize workflow, no-debiasing positioning |
| Version parity test | `tests/test_version_parity.py` | Skill axis and engine axis checked separately |

## Deliberately not ported from the 2.0.0a1 branch

- Timeline UTC assumption with flags — 3.x refuses to assume a zone; kept.
- Reliability as a numeric multiplier in the pipeline — 3.x keeps reliability an assertion; PARC weights are explicit analyst assertions supplied out of band.
- Coherentization inside the boundary — 3.x rejects incoherent fully-quantified sets; coherentization moved to the pre-step.
- `PartitionRequired` — 3.x allows `overlapping`; coherence facts are simply absent for it.
- The full SKILL.md rewrite; the 2.0 amendment plan (it targeted a codebase that no longer exists).

## Harness finding (reproduced on this engine)

`breach_002`: descriptive total → H3 (truth); PARC → H6 (the consistent-with-everything Null);
PARC with vague guard → H3. Pure contradiction counting rewards the vague hypothesis — Mandel,
Karvetski and Dhami (2018) reproduced — which corrects the 05-05 spec §1.2 #5 mechanism. The
`descriptive_total = 100%` figure is a construction artifact of the synthetic corpus and is not
evidence for that rule. No ranking rule choice is made on this corpus.

## Test state

285 tests, 550 subtests (3.0.0 baseline: 269 / 550). All 3.0.0 tests retained; the only edits
to existing tests were the `engine_version` constant and `coherence: None` in two hand-built traces.

## Open

- Replace the synthetic corpus with labeled real cases before any gate becomes blocking.
- Primary AJP-2.1 text for `NATO-INFORMATION-CREDIBILITY` not fetched (secondary corroboration only).
- `n_elicitations`-style aggregation is SDK-only; whether independent model elicitations transfer the human aggregation gain is unmeasured.
