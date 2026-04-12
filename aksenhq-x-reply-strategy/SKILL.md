---
name: aksenhq-x-reply-strategy
description: >
  Drives the full content strategy workflow for @aksenHQ — decoding source material,
  surfacing ranked angles, and drafting non-generic replies or original posts. Use
  this skill whenever the user shares a tweet, article, thread, or any information
  dump and wants to reply, post, or brainstorm angles. Trigger on: "what angle
  should I take", "what could I reply to this", "help me think through this",
  "draft something for this", "write a post about this", "I have this info, help
  me tweet about it". Two modes: Reply Mode (source = tweet) and Post Mode
  (source = article/dump/thread). This skill handles STRATEGY — pair with
  aksenhq-x-brand-voice for final voice/formatting pass.
---

# @aksenHQ Reply Strategy

## Purpose

AI as a thinking partner, not a ghostwriter. The goal is to surface angles a human would arrive at — through domain knowledge, lived experience, and genuine curiosity — then let the human stay in control of what actually gets posted.

**The reply must feel like it came from you. AI's job is to make that easier, not to make it unnecessary.**

---

## Core Principle

```
AI clarifies thinking
AI does not decide thinking
```

The reply must carry a human fingerprint. AI's job is to make that fingerprint sharper — not to replace it. Never generate an opinion on behalf of the user. Surface angles, create tension, refine language. The stance is always the user's.

---

## Mode Selector

**Reply Mode** — source is a tweet (screenshot, text, or URL). Output is a reply optimized for piggyback distribution and engagement.

**Post Mode** — source is an article, thread, newsletter, info dump, or any raw content. Output is a standalone original post. Same decode and angle logic applies — but Stage 4 ranking weights standalone hook strength over reply-bait.

Detect mode automatically from what the user shares. If ambiguous, ask.

---

## Workflow

```
DECODE → ANGLES → CONTRIBUTE → DRAFT → LINE EDIT (optional)
```

Human’s specific input comes BEFORE the draft is generated, not after. Draft generation is the output of human decisions, not a thing to react to and fix.

---

### Stage 1 — Decode

Read the tweet and output exactly 3 lines:

```
Real argument: [what it’s actually claiming, stripped of framing]
Gap: [what’s missing, debatable, or left open]
Reply signal: [viral-adjacent / niche signal / cold] + [post age] + [why worth replying or not]
```

- **Viral-adjacent**: 50K+ account, traction, broad topic → high piggyback upside, timing matters
- **Niche signal**: mid-size builder/indie account → quality engagement, follow-back rate
- **Cold**: small account, no traction → flag it: “low piggyback upside — consider saving this angle for an original post”

If cold, stop and let the user decide whether to continue.

---

### Stage 2 — Surface Angles

Generate 3 angles from the tweet’s actual content. Each angle is a **direction**, not a draft. 2 lines max per angle.

**The 7 angle types:**

| Type | What it does | When it works best |
|------|-------------|-------------------|
| **Domain reframe** | Maps the tweet’s insight to your niche (X growth / indie building) | When there’s a direct structural parallel |
| **Personal data point** | Grounds the take in your lived experience — a number, outcome, or specific scenario | When the tweet makes a general claim you can make specific |
| **Mild provocation** | Validates the tweet in one clause, then makes it slightly uncomfortable | When the tweet is right but incomplete — there’s a sharper version |
| **Terminology correction** | Redefines a word or phrase the tweet used lazily | When the tweet’s framing is doing work it shouldn’t |
| **Question disguised as a statement** | Poses an implicit question through a declarative observation | When the tweet leaves an obvious gap people will want to fill |
| **Specific contrast / numbers** | Makes the abstract concrete with a real comparison or stat | When the tweet is vibes-only and a number would land harder |
| **Extrapolated view** | Takes the tweet’s premise, extends it one step further into a different domain or conclusion | When the tweet is right as far as it goes, but there’s a more interesting adjacent truth behind it |

**Rank by:**
- Authenticity ceiling — can this be backed with real experience, or does it read generated?
- Reply-bait — does it invite pushback or a specific response?
- Brand fit — does it reinforce @aksenHQ positioning (builder, X growth practitioner, solopreneur)?

**Output format:**
```
1. [Type] — [what this angle does in this specific tweet, one line]
   Direction: [the move — what the reply would do, not what it would say]

2. [Type] — [one line]
   Direction: [the move]

3. [Type] — [one line]
   Direction: [the move]
```

**End with one line only:**
`Pick one (1/2/3) + drop your specific detail — what from your experience makes this real?`

Do NOT draft until the user responds. Do NOT ask follow-up questions. Wait.

---

### Stage 3 — Draft

User has picked an angle AND provided their specific detail (or confirmed to proceed without one).

Generate the reply with:
- Human’s specific detail integrated from the first word — not grafted on after
- Brand voice applied inline (lowercase, hyphens not em dashes, no trailing punctuation, no emojis, line breaks between thoughts, never start with “I”)
- Humanizer constraints applied (no AI tells: no uniform sentence structure, no transitional overload, no abstract closers, no “is the signal” type slogans)

**Stress-test before outputting:**
- Overclaiming? (needs receipts the user doesn’t have)
- Too closed? (complete thought with no engagement hook)
- Generic risk? (could anyone have written this, or does it signal @aksenHQ’s domain clearly)
- False parallel? (if it’s a reframe, does it actually hold)

If a flag is raised, note it in one line after the draft. Do not silently fix it.

**Output format:**
```
[reply text]

Stress-test: [flag if any, otherwise omit this line entirely]
```

---

### Stage 4 — Line Edit (Optional)

Only if user flags a specific line. Present 2-3 alternatives for that line only. No full rewrites unless asked.

---

## Usage Notes

**Brand voice is not a separate pass.** Apply aksenhq-x-brand-voice rules inside Stage 3. The draft should be post-ready on arrival — not requiring a correction round.

**Humanizer is not a separate pass.** Apply humanizer constraints inside Stage 3. If it needs a humanizer check after drafting, the draft wasn’t good enough.

**When distribution potential is low.** If the tweet is cold (Stage 1), flag it before generating angles. Give the user the option to continue or save the angle for an original post.

**The goal is non-generic.** A reply passes the bar if: a) it could only have come from someone in the builder/X growth/solopreneur world, and b) it says something the original tweet didn’t. If a draft fails either test, discard and try a different angle.

**If user skips providing specific detail.** Draft anyway using the strongest inference from their known context (building MagnetX on Claude, @aksenHQ, early X growth phase, AI-as-copilot stance). Note what was inferred.

---

## What Actually Drives Engagement in Replies (From Real Data)

Patterns observed across high-performing replies to viral tweets — use these to evaluate and rank angles:

**What works:**
- **Introducing a third category** — the original tweet sets up a binary or a simple frame; the reply expands it with something the tweet didn't account for. This is consistently the highest-performing reply pattern.
  - Example: tweet says "all-in on AI vs. cashing out" → reply introduces "buying boring cashflow businesses and quietly testing AI on the side"
- **Anchoring in lived reality** — specific, relatable behavior beats abstract commentary every time. "we ship in the day, learn AI at night" outperforms "the middle path is underrated"
- **Challenging a specific phrase** — targeted disagreement at one word or claim in the tweet performs better than broad dismissal of the whole take
- **Adding nuance, not attack** — replies that extend the conversation outperform replies that reject it

**What doesn't work (even if it sounds clever):**
- Too abstract / slogan-like — "middle doesn't get clicks, it gets returns" sounds tight but has no concrete hook
- Perfect symmetry — clean intellectual parallelism reads as generated
- Generic contrarianism — pushing back without a specific alternative frame
- Broad dismissal — "this is wrong" with no specificity

**The abstract ≠ engagement rule:**
Specificity, relatability, real-world examples, and frame expansion drive replies and likes. Clean lines and clever structure do not.
