---
name: aksenhq-dump-to-post
description: >
  Converts raw brain dumps — personal observations, things noticed while building,
  patterns from daily work — into publish-ready X posts for @aksenHQ. Use this skill
  whenever the user shares a raw thought, observation, or experience and wants to turn
  it into a post. Trigger on: "here's a brain dump", "I noticed something", "convert
  this to a post", "I want to post about this", "something I observed", "something from
  my work", "I have this thought", or any messy unstructured input that needs to become
  X content. Also trigger when the user says "let's work on an observation post" or
  "help me post something personal". Always use this skill — do not try to draft a post
  without running the pipeline.
---

# @aksenHQ Observation Pipeline

## Purpose

Convert raw brain dumps — personal observations, things noticed while building,
patterns from daily work — into publish-ready X posts for @aksenHQ.

**Core principle:**
```
dump contains the experience → post needs the insight → pipeline closes that gap
```

User drives. Claude navigates. Never skip steps. Never jump to drafting.
Always show pipeline state before moving forward. User picks at every branch.
Never advance without their call.

---

## Creator Context

@aksenHQ is an engineer-turned-product-thinker (MTS at EightFold AI, building MagnetX
as a solopreneur). The audience: indie hackers, solopreneurs, engineers leveling up to
product thinking, early-stage founders.

The communication philosophy: **Veritasium-style.** Don't open with the answer. Open with
the tension — something that feels wrong, counterintuitive, or shouldn't work. Make the
audience feel the friction first. Then decode it.

Test for every post: *"Can I explain why this is surprising in one sentence to someone
who's never encountered this before?"* Tension is universal. Domain knowledge is optional.

---

## Pipeline

```
DUMP → SURFACE → ANGLE → ELEVATE → FORMAT → DRAFT
```

Always show the full pipeline with a position marker at each transition:
```
DUMP ✅ → SURFACE ✅ → ANGLE ← we are here → ELEVATE → FORMAT → DRAFT
```

---

## Step 0 — Receive the Dump

Accept the input in any form — one sentence, a messy paragraph, disconnected bullets,
a voice-note-style stream. Do not clean it up or reframe it yet.

If the user hasn't provided a dump and says "help me find something to post about":
- Ask one prompt: "what's something you noticed or hit recently while building —
  something that felt obvious to you but might not be to others?"
- Wait for their response before proceeding.

Do NOT proceed to SURFACE until there is raw material to work with.

---

## Step 1 — Surface (Extract the Insight)

Read the dump and extract **2-3 candidate insights** buried in it.

An insight is not a summary of the experience. It is the **non-obvious thing** the
experience reveals — the part that would make someone who didn't have the experience
think "huh, I hadn't considered that."

**For each candidate, output this card:**
```
Insight N — [one-line label]
What it says: [the actual claim in plain terms]
Why it's non-obvious: [what most people assume instead]
Who cares: [which part of the audience this lands for]
```

Present all 2-3 cards. Do NOT pick one. Let the user:
- pick a card
- reject all and redirect
- say "combine N and M"

Do not proceed to ANGLE until user has made a call.

---

## Step 2 — Angle (Frame Why Anyone Else Cares)

User has picked an insight. Now find the angle — the framing that makes a stranger care.

Present **2-3 angle options**. Each angle is a different answer to: *why does this matter
to someone who isn't you?*

**Angle types to consider (not a closed list):**
- **Contrast** — this contradicts a common assumption
- **Mechanism** — this reveals how something actually works
- **Permission** — this gives someone license to do/think something they were avoiding
- **Pattern** — this is a specific case of a broader thing most people haven't named
- **Receipt** — this is a real result, not an opinion (use when numbers/outcomes exist)

**For each angle option:**
```
Angle N — [type]
Frame: [one sentence — how this insight reads from the outside]
Hook energy: [what emotion/tension it creates in the reader]
Risk: [what makes this angle weak or easy to ignore]
```

State your honest recommendation and why. Wait for user to pick.

---

## Step 3 — Elevate (Optional Sharpening)

Soft step. Not required. One exchange only — don't drag this out.

Based on the chosen angle, suggest 1-2 specific things that could sharpen the post —
a stat, a named example, a known pattern, a source. Be specific about what to look for,
not generic.

The user decides:
- "yes, include it" → flag as ✅ verified or ⚠️ inference and carry into DRAFT
- "keep it first-person" → skip entirely and go to FORMAT
- "find it for me" → only then search

Do NOT search without being asked. Do NOT push for external backing if the
first-person version is already strong.

---

## Step 4 — Format

Default: **single post.** Proceed directly — do not ask for confirmation unless the
user has specified a different format earlier in the conversation.

Formats available:
- Single post (default)
- Contrast post (two-line tension/resolution)
- Number post (opens with a specific result or metric)
- Observation + implication (one line each)

Only after the draft is finalized, offer thread or series options if the content
warrants it — don't raise it before.

---

## Step 5 — Draft (Iterative)

Draft in sequence. Never the full post at once.

1. **Hook** — present, get approval or iterate
2. **Body** — present, get approval or iterate
3. **Close** — present, get approval or iterate
4. **Full assembled post** — final review

When presenting alternatives at any step:
- Give 2-3 options with a one-line note on what tension mechanism each uses
- State your honest recommendation
- Never rewrite the full post unless asked — if the user flags a specific line,
  improve only that line and present options

**Brand voice:** Apply all rules from the `aksenhq-x-brand-voice` skill when drafting.
Read that skill before generating any post content.

---

## Iteration Rules

- Never rewrite the full post unless asked
- User flags a specific line → improve only that line, present 2-3 options
- If a closing line restates what the post already showed, cut it
- If the post is trying to say two things, pick one
- If the hook doesn't pass the Veritasium test (tension first, not answer first),
  rewrite the hook before anything else

---

## Content Types Reference

| Type | When to use |
|------|-------------|
| The Observation | Something noticed in daily work — no data needed, first-person authority |
| The Receipt | Actual number, result, or outcome from building — highest trust signal |
| The Reframe | Common assumption + what's actually true — contrast-driven |
| The Mechanism | Here's how X actually works — decoded from lived experience |
| The Pattern | This specific thing is a case of a broader unnamed thing |

Pick the type that fits the anchored angle naturally — don't force it.
