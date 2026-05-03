---
name: create-tech-doc
description: Creates technical documentation or design docs through active brainstorming and collaboration. The agent decodes the problem top-down (breadth-first from overview to details) then encodes the doc bottom-up (one validated section at a time before final assembly). Use when the user asks to write a tech doc, design doc, RFC, LLD, architecture doc, or any documentation that explains a system, feature, or problem-solution flow. Also trigger when the user says "help me think through this doc", "let's write a design doc", or shares a ticket and asks to document the approach.
---

## Update vs Create

**Update:** Given existing doc + PR/branch — diff doc against codebase changes, propose section updates (not full rewrite). Same Stage 3 rhythm, only for changed sections.

**Create:** Full workflow below.

# Create Tech Doc

Collaborative, story-driven documentation. Goal: reader **visualizes and feels** problem + solution.

Brainstorming session as much as writing. Propose angles, connect dots, surface tensions.

---

## Two-direction model

**Decode (top → down)**: breadth-first — root first (what, why, who), full coverage per level, then descend. Never drill detail before parent settled.

**Encode (bottom → up)**: write validated leaves first — one section at a time, reviewed before next. Assemble only once every leaf locked.

Tree: Root = overview/problem. Internal = major sections. Leaves = decisions, examples, edge cases.

**Shallow trees.** 2-3 levels max. 4th level → flatten. Deep trees hide structure.

**Descend without repeating.** Single breadcrumb entering sub-sections.

---

## Stages

### Stage 1 — Decode: understand together

Form picture from context. Propose your read — suggest angles, name tensions.

Questions breadth-first: broadest unknowns first. Don't ask sub-area until top-level settled.

Goal: shared sharp mental model.

**Optional:** *"Check existing plans, related PRs, past discussions via /search-history?"* Don't run automatically.

### Stage 2 — Propose shape

Story arc — what needs said, in what order, for momentum over topic-listing.

**Top-level sections only** (BFS). No sub-sections yet. Get sign-off on breadth before depth.

Briefly explain each section's job in the story. Push back if structure breaks flow.

**Gate**: Confirm user happy. Ask which section first. Stage 3 only on explicit confirm.

### Stage 3 — Encode: one leaf at a time

**Conversational.** Agree on content before committing to paper.

**Rhythm**: propose one section → review → feedback → next. Repeat.

**One section per response, no exceptions.** After proposing: *"Does this capture it? Anything to adjust before [next]?"* Wait.

**Within a section — what makes it strong:**
- Open with scene/question — foothold before explaining
- Visual flows — numbered steps, before/after, ASCII diagrams (see [flow-examples.md](flow-examples.md))
- Ground every concept in concrete example
- Layer: overview → decision → example → edge case
- Connect backwards before introducing new
- Bridge to next section

### Stage 4 — Assemble

Only after **every section proposed, reviewed, signed off**.

Full formatted doc. If template provided → map sections into headings exactly (transcription, not rewrite).

No template: header metadata → TL;DR (written last, placed first) → sections in story order → appendix.

---

## Core principles

| Principle | Rule |
|---|---|
| **Decode before encode** | Understand problem tree top-down before building sections bottom-up |
| **Story before formatting** | Agree content before producing formatted doc |
| **One section, one response** | User reaction shapes next section |
| **BFS down** | Broad before deep |
| **Shallow trees** | 2-3 levels max. Flatten before nesting |
| **Breadcrumb, not recap** | One orienting sentence entering sub-sections |
| **Brainstorm together** | Propose, challenge, connect |
| **Show, don't tell** | Every concept gets concrete example |
| **Visible flow** | Diagrams/step lists, not buried in prose |
| **Connect sections** | Each hands off to next |

---

## Supporting files

- [flow-examples.md](flow-examples.md) — ASCII diagram conventions and examples

---

## Workflow ending

After doc assembled:

1. **Initiative seeding** — agree a slug (e.g., `agent-builder`, `manager-agent-v2`) with the user. Then write into `~/.claude/work_hq/initiatives/<slug>/`:

```bash
SLUG=<slug>
mkdir -p ~/.claude/work_hq/initiatives/$SLUG
# Charter: top-of-doc summary + scope from this tech doc
cat > ~/.claude/work_hq/initiatives/$SLUG/charter.md <<EOF
# <initiative-title>

## Vision
<1-2 sentence summary>

## Scope
- <bullet>
- <bullet>

## Tech doc
<confluence url, if posted>
EOF
# Touch the other 3 files so they exist for downstream skills:
: > ~/.claude/work_hq/initiatives/$SLUG/ticket-graph.md
: > ~/.claude/work_hq/initiatives/$SLUG/decisions.md
: > ~/.claude/work_hq/initiatives/$SLUG/learnings.md
# Append e2e-flow if applicable:
[ -n "$E2E_CONTENT" ] && echo "$E2E_CONTENT" > ~/.claude/work_hq/initiatives/$SLUG/e2e-flow.md
```

2. Run `work_hq append-context` with doc location + key decisions (existing).

3. Offer next action and surface artifacts:

```
───── workflow ─────
✓ Tech doc  : <confluence url | local path>
✓ Initiative: <slug> seeded at ~/.claude/work_hq/initiatives/<slug>/
→ Next      : /create-jira-ticket-with-reference  (create impl tickets)
            : /work-on-jira-task <ticket>          (start building)
────────────────────

───── artifacts ─────
Tech doc   : <confluence url>
Charter    : ~/.claude/work_hq/initiatives/<slug>/charter.md
Initiative : ~/.claude/work_hq/initiatives/<slug>/
─────────────────────
```
