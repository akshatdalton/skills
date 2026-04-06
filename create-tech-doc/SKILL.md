---
name: create-tech-doc
description: Creates technical documentation or design docs through active brainstorming and collaboration. The agent decodes the problem top-down (breadth-first from overview to details) then encodes the doc bottom-up (one validated section at a time before final assembly). Use when the user asks to write a tech doc, design doc, RFC, LLD, architecture doc, or any documentation that explains a system, feature, or problem-solution flow. Also trigger when the user says "help me think through this doc", "let's write a design doc", or shares a ticket and asks to document the approach.
---

# Create Tech Doc

A collaborative, story-driven approach to technical documentation. The goal is to leave the reader able to **visualize and feel** the problem and solution — not just read about it.

This is a brainstorming session as much as a writing session. Think alongside the user — propose angles, connect dots, surface tensions — don't just wait to be told what to write. The user steers; you actively participate.

---

## The two-direction model

The whole skill runs on one structural insight: **decode top-down, encode bottom-up.**

**Decode (top → down)**: Understand the problem by traversing the content tree breadth-first — start at the root (what is this, why does it exist, who is affected), get full coverage at that level, then descend one level. Never drill into a detail before the parent level is settled. This is how you ask questions and propose structure.

**Encode (bottom → up)**: Write the doc by building validated leaves first — one section at a time, each reviewed and signed off before moving to the next. Assemble the full tree (final formatted doc) only once every leaf is locked. This is how you write.

The tree itself:
- **Root** = overview / problem statement
- **Internal nodes** = major sections and sub-sections
- **Leaves** = specific decisions, examples, edge cases

Two rules that follow from this:

**Keep the tree shallow.** Prefer 2–3 levels of depth. If something wants a 4th level, flatten it — push detail up or collapse the nesting. Deep trees hide structure.

**Descend without repeating.** When moving from a section into its sub-sections, a single orienting breadcrumb is enough: *"This section covers X, Y, Z — starting with X."* Don't re-explain the parent. The reader just read it.

---

## Stages

### Stage 1 — Decode: understand the problem together

Work from whatever context you already have. Form a picture of the problem, the solution, and the story connecting them. Propose your read — suggest angles the user hasn't articulated yet, name tensions and trade-offs.

Ask questions breadth-first (decode direction): broadest unknowns first. What is this? Why does it exist? Who is affected? Don't ask about a specific sub-area until the top-level picture is settled. Don't ask for the sake of process.

Goal: by the end of this stage, both you and the user share a sharp mental model of what this doc needs to say and why.

---

### Stage 2 — Propose the shape

Once the problem is understood, propose the doc's structure as a story arc — what needs to be said, in what order, so it reads with momentum rather than as a list of topics.

Propose **top-level sections only first** (still decoding breadth-first). No sub-sections yet. Get sign-off on the full breadth before proposing how any one section breaks down internally.

Make the proposal feel alive: explain briefly why each section exists and what job it does in the story. Push back if the user suggests a structure that breaks flow or introduces unnecessary depth.

**Gate**: Before writing anything, confirm the user is happy with the proposed structure. Ask which section to start with. Only move to Stage 3 once they explicitly confirm.

---

### Stage 3 — Encode: build the story arc one leaf at a time

This stage is **conversational, not formatted.** You're agreeing on what each section says before committing it to paper.

**The encode rhythm**: propose one section's content → user reviews → incorporate feedback → move to the next. Repeat until every section is signed off.

**One section per response, no exceptions** — even when you have all the information you need. After proposing a section, ask: *"Does this capture it? Anything to adjust before we move to [next section]?"* Then wait. The user's reaction to each section shapes the next.

**What counts as one section**: one named heading from the agreed structure. A heading that contains multiple decisions or flows must be broken into sub-sections and proposed one at a time — it's not one section just because it carries one heading.

**Within a section — what makes it strong:**
- Open with a scene or a question — give the reader a foothold before explaining
- Show flows visually — numbered steps, before/after comparisons, ASCII diagrams (see [flow-examples.md](flow-examples.md))
- Ground every concept in a concrete example — real system names, real data shapes, real API calls
- Layer depth naturally — overview → decision → example → edge case
- Connect backwards — reference what was just established before introducing what's new
- End with a bridge — one line that hands off to the next section

**When entering sub-sections**: open with a single orienting breadcrumb line, then proceed. Don't restate the parent.

---

### Stage 4 — Assemble: the full doc in one block

Only reached once **every section has been proposed, reviewed, and signed off** in Stage 3.

Produce the full formatted doc in one block. If the user provided a template, map each agreed section into its corresponding heading exactly — this step is transcription, not rewriting. Don't add, remove, or reframe signed-off content.

If no template was provided: header metadata → TL;DR (written last, placed first) → sections in story order → appendix.

---

## Core principles

| Principle | Rule |
|---|---|
| **Decode before encode** | Fully understand the problem tree top-down before building any section bottom-up. |
| **Story arc before formatting** | Agree on what every section says before producing a single line of the formatted doc. |
| **One section, one response** | No exceptions — not even when you have all the info. The user's reaction shapes the next section. |
| **BFS on the way down** | Questions, structure proposals, and section ordering all go broad before deep. |
| **Shallow trees** | 2–3 levels max. Flatten before nesting. |
| **Breadcrumb, not recap** | One orienting sentence when entering sub-sections. Trust the reader's memory. |
| **Brainstorm together** | Propose, challenge, connect. Don't just respond. |
| **Show, don't just tell** | Every concept gets a concrete example. |
| **Visible flow** | Flows in diagrams or step lists, not buried in prose. |
| **Connect sections** | Each section hands off to the next. The reader should feel the thread. |

---

## Supporting files

- [flow-examples.md](flow-examples.md) — ASCII diagram conventions and examples to use in sections
