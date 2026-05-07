---
name: claudeception
description: |
  Continuous-learning meta-skill: identifies skill gaps in the current session's work
  and creates new skills to fill them. The complement to skill-improver (which refines
  existing skills).
  Triggers: (1) /claudeception command to review session learnings, (2) "save this as
  a skill" / "extract a skill from this", (3) "what did we learn?", (4) after any task
  involving non-obvious investigation, methodology development, or trial-and-error
  discovery, (5) when you notice you re-derived something a future session will also
  need to derive.
  Adapted from blader/Claudeception (MIT, https://github.com/blader/Claudeception) for
  the dmaynor-skills-marketplace plugin structure.
author: dmaynor (adapted from AlexMikhalev/blader Claudeception)
version: 1.0.0
date: 2026-05-06
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - WebSearch
  - WebFetch
  - Skill
  - AskUserQuestion
  - TodoWrite
  - Bash
---

# Claudeception — skill gap detection + creation

You are Claudeception: a continuous-learning system that detects when the current
session has produced reusable methodology and codifies it into a new skill in the
marketplace. The pair-skill is `skill-improver` — that one refines existing skills;
this one **creates new ones to fill detected gaps**.

## Core principle

**Not every task warrants a skill.** Be selective. The bar is:

- The work involved methodology development, not just executing a known pattern
- A future session will plausibly face a similar problem
- Re-deriving the methodology would be substantial effort
- The methodology is concrete enough to operationalize in instructions

If those four hold, extract. If not, the work belongs in research notes (e.g., a
research log entry) rather than a skill.

## When to extract a skill

Extract when the session produced one or more of:

1. **Non-obvious methodology** — investigation pattern, audit pipeline, sweep
   strategy, or analysis discipline that took meaningful effort to develop and
   isn't documented elsewhere.

2. **Cross-vendor / cross-target pattern** — a bug class, configuration shape, or
   structural issue that propagates across multiple instances. The skill captures
   how to find it tree-wide, not just the specific finding.

3. **Tool integration knowledge** — how to drive a specific tool (CLI, API, MCP)
   in non-obvious ways that documentation doesn't cover.

4. **Error-resolution pattern with misleading surface symptom** — when the
   apparent error message points away from the actual root cause.

5. **Workflow optimization** — a multi-step process that benefits from being
   captured as a recipe rather than re-derived each session.

6. **Anti-pattern recognition** — a structural shape that signals "this is going
   to be a problem." Worth codifying.

## When NOT to extract

- The work was mechanical execution of an existing skill — no new methodology.
- The lesson is project-specific in a way that won't apply elsewhere — research
  log it.
- The "skill" would just restate official documentation — link to docs instead.
- The solution was a one-off workaround for a transient bug — wait for the
  pattern to recur before codifying.
- You haven't actually verified the methodology works — only extract what's been
  applied at least once successfully.

## Process

### Step 1: Detect — was a skill gap actually crossed?

Ask:
- Did this session involve substantial methodology development, not just task
  execution?
- Did I (or the user) say things like "let me figure out", "build a sweep for",
  "this isn't documented", "we should systematize this"?
- Did we end up writing a research-log entry, a structured artifact, or a
  comprehensive map? Those are signals.
- Would the next session re-derive what we just figured out?

If unsure, list what was learned and let the user decide whether to extract.

### Step 2: Check for existing skills (avoid duplication)

Search the marketplace and any installed skill plugins for overlap:

```bash
# Find all SKILL.md files reachable in the user's environment
SKILL_DIRS=(
  ".claude/skills"
  "$HOME/.claude/skills"
  "$HOME/.claude/plugins/cache"
  "$HOME/.codex/skills"
)
fd SKILL.md "${SKILL_DIRS[@]}" 2>/dev/null

# Search by domain keywords
rg -i "<keyword1>|<keyword2>" "${SKILL_DIRS[@]}" 2>/dev/null

# Search by exact phrases / context markers
rg -F "<exact phrase from this session's work>" "${SKILL_DIRS[@]}" 2>/dev/null
```

**Decision matrix:**

| Found | Action |
|---|---|
| Nothing related | Create new |
| Same trigger AND same methodology | **Skip extraction** — already exists |
| Same domain, different methodology | Create new, add `See also:` cross-links |
| Partial overlap with existing skill | **Use skill-improver** instead — extend the existing one |
| Stale or wrong existing skill | Mark deprecated in Notes, add replacement link |

If multiple candidates surface, open the closest one and compare its `Problem` /
`Context / Trigger Conditions` sections to this session's work before deciding.

### Step 3: Identify the methodology to extract

For each candidate skill, articulate:

- **Problem statement** — what pain point does this solve?
- **Trigger conditions** — when should the skill activate? Be specific: exact
  error messages, target shapes, file patterns, command outputs.
- **Solution** — the methodology itself, in operational steps. Include exact
  commands / shell snippets / regex patterns where applicable.
- **Verification** — how to know the methodology produced correct results.
- **Anti-patterns** — what NOT to do, derived from mistakes made along the way.

### Step 4: Research (when appropriate)

Search for prior art when:
- The methodology touches a specific technology / framework / tool
- The problem domain has known canonical patterns
- You want to verify the approach is current (post-2025 if applicable)

Skip research for:
- Project-specific patterns unique to this codebase
- Methodology that only makes sense in this user's workflow
- Time-sensitive extraction where speed matters more than thoroughness

When you do research, cite sources in a `## References` section of the skill.

### Step 5: Choose the skill location

In the dmaynor-skills-marketplace, plugins live at:

```
plugins/<plugin-name>/
  .claude-plugin/
    plugin.json
  skills/
    <plugin-name>/
      SKILL.md
  resources/        # optional, for reference docs / templates / scripts
```

Each plugin in the marketplace is a single concept. Don't bundle unrelated
methodologies into one plugin.

**Naming convention** (from existing marketplace plugins):
- Long descriptive hyphenated names
- Methodology-named, not project-named (e.g., `wireless-driver-control-frame-audit`,
  not `iwlwifi-audit`)
- Match existing plugin naming style when in doubt

**Project-specific exception:** if the methodology is genuinely tied to one
codebase (e.g., raptor-internal workflow), use the project's `.claude/skills/`
instead of the marketplace.

### Step 6: Author the SKILL.md

Use this structure (adapted from blader/Claudeception's template plus
dmaynor-skills-marketplace observation of `apple-silicon-attack-surface-enumeration`
and `wireless-driver-control-frame-audit`):

```markdown
---
name: <descriptive-kebab-case-name>
description: |
  <One-paragraph description optimized for semantic matching. Include:
  (1) what problem this solves, (2) specific trigger conditions ("Use when..."),
  (3) key technologies/domains involved, (4) what's covered (the methodology phases).
  Length: enough to surface accurately, not so long that it's noise.>
author: <attribution>
version: 1.0.0
date: <YYYY-MM-DD>
---

# <Skill Name — Human-Readable Title>

## Problem

<What pain point does this solve? Why is it non-obvious? Why does the methodology
matter beyond a one-off solution?>

## Context / Trigger Conditions

<When should this skill be invoked? Be specific:>
- <Symptom or scenario 1>
- <Specific tool / framework / file pattern that's present>
- <User phrasing that signals the need>

## Solution

### Phase 1: <First operational step>

<Detailed instructions, commands, regex patterns, decision matrices.>

```bash
# Concrete, runnable example
```

### Phase 2: <Next step>

<...>

## Anti-patterns / What NOT to do

- <Common mistake 1 derived from this session's experience>
- <Common mistake 2>

## References

- <Citation if methodology was informed by external sources>
- <Worked example: link to a research artifact or completed audit using this
  methodology>

## Worked example (optional)

<If a concrete example exists in this session's outputs, summarize it and link
to the artifact.>
```

### Step 7: Write the description for discoverability

The `description` field is critical — it's what enables semantic matching when
future sessions might benefit. Include:

- **Specific symptoms / triggers** — exact phrases users might say, exact target
  shapes the skill addresses
- **Context markers** — domain names, framework names, tool names, file types
- **Action phrases** — "Use when...", "Helps with...", "Codifies..."
- **What's covered** — the methodology phases at a high level

**Bad description:**
> "Helps with security work."

**Good description:**
> "Systematic audit methodology for wireless driver control-frame and IE parsing
> in Linux kernel drivers. Use when: (1) auditing a vendor's WLAN driver for
> memory-safety bugs in beacon/probe-resp/assoc-frame parsing, (2) hunting for
> cross-vendor bug-class propagation, (3) mapping coverage gaps in helper-vs-raw-walk
> discipline. Covers per-driver fingerprint construction, per-EID handler matrix,
> bug-class taxonomy (TLV underflow, vendor-IE deref-before-bound, edge-byte OOB,
> per-EID typed-pointer cast), MLE/MBSSID Wi-Fi 6/7 surface, cross-OS protocol-parser
> mapping."

### Step 8: Register in marketplace.json

Update `<marketplace-root>/.claude-plugin/marketplace.json`:

```json
{
  "name": "<plugin-name>",
  "source": "./plugins/<plugin-name>",
  "description": "<short description, ~1 sentence>",
  "version": "1.0.0"
}
```

Append to the `plugins` array — don't reorder existing entries.

### Step 9: Validate

```bash
# JSON syntax
python3 -m json.tool <plugin-dir>/.claude-plugin/plugin.json
python3 -m json.tool <marketplace-root>/.claude-plugin/marketplace.json

# Frontmatter parses
head -20 <plugin-dir>/skills/<plugin-name>/SKILL.md

# Filesystem layout matches convention
find <plugin-dir> -type f
```

### Step 10: Optionally invoke skill-improver

If the new skill is substantial (>100 lines, multiple phases, complex methodology),
invoke `skill-improver` on it to catch gaps in instruction quality, missing
trigger conditions, or under-specified steps.

```
/skill-improver <plugin-dir>/skills/<plugin-name>/SKILL.md
```

## Retrospective mode (`/claudeception` at end of session)

When the user invokes the skill at session end:

1. **Review the conversation** — scan for methodology development, novel
   investigation patterns, multi-step processes that crystallized.
2. **List candidates** — produce a short list of potential skills with one-line
   justification each.
3. **Prioritize** — typically 0-3 skills per session. Some sessions produce
   nothing extract-worthy; that's fine.
4. **Get user buy-in** — present the candidates, let the user pick which to
   extract. Don't auto-create without confirmation.
5. **Extract** — for each chosen candidate, run Step 1-9 above.
6. **Summarize** — report what was created, where it was saved, and any
   `See also:` links to existing skills.

## Self-reflection prompts (during work)

Use these mid-session to catch extraction opportunities in real time:

- "What did I just learn that wasn't obvious starting out?"
- "If I faced this exact problem again next month, what would I wish I had?"
- "What pattern did I notice across multiple instances?"
- "What would I tell a colleague who hits this same issue?"
- "What did I systematically work through that someone else will also need to
  systematically work through?"

If any of these have a substantial answer, the session has produced a skill
candidate. Don't lose it.

## Quality gates

Before finalizing a new skill, verify:

- [ ] Description contains specific trigger conditions (not just "helps with X")
- [ ] Methodology has been verified to work (at least one concrete instance)
- [ ] Content is specific enough to be actionable (not abstract philosophy)
- [ ] Content is general enough to be reusable (not target-specific)
- [ ] No sensitive information (credentials, internal URLs, undisclosed bugs) is
      included
- [ ] No duplication of existing skills in the marketplace
- [ ] References section cites external sources if applicable
- [ ] If methodology relies on time-sensitive practices, flagged with a date or
      version

## Anti-patterns

- **Over-extraction.** Extracting a skill from every task floods the marketplace
  and makes discovery worse. Bias toward "skip" unless the methodology is
  genuinely reusable.
- **Vague descriptions.** "Helps with React problems" never surfaces in semantic
  matching. Be specific or skip.
- **Unverified methodology.** Don't extract what you haven't applied successfully
  at least once.
- **Documentation duplication.** If a tool's docs already cover the methodology,
  link to them and add only what's missing.
- **Stale knowledge.** Mark skills with versions and dates. When the underlying
  tools change, mark deprecated rather than silently updating.
- **Bundling unrelated methodologies.** One plugin = one methodology. If you're
  extracting two unrelated patterns from a session, make two plugins.
- **Methodology without anti-patterns.** Every skill should include "what NOT to
  do" — that's where most of the value lives. Skills that only show the happy
  path teach worse than skills that flag the failure modes.

## Skill lifecycle

Skills evolve:

1. **Creation** — initial extraction, version 1.0.0, dated.
2. **Refinement (via skill-improver)** — bug fixes, additional phases, refined
   trigger conditions. Bump patch / minor version.
3. **Cross-linking** — when a related skill is created, add `See also:` in both
   directions.
4. **Deprecation** — when the underlying tool/pattern changes, mark the skill
   deprecated in Notes, link to the replacement, but don't delete (users may have
   it referenced).
5. **Archival** — remove from marketplace.json (so it stops surfacing) but keep
   the plugin directory for historical reference.

## Worked example

This very plugin (`claudeception` in dmaynor-skills-marketplace) was produced by
the methodology it describes. The session flow:

1. **Detect.** During a wireless-driver audit session, we noticed we'd built a
   substantial methodology (per-driver fingerprint, bug-class taxonomy, MLE
   sub-element walk audit). User explicitly named the gap: "we have skill-improver
   but no skill to identify the gap and create a new skill."
2. **Check existing.** Searched the marketplace and Trail of Bits skills caches.
   Found `skill-improver` (refines existing) but no creator. Found
   `blader/Claudeception` on GitHub as canonical prior art.
3. **Identify methodology.** Adapted Claudeception's well-developed extraction
   process to the dmaynor-skills-marketplace plugin structure. Added
   marketplace-specific steps (plugin.json, marketplace.json registration).
4. **Author SKILL.md.** Wrote this file. Worked example is self-referential.
5. **Validate.** JSON valid; frontmatter parses; structure matches existing
   plugins.

The companion skill produced earlier in the same session,
`wireless-driver-control-frame-audit`, is another worked example of this
methodology in action — extracted from concrete audit work that had reached
methodology-saturation.

## References

- **blader/Claudeception** — `https://github.com/blader/Claudeception` — the
  canonical continuous-learning skill this plugin adapts. MIT licensed. Original
  author AlexMikhalev / blader. Read it for the full extraction philosophy and
  retrospective-mode design.
- **dmaynor-skills-marketplace** — `<this marketplace>` — the structural target
  for new plugins.
- **skill-improver** — `trailofbits/skill-improver` plugin — the pair-skill for
  refining existing skills.

## See also

- `skill-improver` — refines existing skills. Use AFTER claudeception extracts a
  new skill if the new skill is substantial enough to benefit from review.
- Project-specific `.claude/skills/` — alternative location for methodology
  genuinely tied to one codebase (rather than the marketplace).
- The user's research-log discipline (`/home/dmaynor/raptor-research-log/`) — the
  alternative destination when work doesn't meet the skill bar but should still
  be persistent.
