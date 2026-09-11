# sat-analysis changelog

## 3.1.0 — 2026-09-11 (engine 1.1.0)

Research port onto the 3.x engine; see `docs/2026-09-11-research-port.md`.

- Added: ICD 203 ladder-term and band validation; likelihood/confidence same-sentence rejection (D.6.e.(2)(b)).
- Added: `sat coherentize`; `sat_engine.coherence` (coherentize, incoherence metric, equal-weight aggregation).
- Added: `posterior_probability` on hypotheses; trace `coherence` block; `posterior_leaders_disagree` diagnostic.
- Added: catalog 1.1.0 with `ICD203-LIKELIHOOD-TERMS`, `ICD203-LIKELIHOOD-CONFIDENCE-SENTENCE`, `MANDEL-COHERENTIZE`, `KM2020-PSEUDODIAGNOSTIC`, `EVID-ACH-NOT-A-DEBIASER`, `NATO-INFORMATION-CREDIBILITY`.
- Added: opt-in `sat_engine.parc` descriptive ranking (harness only); `evaluations/ranking_baselines.py` with a synthetic corpus.
- Changed: analytic trace gains `coherence` (engine 1.0.0 → 1.1.0); golden fixtures regenerated through `tests/fixtures/engine/regenerate_expected.py`.
- Changed: SKILL.md frontmatter uses the nested `metadata` block (PR #9 convention); versions 3.1.0 / 1.1.0 enforced by `tests/test_version_parity.py`.
- Unchanged: no computed causal winner; reliability never a numeric weight; strict sum-to-one contract; overlapping sets allowed; timeline refuses to assume a zone.

## 3.0.0 — 2026-09-09

Engine redesign with versioned contracts and verified artifacts (`feat/sat-engine-redesign`).
