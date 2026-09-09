# Evaluating SAT behavior

Use this reference when maintaining or evaluating the skill, not while answering
an ordinary analysis request. Python 3.12+ and its standard library are enough.
The harness does not call a model, acquire credentials, or judge prose keywords.

## Freeze and separate inputs

`evaluations/cases.json` contains solver-facing raw prompts. `rubric.json` contains
assessor-only criteria and scoring anchors. Eight regression cases address shared
sources, confounded changes, invalid negative probes, mixed causation, fallback
capacity, confirmed simple failures, corrupted records/unknown clocks, and tied or
empty assessments. Four `held_out` variants use different surface facts.

Freeze both files before trials. Keep held-out text from implementation agents
until evaluation. `held_out` is a procedural designation, not access control: if a
variant was inspected or used for tuning, record that exposure and stop treating
it as untouched validation. Freeze a new case/version for another forward test.

Run three conditions: no skill, preserved previous skill, and revised skill. Give
fresh solver agents the identical raw prompt and only the selected skill for that
condition. Do not give them this rubric, change rationale, earlier diagnoses,
other answers, or the fact that they are being evaluated. Avoid inherited prior
conversation. Preserve actual raw answers before any scoring or editing.

Use the same model, reasoning settings, tool availability, output constraints,
and case/repeat selection in every condition. Record unknown or unexposed settings
as unknown rather than inventing values. Randomize execution order where
practical. Repeated fresh trials can expose variability; one trial cannot do so.
Hold the model constant while comparing instructions. A model change requires a
separate comparison, not an attribution of its difference to the skill.

## Prepare and collect

From the skill directory, prepare a run with a settings file describing the
actual setup. Store runs outside the installed skill. Example settings:

```json
{"reasoning":"inherited default; exact setting unexposed","tools":"same availability in all conditions","context":"fresh task-only thread","output_limit":"identical case prompt constraints"}
```

```bash
python3 evaluations/run_evaluation.py prepare \
  --output /path/to/runs/revised \
  --condition revised \
  --model 'inherited default; exact model unexposed' \
  --settings /path/to/settings.json \
  --skill-root /path/to/revised/sat-analysis \
  --split regression
```

Use `--case case-01 --case case-06` for a selected subset, `--split held_out` for
variants, and `--repeats 2` for independent repeats. Omit `--skill-root` for the
no-skill condition. Record the actual preserved skill location in the current
condition. The manifest fingerprints instructions/references for attribution;
hashes establish content identity, not analytic correctness.

Give solvers only the relevant `prompts/<trial-id>.txt` and selected skill
instructions. The prepared prompt contains no condition, expected answer, or
rubric. Save each exact answer at `answers/<trial-id>.txt` inside the run directory.
Fresh independent assessors receive the raw case, rubric, and anonymized answer
text, without condition labels or skill versions. Keep the answer-to-condition
mapping with the coordinator. Never ask the answer-producing agent to score itself.

After saving answers, create a fresh blank template with their content hashes:

```bash
python3 evaluations/run_evaluation.py score-template \
  --run /path/to/runs/revised \
  --output /path/to/runs/revised/assessor/scored.json
```

The template is intentionally unscored. Fill `assessor.id`, `assessor.blinded`,
each critical check's `status` (`pass`, `fail`, `unscored`), and each metric's
`score` (`0`, `1`, `2`, or `null`). Every actual rating requires a nonempty `reason`
and one or more verbatim `quotes` from that saved answer. Missing checks/metrics
remain unscored. A nonexistent quote cannot substantiate an omission: quote the
nearest relevant passage, explain the omission, and use a separate reviewer if
the judgment is disputed. Do not infer scores from headings or word matches.

Example of an individual metric judgment (illustrative, not a trial result):

```json
{"score":1,"reason":"The check is useful but has no decision boundary.","quotes":["Measure the application acknowledgment interval."]}
```

The harness checks quote presence, not the truth of an assessor's interpretation.
Resolve consequential scoring disagreements by an independent review; retain
both initial judgments and the adjudication. Assessors can be human or fresh
agents, but their identities and whether blinding actually occurred must be
recorded truthfully. The coordinator enters the blinded ratings into each run.

## Report observed results

```bash
python3 evaluations/run_evaluation.py report \
  --run /path/to/runs/revised \
  --scores /path/to/runs/revised/assessor/scored.json \
  --output /path/to/runs/revised/report.json
python3 evaluations/run_evaluation.py compare \
  /path/to/runs/none/report.json \
  /path/to/runs/current/report.json \
  /path/to/runs/revised/report.json \
  --output /path/to/runs/comparison.json
```

Omitting `--scores` yields `not_evaluated`, never a perfect result. Partial scoring
is `incomplete`; observed critical failures remain visible even with other scores
missing. `passed_observed_checks` means the supplied ratings passed this case set;
it does not establish general accuracy or authorize release. Reports expose
denominators, critical pass/fail/unscored counts, and separate 0–2 means for useful
conclusions, useful decisions, and proportionate operator burden. Means exclude
unscored entries; compare only matched coverage. Answer length is descriptive,
not a burden grade. Justified positive conclusions matter as much as appropriate
abstention, especially on the simple-failure cases.

The comparison reports different model/settings/rubric, mismatched cases or
prompts, incomplete scoring, and absent blinding as limitations. It does not
declare a winner or statistical improvement. Blinding and settings remain
procedure declarations; no local harness can verify them from JSON alone.

Run helper regressions separately:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

Test fixtures use explicitly synthetic scores to exercise harness behavior;
those are not model trials and must not be reported as skill performance.
For numeric likelihood calibration, collect a sufficiently broad set of resolved
cases with predeclared propositions and an appropriate proper scoring rule. This
small diagnostic suite does not supply that evidence.
