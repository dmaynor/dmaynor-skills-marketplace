# SAT engine implementation and accuracy evidence

The engine redesign is implemented on `feat/sat-engine-redesign`. Architecture and
processing checks pass. **An analytical accuracy improvement has not been
established.** The first candidate failed one required-fact retention criterion in
one repeat; both independent reviewers agreed. The failure remains in the record.
A narrow instruction correction follows that result; it is not substituted into
the original benchmark. The existing installed helper skill was not promoted.

## Implemented architecture

| Contract | Implementation | Observed verification |
|---|---|---|
| ARCH-01 | Typed records, 11 versioned JSON schemas, strict offline validation, RFC 8785 hashes | Malformed JSON, references, formats, nonportable numbers, mode constraints, and exact canonical vectors tested |
| ARCH-02 | Provenance-preserving ingestion and timeline SDK | Original bytes/hashes, rejected records, physical lines, source identity, unknown clocks, fractional thresholds retained |
| ARCH-03 | Observation-linked ACH and compatibility wrappers | Missing differs from neutral; provenance inherited; derivative copies deduplicated; source/dependency sensitivity; no computed causal winner |
| ARCH-04 | Decision card, canonical trace, FULL tasking view, Markdown templates | Every derived field is recomputed for verification; rehashed altered outputs and stale summaries rejected |
| ARCH-05 | Offline doctrine catalog and enrichment | Reviewed source principles distinguished from local policy; unknown IDs rejected; repeated enrichment idempotent |
| ARCH-06 | Importable SDK, unified CLI, installable package | Installed commands and SDK exercised outside checkout, including real output publication |
| ARCH-07 | Thin SAT skill with LIGHT and five FULL domains | Domain/depth routing, actual engine use, explicit manual fallback and judgment boundaries; behavioral runs exercised LIGHT |
| ARCH-08 | Six portable fixtures and packaged resources | Six fixture replays plus hand-authored arithmetic/provenance/time expectations; 11 schemas, one catalog, four templates verified in wheel |
| ACC-01 | Existing corrected helper behavior | Baseline regressions retained in the combined suite |
| ACC-02 | Blinded analytical comparison | Completed with documented design limitations; improvement gate not met |

The combined suite passed **269 tests** on Python 3.12.14. This includes 32 tests
of the comparison aggregator; these are structural test counts, not 269 analytic
successes. The source CLI, installed entrypoint, SDK, schema/catalog export, and
complete artifact rendering were exercised. Wheel and sdist built; the wheel
rebuilt from the initial sdist had identical member contents. A final wheel was
then rebuilt and reinstalled after production changes, and all 12 packaged Python
modules and resource exports matched final source. The package evidence and exact installed dependency versions are retained in the
private benchmark audit.

Integration review found an output-publication race: ordinary POSIX rename could
replace a concurrently created empty directory. The CLI now uses atomic no-replace
publication on supported platforms, and the reproduced race passes regression.
Linux was exercised; Windows has an adapter but was not tested. Other platforms
can use the SDK or JSON stdout, while directory publication fails explicitly.

## Aided versus unaided comparison

The fixed suite contains 12 purpose-built cases spanning the five domains. Each
case was answered twice under three conditions:

- **No skill:** ordinary reasoning, with generic arithmetic/code tools allowed.
- **Current corrected:** the existing helper skill and its resources.
- **Engine:** the redesigned skill, SDK, schemas, references, and helpers.

Thus, “unaided” means no SAT aid, not a prohibition on arithmetic. All conditions
received the same raw prompts, common word target, and tool permissions. No
solver received the rubric or other answers. Six fresh solver contexts generated
72 responses; two independent reviewers scored anonymized responses by case group.
All response bytes were frozen before scoring. Reviewers supplied literal answer
quotations and explicit reasons, which the harness checked against saved files.

The primary unit is the **case**. A case passes only when every required criterion
passes on **both** repeats. Repeats and criteria are not counted as independent
cases. Engine versus current-corrected is the primary comparison; engine versus
no-skill is supporting. Factual and numerical errors are audited separately from
omissions. Decision usefulness and operator burden are secondary, not substitutes
for accuracy. Missing grades are never passes.

| Condition | Cases passing all critical checks on both repeats | Reviewed factual errors | Reviewed numerical errors |
|---|---:|---:|---:|
| No skill | 12/12 | 0 | 0 |
| Current corrected | 12/12 | 0 | 0 |
| First engine candidate | 11/12 | 0 | 0 |

The paired comparison has 11 shared passes, zero engine wins, and one engine loss
against each comparator: a descriptive difference of −1/12. One engine response omitted an established state transition from its brief
judgment. The fixed rubric required that fact. A second blinded reviewer independently reached the same
judgment. This is a required-fact omission, not a fabricated fact or numerical error.

The no-new-critical-regression guard therefore failed for the first candidate.
The engineering tests do not override that finding. The comparison, error ledger, independent recheck, and complete prepared runs
are preserved in the private audit. Raw prompts, generated answers, and local-path
metadata are not included in this public repository.

## Correction and interpretation

After freezing those results, the skill received one narrow instruction: retain
established state changes and their comparison baseline in the judgment, including
brief summaries. Uncertainty about the mechanism must not erase the known change.
Only the instructions changed; the engine implementation and original answers did
not. The initial and post-correction content fingerprints are both retained.

Targeted fresh-context runs of the exposed case assess this correction as a
**regression check**. They do not replace the original scores or constitute new
held-out evidence of overall improvement. Both fresh runs retained the missing transition and passed artifact verification.
The coordinator reviewed those outputs without blinding. Results and supporting
quotations are retained separately in the private audit.
A new improvement claim requires a new unexposed comparison suite.

## Limits that affect the conclusion

The cases/rubric were frozen after implementation had begun, although implementers
did not inspect their expectations. Each fresh context handled all 12 cases rather
than one case, so cross-case context could affect answers. Solver order was not
randomized or counterbalanced. Exact model/version, decoding settings, seeds, and
fixed execution budgets were not exposed. File restrictions were instructions,
not separate OS sandboxes. Baseline content fingerprints were recorded after its
answers; that skill was unchanged. Tool usage was reported by solvers rather than
independently exported full transcripts. Grading order was randomized only after
answer freeze. The complete deviation record is retained in the private audit.

Consequently, this is an exploratory comparison against frozen criteria. It does
not establish a causal effect of using the engine, real-world accuracy, probability
calibration, or equivalence. Both engine repeats used LIGHT; FULL is covered by
engineering fixtures and integration tests, not this behavioral comparison.

The engine validates declared data and computations. It does not authenticate
sources, infer that analyst assertions are true, or prove latency from clock
subtraction. Consistently fabricated input can produce consistent output.
Unresolved clock context and nonzero precision beyond microseconds remain
unresolved. Portable fixtures do not prove another language or platform matches
until an independent implementation runs them.

## Reproduce the checks

From `plugins/sat-analysis/skills/sat-analysis`, with declared dependencies installed:

```sh
python -m unittest discover -s tests -q
python -m sat_engine --version
python -m sat_engine export-contracts --output /tmp/sat-contracts-new
```

The evaluation aggregator is standard-library-only. It accepts the three prepared
reports (no-skill, current-corrected, engine) and `--expected-cases 12`. Private
prepared runs contain frozen prompts, answers, rubric, and completed scores for
`run_evaluation.py report`. These are assessor judgments; successful quote
validation is not independent proof that a grade is right.

The current three-arm comparison measures the bundled redesign. A further arm
using redesigned instructions with the engine disabled would separate instruction
changes from executable assistance. A stronger benchmark also needs a fresh
context per case/repeat, randomized order, locked model/settings, and a larger
unexposed corpus selected before observing candidate performance.

## Ranking baselines added in 3.1.0 (advisory)

`evaluations/ranking_baselines.py` on a 15-case synthetic corpus: descriptive total 100%,
PARC weighted inconsistency 93.3%, PARC with vague guard 100%. The single disagreement,
`breach_002`, is the one informative result: pure contradiction counting ranks the hypothesis
consistent with everything first, as Mandel, Karvetski and Dhami (2018) describe. The 100%
figures are construction artifacts and do not establish an accuracy improvement for any rule.
See `2026-09-11-research-port.md`.
