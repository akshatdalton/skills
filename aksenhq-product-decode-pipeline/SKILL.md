---
name: aksenhq-product-decode-pipeline
description: >
  Runs the full BFS product deconstruction pipeline for @aksenHQ content creation on X.
  Use this skill whenever the user wants to decode a product decision, build a post about
  a product, says "let's work on [product]", "help me decode [product]", "suggest a product
  to write about", "let's build content", or shares any product + decision context and wants
  to turn it into X content. Also triggers when the user wants to continue a previous
  decode session or pick up where they left off. Always use this skill for any @aksenHQ
  content creation task that starts from a product — do not skip it.
---

# @aksenHQ Product Decode Pipeline

## Purpose

Run the BFS (breadth-first search) product deconstruction workflow that turns a product
pick into a publish-ready X post. User drives. Claude navigates.

**Core principle:**
```
surface all decisions first (breadth)
→ deep dive one node (depth)
→ verify sources before writing
→ traverse back to draft iteratively
```

Never skip steps. Never jump to drafting. Always show pipeline state before moving forward.

---

## Pipeline

```
PICK A PRODUCT → MAP DECISION TERRITORY → ANCHOR DECISION → CONTENT MEAT → FORMAT → DRAFT
```

Always show the full pipeline with a position marker at each transition:
```
PICK ✅ → MAP ✅ → ANCHOR ← we are here → MEAT → FORMAT → DRAFT
```

---

## Step 0 — Product Pick

**If user has already picked:** skip to Step 1 immediately. Always start from MAP —
assume nothing has been done on the pipeline.

**If user asks for a suggestion:**
- Check memory for the decoded products tracker first — suggest from the not-yet-decoded list
- Use `recent_chats` / `conversation_search` to check if any were partially started
- Present 2-3 options with a one-line tension for each
- State which you'd pick and why (tension clarity + source availability)
- Wait for user confirmation before proceeding

**Guiding questions at this step:**
- Am I starting from a product I already use and noticed something odd?
- Or going source-first (founder interview, HN thread) and letting it surface the product?
- Does this fall in the territory? (Productivity / Dev tools / B2B SaaS / Consumer / Failures)
- Is there a real strategic bet here or just a feature I find interesting?

**Product territory (reference):**
- Productivity/Workspace: Notion, Linear, Superhuman, Obsidian, Raycast
- Dev tools gone mainstream: Figma, Cursor, Vercel, Supabase, GitHub
- B2B SaaS that grew weird: Calendly, Loom, Typeform, Airtable, Intercom
- Consumer: Duolingo, Spotify, Bumble
- Failures: Clubhouse, Quibi, Google+, Path, BeReal

---

## Step 1 — Map Decision Territory (Breadth)

Surface ALL decisions worth decoding for this product — not just the obvious one.

**Decision categories (scaffold — not a closed list):**
These are starting prompts. If the product has unusual bets that don't fit, add new
categories. The list should expand dynamically based on what the product actually did.

- Pricing — what they charged, how they picked it, who it filtered
- Distribution — how it spread, what channels they bet on or avoided
- Feature absence — what they deliberately didn't build
- Onboarding — manual vs. automated, who they let in
- Positioning — who they said it was for, who they ignored
- Timing — why they launched when they did, or waited
- Failure modes — what broke, what the market rejected
- [Any other category the product's specific story demands]

**For each decision, output this card:**
```
Decision N — [Name]
Surface story: [what it looks like from the outside]
Non-obvious bet: [what was actually going on strategically]
Tension sentence: [one sentence — "this is surprising because..."]
Source available: [yes / need to search / unknown]
```

The tension sentence IS the tension test — it's inline per decision, not a separate gate.
Present all decision cards at once (breadth). Do not pick one yet.
Let the user choose which node to go deep on.

**Guiding questions:**
- Which content type fits this decision? (see Content Types Reference below)
- Is the tension about a win or a failure? Pick one angle — don't combine.
- Is there a real source that confirms this, or is it inference?

---

## Step 2 — Anchor Decision (Depth)

User has picked a decision. Now go deep.

**Pull sources before expanding.** Use web search to find:
- Founder interviews: First Round, a16z, Lenny's Newsletter, Acquired podcast
- HN threads, old blog posts, earnings calls
- Direct quotes from the founder on this specific decision

**Present sourced claims with URLs inline — not after drafting.** Flag explicitly:
- ✅ Verified — direct from source
- ⚠️ Synthesis — our framing, grounded in sources but not a direct quote

Correct any wrong priors from Step 1 here. If the tension sentence needs updating based
on what sources actually say, surface it before writing.

**Guiding questions:**
- Does the source confirm the bet, add texture, or contradict our framing?
- If no source confirms it — keep looking before writing
- Does the real story make the tension sharper or weaker? Adjust accordingly.

---

## Step 3 — Content Meat

Before drafting, align on what goes into the post.

Present the full content architecture:
```
Hook beat      — the tension/contradiction that opens it
Evidence layer — sourced claims that make it credible
Mechanism      — how it actually worked (the decode)
Zoom-out       — the underlying constraint or insight
Takeaway       — what a builder does with this
```

Discuss each beat. Let the user add, cut, or reframe before anything is written.
If the user has a sharper angle or framing, use it.

Do NOT draft yet. Only proceed after user approves the architecture.

**Guiding question:**
- What does the audience walk away knowing? A builder's insight they can think with —
  not a fact they already knew.

---

## Step 4 — Format Decision

Format follows substance. Default: **single post, small-medium size.**

Only after single post is finalized, discuss:
- Thread (3-5 tweets)
- Quote-tweet continuation
- Series connection (link to past or future decodes)

**Media suggestion (after draft is finalized, not during):**
Suggest relevant media that could strengthen the post at publish time:
- Reddit thread screenshot where real users debate the exact decision
- Source article / founder interview screenshot
- Chart or stat that makes an abstract claim concrete
- Before/after product screenshot if the decision was a UI/feature bet

Media is a publishing decision, not a drafting decision.

---

## Step 5 — Draft (Iterative)

Draft hook → body → close. Never the full post in one shot.

1. Hook — present, get approval or iterate
2. Body — present, get approval or iterate
3. Close — present, get approval or iterate
4. Full assembled post — final review

**Brand voice rules (from aksenhq-x-brand-voice):**
- Lowercase always (proper nouns excepted)
- No trailing punctuation
- No emojis in body (functional use only)
- Never start with "I"
- Line breaks between thoughts, not periods
- No motivational generics — every line earns its place
- Closing line = the answer, not a label for it

**When presenting alternatives:**
- Give 2-4 options with a one-line note on the tension mechanism each uses
- State your honest recommendation and why

**Fact flags:**
- Any synthesis claim must be flagged — user verifies before approving

---

## Iteration Rules

- Never rewrite the full post unless asked
- User flags a specific line → improve only that line, present options
- Do not ask "do you have a personal data point?" — skip it
- If a closing line restates what the post already showed, cut it

---

## Session Close

After post is finalized:
- Update the decoded products tracker in memory (add to decoded, keep not-decoded current)
- Note which decisions from Step 1 are still unexplored
- Note format expansion options for the next session

---

## Content Types Reference

| Type | What it decodes |
|------|----------------|
| The Decode | The strategic/psychological decision behind a product move |
| The Steal | One thing a solo builder can take from a big product decision |
| The Contrarian | Everyone praises X, but the real story is Y |
| The Autopsy | A product that failed — dissected decision by decision |
| The Numbers | One specific metric that tells the whole strategic story |
| The Timing | Why they launched when they did — or waited |

This list is open. New types should emerge from the content, not be pre-defined.
Pick the type that fits the anchor decision naturally — don't force it.
