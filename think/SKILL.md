---
name: think
description: Use when there's no ticket or PR yet and the user wants to think through a problem, weigh approaches, or explore an idea. Trigger on phrases like "let's think about", "I want to think through", "let's brainstorm", "let's explore", "should we", "before we build", "no ticket yet", "I have an idea", "weigh A vs B", "what's the right approach for", "research X". Anchors to a vault initiative, captures decisions/scope/learnings passively into vault DB during dialogue, ends on a decision menu (create tickets / work existing / write hybrid plan file / defer). Use INSTEAD OF superpowers:brainstorming in Akshat's dev workflow.
---

# Think — Anchored Brainstorm

Open-ended exploration that anchors to a vault initiative, captures into the brain as you go, and ends on a clear next step. Borrows discipline from `superpowers:brainstorming`; diverges on three mechanics:

- **Bundled questions** via `AskUserQuestion` (not one-at-a-time).
- **Plan file output** at `~/.claude/plans/<slug>.md` (not `docs/superpowers/specs/`).
- **Vault passive capture** during dialogue (3-way classifier into `initiatives/<slug>/{decisions,charter,learnings}.md`).

Wrapper owns capture — never invoke `superpowers:brainstorming`, never write outside `wiki/` and `~/.claude/plans/`.

---

## Pre-entry: resolve initiative (mandatory, ≤3 steps)

Determine the initiative slug. Try in order, stop at first hit. Surface one line: `↳ initiative: <slug> (resolved via <step>)`.

1. **Branch's existing work_hq context** — if branch has an `ENG-\d+` ticket, run `python3 ~/.claude/work_hq/update.py get <TICKET_ID>`. If it returns `initiative_slug`, use it.
2. **Keyword match** — list `~/opensource/vault/wiki/projects/*/initiatives/*/`, match user's request against initiative directory names + first-line of `charter.md` (when present). Surface top match: `↳ matched <slug> — proceed with this? (y/n)`.
3. **Propose new** — derive slug from user's request topic (lowercase, dashes, max 4 words). Ask once: `↳ creating new initiative <slug> under <repo>? (y/n)`. Repo defaults to cwd resolution; ask if cwd is not a repo.

Then load context: read `wiki/projects/<repo>/initiatives/<slug>/{charter,decisions,learnings,e2e-flow}.md` (skip files that don't exist). Read `~/.claude/work_hq/initiatives/<slug>/ticket-graph.md` for sibling tickets in flight.

---

## Body — bundled-question dialogue

### Dialogue pattern

1. **Reflect framing** — restate what the user is exploring in one sentence so they can correct early.
2. **Surface what's already known** — pull from loaded initiative context. Cite specifically: `per decisions.md: "..."`, `per charter constraints: "..."`, `per learnings.md: "..."`.
3. **Bundled clarifying questions via AskUserQuestion** — issue 2-4 questions in a SINGLE turn. Cover: constraint, deadline/reversibility, who's affected, success criteria. Multiple choice preferred over free text. NEVER ask one-at-a-time.
4. **Propose 2-3 approaches** — each with the main tradeoff named. Don't recommend yet.
5. **Narrow with another bundled AskUserQuestion** if discrimination is needed (1-3 questions max).
6. **Recommend** — pick one with main tradeoff explicitly named.
7. **Capture** — passive, see classifier below.

Iterate steps 3-6 as the user pulls threads. Don't railroad to a one-turn conclusion.

### Passive capture — 3-way classifier

The moment a discrete insight crystallizes, route by content type and surface the destination filename:

| Content type | Destination | Surface line |
|---|---|---|
| Concrete decision (chose A over B, picked approach X) | `initiatives/<slug>/decisions.md` | `↳ saved to decisions.md: <one-line>` |
| Charter scope/constraint (out of scope, must support X, deferred) | `initiatives/<slug>/charter.md` (under `## Constraints` or `## Out of Scope`) | `↳ saved to charter.md: <one-line>` |
| Past-tense insight from prior work ("we tried Y, didn't work because Z") | `initiatives/<slug>/learnings.md` | `↳ saved to learnings.md: <one-line>` |

**Format for `decisions.md` entries** (append, never overwrite):
```markdown
## YYYY-MM-DD — <one-line decision>
- Why: <rationale, one sentence>
- Trade: <what we give up, optional>
- Source: this /think session
```

**Format for `charter.md` entries** — append a bullet under the appropriate H2 (`## Constraints` / `## Out of Scope`); create the H2 if missing.

**Format for `learnings.md` entries** — append a dated bullet:
```markdown
- YYYY-MM-DD: <past-tense insight>. Why it matters now: <one-line>.
```

NEVER ask "should I save this?". Save and notify inline.

### Self-review trigger (>2 decisions in this session)

After the brainstorm produces a 3rd decision in `decisions.md` for this session, BEFORE the decision menu, run a quick scan:

- **Contradictions** — do any decisions in this session contradict each other or earlier `decisions.md` entries?
- **Ambiguity** — could any decision be interpreted two ways? Pick one and make explicit.
- **Scope drift** — did decisions creep beyond the charter? Flag for user.

Surface findings in 3-5 lines. Fix inline (with user confirmation) before menu. <3 decisions → skip self-review.

---

## Post-exit: decision menu

When user signals convergence ("ok let's do this", "I think we've got it", "let's move forward"), present:

```
Brainstorm complete. <N> decisions captured · initiative: <slug>

Pick next:
1. Create tickets   → /create-jira-ticket-with-reference
2. Work on existing → /work-on-jira-task <ticket-id>
3. Write plan       → ~/.claude/plans/<slug>.md  (this skill writes it directly — hybrid template below)
4. Defer            → already saved; come back any time
```

Never auto-pick. Wait for user.

---

## Plan file template (option 3 — hybrid spec + plan)

When user picks option 3, write a plan file at `~/.claude/plans/<slug>.md`. Same directory as plan-mode plans. Hybrid: spec-level rationale (so future-Claude understands *why*) + plan-level steps (so it can execute). Pull this session's vault captures inline.

**Do NOT delegate to `/writing-plans`** — this skill has already done the question-asking work; `/writing-plans` would re-ask. `/writing-plans` is for plans authored *outside* a brainstorm.

**Template:**

```markdown
# <Initiative Title> — Plan

> Generated from /think session on YYYY-MM-DD. Initiative: `<slug>`.
> Captures from `wiki/projects/<repo>/initiatives/<slug>/{decisions,charter,learnings}.md` (this session).

## Context

<2-3 sentences: why this work, what prompted it, intended outcome.>

## Decisions (this session)

- **<decision 1>** — <rationale, one line>. Trade: <what we give up>.
- **<decision 2>** — ...
(One bullet per entry written to decisions.md during this brainstorm. Cite verbatim.)

## Constraints (from charter)

- <constraint or scope item>
- Out of scope: <X>
(Pulled from charter.md; only items relevant to this plan.)

## Prior Learnings Honored

- <past-tense insight that shaped the approach>
(Pulled from learnings.md; only those that influenced a decision above.)

## Approach

<Chosen approach in prose, 1-3 paragraphs. Reference decisions and constraints by name.>

### Alternatives Considered

- **<alt A>** — rejected because <one-line>.
- **<alt B>** — rejected because <one-line>.

## Critical Files to Modify

| Path | Action |
|---|---|
| `<path>` | <create/edit/delete> — <one-line what changes> |

## Sequencing

1. <step — small, verifiable>
2. <step>
3. ...

## Verification

<How to test end-to-end. Specific commands, files to inspect, expected outputs.>

## Out of Scope

- <explicit non-goal>
- <deferred item with reason>
```

**Behavior on option 3:**
1. Draft the file contents using the template, populated from this session's vault captures.
2. Show the draft to the user inline (or summarize sections if very long).
3. On user approval: write to `~/.claude/plans/<slug>.md`. Surface: `↳ plan written: ~/.claude/plans/<slug>.md`.
4. On user changes requested: revise inline; re-show; write on approval.

The plan filename is `<slug>.md`. If multiple plans per initiative, use `<slug>-<topic>.md`.

---

## When NOT to use

- User shares a ticket URL → `/work-on-jira-task` directly.
- User shares a PR URL → `/explain-anything` or `/get-pr-ready-to-merge`.
- User asks for a tech doc → `/create-tech-doc`.
- User has a concrete bug to fix → `superpowers:systematic-debugging`.

---

## Notes

- Project context update happens throughout, not just at end — compaction-safe.
- The wrapper exists specifically to prevent `superpowers:brainstorming` from creating side artifacts (`docs/superpowers/specs/`). If tempted to invoke that skill from inside this one, don't.
- **Bundled questions are deliberate divergence** from `superpowers:brainstorming`. The user prefers fewer turns over its "one question at a time" rule.
- **Self-review at >2 decisions is deliberate** — single-decision brainstorms don't need it; many-decision brainstorms drift without it.

---

## Data Contract

### Reads (DB)
- `~/opensource/vault/wiki/projects/<repo>/overview.md` — project context (light)
- `~/opensource/vault/wiki/projects/<repo>/decisions.md` — existing project-level decisions
- `~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/{charter,decisions,learnings,e2e-flow}.md` — initiative context

### Reads (Memory)
- `~/.claude/work_hq/board.json` — for initiative resolution from branch
- `~/.claude/work_hq/initiatives/<slug>/ticket-graph.md` — sibling tickets in flight
- `~/opensource/vault/wiki/projects/<repo>/open-threads.md` — parked questions in this area

### Writes (Memory + DB)
- `~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/decisions.md` — passive capture (decisions only)
- `~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/charter.md` — passive capture (scope / constraints / out-of-scope)
- `~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/learnings.md` — passive capture (past-tense insights)
- `~/opensource/vault/wiki/projects/<repo>/open-threads.md` — append H2 if exploration parks a question (per CLAUDE.md)
- `~/opensource/vault/wiki/log.md` — append on session end: `<ts> think: <slug> — N decisions, M new threads, terminal=<menu choice>`
- `~/.claude/plans/<slug>.md` — only if menu option 3 chosen; written directly by this skill using the hybrid template above (NO `/writing-plans` handoff)

> DB writes from this skill are user-anchored captures during dialogue (not derived) — as durable as a manual Obsidian edit. Distinct from `/brain-ingest`'s weekly distillation.

### Local (skill-only)
- (none — wrapper deliberately avoids creating thoughts/, brainstorms/, side files)

### Live external (not stored)
- Jira / GitHub MCP for resolution
