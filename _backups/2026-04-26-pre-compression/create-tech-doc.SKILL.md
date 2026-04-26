---
name: create-tech-doc
description: Creates technical documentation or design docs through active brainstorming and collaboration. The agent decodes the problem top-down (breadth-first from overview to details) then encodes the doc bottom-up (one validated section at a time before final assembly). Use when the user asks to write a tech doc, design doc, RFC, LLD, architecture doc, or any documentation that explains a system, feature, or problem-solution flow. Also trigger when the user says "help me think through this doc", "let's write a design doc", or shares a ticket and asks to document the approach.
---

## Update vs Create

**Update mode:** Given existing doc path + PR/branch reference — diff current doc against codebase changes, propose specific section updates (not full rewrite). Same Stage 3 encode rhythm, only for sections needing update.

**Create mode:** Full workflow below.

# Create Tech Doc

Collaborative, story-driven technical documentation. Goal: reader can **visualize and feel** problem and solution.

Brainstorming session as much as writing session. Propose angles, connect dots, surface tensions — don't wait to be told.

---

## Two-direction model

**Decode (top → down)**: Traverse content tree breadth-first — root first (what is this, why, who affected), full coverage at each level, then descend. Never drill detail before parent level settled.

**Encode (bottom → up)**: Write validated leaves first — one section at a time, reviewed and signed off before next. Assemble full tree only once every leaf locked.

Tree: Root = overview/problem. Internal nodes = major sections. Leaves = decisions, examples, edge cases.

**Keep tree shallow.** 2-3 levels max. 4th level → flatten it. Deep trees hide structure.

**Descend without repeating.** Single orienting breadcrumb when entering sub-sections. Don't re-explain parent.

---

## Stages

### Stage 1 — Decode: understand problem together

Work from available context. Form picture of problem, solution, connecting story. Propose your read — suggest angles user hasn't articulated, name tensions and trade-offs.

Questions go breadth-first: broadest unknowns first. What is this? Why? Who affected? Don't ask about sub-area until top-level settled.

Goal: shared sharp mental model of what doc needs to say and why.

**Optional:** Offer: *"Want me to check for existing plans, related PRs, or past discussions via /search-history?"* Do not run automatically.

### Stage 2 — Propose shape

Propose doc structure as story arc — what needs said, in what order, for momentum over topic-listing.

**Top-level sections only first** (still BFS). No sub-sections yet. Get sign-off on full breadth before breaking down internals.

Explain briefly why each section exists and its job in the story. Push back if structure breaks flow or adds unnecessary depth.

**Gate**: Confirm user happy with structure. Ask which section to start with. Only move to Stage 3 on explicit confirm.

### Stage 3 — Encode: build story one leaf at a time

**Conversational, not formatted.** Agree on content before committing to paper.

**Encode rhythm**: propose one section → user reviews → incorporate feedback → next. Repeat until all signed off.

**One section per response, no exceptions.** After proposing: *"Does this capture it? Anything to adjust before [next section]?"* Then wait.

**One section** = one named heading from agreed structure. Heading with multiple decisions/flows → break into sub-sections, propose one at a time.

**Within a section — what makes it strong:**
- Open with scene or question — foothold before explaining
- Show flows visually — numbered steps, before/after, ASCII diagrams (see [flow-examples.md](flow-examples.md))
- Ground every concept in concrete example — real system names, data shapes, API calls
- Layer depth: overview → decision → example → edge case
- Connect backwards — reference what was established before introducing new
- End with bridge to next section

**Entering sub-sections**: single orienting breadcrumb, then proceed. Don't restate parent.

### Stage 4 — Assemble

Only after **every section proposed, reviewed, signed off** in Stage 3.

Full formatted doc in one block. If user provided template, map each section into corresponding heading exactly — transcription, not rewriting.

No template: header metadata → TL;DR (written last, placed first) → sections in story order → appendix.

---

## Core principles

| Principle | Rule |
|---|---|
| **Decode before encode** | Fully understand problem tree top-down before building any section bottom-up |
| **Story arc before formatting** | Agree on every section's content before producing formatted doc |
| **One section, one response** | No exceptions — user's reaction shapes next section |
| **BFS on the way down** | Questions, structure, ordering all go broad before deep |
| **Shallow trees** | 2-3 levels max. Flatten before nesting |
| **Breadcrumb, not recap** | One orienting sentence entering sub-sections |
| **Brainstorm together** | Propose, challenge, connect |
| **Show, don't tell** | Every concept gets concrete example |
| **Visible flow** | Diagrams or step lists, not buried in prose |
| **Connect sections** | Each hands off to next. Reader feels the thread |

---

## Supporting files

- [flow-examples.md](flow-examples.md) — ASCII diagram conventions and examples
