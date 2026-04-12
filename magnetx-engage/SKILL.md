---
name: magnetx-engage
description: >
  Personal X growth engagement system for @aksenHQ. Two modes: (1) Daily session
  — reads accounts.json, scrapes recent tweets, ranks top 5 posts to engage with
  today. (2) Reply coach — collaborative loop: decodes tweet, surfaces 2-3 angles
  with drafts, invites human to add specific experience, sharpens draft around
  that input. Wraps aksenhq-x-reply-strategy. Trigger on "/magnetx-engage"
  (daily mode) or "/magnetx-engage <url>" (reply coach mode).
---

# /magnetx-engage Skill

AI co-pilot for consistent, high-intent X engagement. Surfaces targets and thinking, user stays in control of replies.

---

## Core Design Principle

**AI finds targets and angles; human writes the reply.**

This skill surfaces the *what* (which accounts to engage with, what angles to explore) and the *why* (why this post, why this angle is strong). The reply is always yours to write.

---

## Mode 1: Daily Session

**Command:** `/magnetx-engage` (no arguments)

**Purpose:** Morning habit kickstart. Surface 5 posts from your target accounts that are high-intent engagement targets.

### Workflow

1. **Read accounts.json** from `~/.claude/skills/magnetx-engage/accounts.json`
2. **Scrape recent tweets** (last 15 tweets from each account) using the `scrape-x-profile` skill
3. **Calculate per-account metrics:**
   - **Engagement rate** = (likes + replies + retweets) / impressions, averaged across last 15 tweets
   - **Reply-back signal** = % of recent posts where replies > 0 (shows whether account engages back)
   - **Peak posting hour** = most frequent hour in tweet timestamps (UTC)
4. **Rank accounts** by:
   - Engagement rate (higher is better)
   - Reply-back signal (higher is better — accounts that reply back are worth engaging)
   - Recency (newer posts > older posts)
5. **Surface top 5 posts** to engage with:
   - Post text + URL
   - Account info (handle, followers, engagement rate)
   - Why this post (engagement signal + account engagement history)
   - Suggested reply angle (brief 1-line thinking starter, not a draft)

### Output Format

```
🧲 YOUR DAILY ENGAGEMENT TARGETS (5 posts)

---

1. [@handle] — [N followers, [engagement rate]]
   📄 Post: [quote of post text, first 100 chars]
   🔗 [URL to tweet]
   Why: This account has [X%] reply-back rate. Post has [Y] replies (strong signal they engage).
   Angle to explore: [One-line thinking starter, e.g., "the tooling gap they're pointing at"]

[repeat for posts 2-5]

---

⏱️ Account scores: [breakdown of engagement rates used to rank]
```

### Notes

- **Always include the tweet URL** so user can click directly
- **Suggested angle is NOT a draft** — it's a thinking direction, not a reply
- **If an account recently got engagement from @aksenHQ already**, note it (save mental state if possible)
- **Peak posting hours are informational** — useful for scheduling replies if user wants to engage live

---

## Mode 2: Reply Coach

**Command:** `/magnetx-engage <tweet-url>`  
Optional: `/magnetx-engage <tweet-url> @handle` (for quick account context)

**Purpose:** Think partner for crafting thoughtful replies. Surface angles rooted in the Add/Position/Ask framework.

### Workflow

1. **Parse tweet URL** and extract tweet text (via read or manual paste)
2. **Optional: Scrape target account context** (if @handle provided) — last 5 tweets, follower count, recent engagement patterns
3. **Decode the tweet:**
   - What's the real argument (vs. literal words)?
   - What emotional trigger? (validation, outrage, curiosity, aspiration, fear, contrarian satisfaction)
   - What's debatable or missing?
   - Who's the likely audience?
4. **Generate angles** using the 7 angle types (see below)
5. **Map to Add/Position/Ask framework:**
   - **Add** — "I built X, I noticed..." (experience, not opinion)
   - **Position** — "The part that gets overlooked here..." (agree/disagree + reason)
   - **Ask** — One specific genuine question
6. **Rank top 2–3 angles** by engagement potential
7. **Output angles only** — no reply drafts

### The 7 Angle Types

(From `aksenhq-x-reply-strategy` — adapted for MagnetX context)

| Type | Maps to | What it does | Example trigger |
|------|---------|-------------|-----------------|
| **Domain reframe** | Add | Maps tweet insight to your niche (X growth, indie building) | "Building in public works because..." |
| **Personal data point** | Add | Grounds the take in your lived experience — a number, outcome, scenario | "We tried this — here's what happened..." |
| **Mild provocation** | Position | Validates tweet in one clause, then makes it slightly uncomfortable | "True, AND the harder part is..." |
| **Terminology correction** | Position | Redefines a word the tweet used lazily | "This isn't really X, it's Y..." |
| **Question disguised as statement** | Ask | Poses implicit question through observation | "The real question is whether..." |
| **Specific contrast / numbers** | Add | Makes abstract concrete with real comparison or stat | "That's true for [segment], but for [segment]..." |
| **Extrapolated view** | Position | Takes premise, extends it one step further | "Yes, and this pattern shows up in..." |

### Workflow — wraps aksenhq-x-reply-strategy

Mode 2 runs the aksenhq-x-reply-strategy pipeline. Human's specific input comes **before** the draft is generated.

```
DECODE → ANGLES → CONTRIBUTE → DRAFT → LINE EDIT (optional)
```

**Step 1 — Decode (3 lines):**
Real argument / Gap / Reply signal (viral-adjacent | niche | cold + post age). If cold, flag and let user decide.

**Step 2 — Surface 3 angles as directions:**
No drafts. Each angle = 2 lines: angle type + what the move is. End with:
`Pick one (1/2/3) + drop your specific detail — what from your experience makes this real?`

**Step 3 — Draft:**
After user picks + contributes their specific detail. Draft generated with that detail integrated from the first word. Brand voice + humanizer constraints applied inline — not as separate passes. Stress-test embedded in the output.

**Step 4 — Line edit (optional):**
User flags one line → 2-3 alternatives for that line only.

### Output Format — Step 2

```
🎯 [tweet, first 100 chars] | [@handle] | [age] | [signal level]

Real argument: [one line]
Gap: [one line]

1. [Type] — [why this tweet unlocks it]
   Direction: [the move]

2. [Type] — [one line]
   Direction: [the move]

3. [Type] — [one line]
   Direction: [the move]

Pick one (1/2/3) + drop your specific detail — what from your experience makes this real?
```

### Output Format — Step 3 (after human contributes)

```
[reply text]

Stress-test: [one flag if any — omit if clean]
```

### Key Constraints

- **No drafts in Step 2** — angles are directions, not output to react to
- **Draft only after human input** — the human's specific detail must come before writing begins
- **3 angles** — depth over breadth
- **Brand voice + humanizer are not separate passes** — applied inside draft generation
- **If tweet has low signal** — flag at Step 1 (cold), let user decide before generating angles

---

## Implementation Notes

### Integrations

- **`scrape-x-profile` skill:** Use to fetch account tweet history (Mode 1 & optional Mode 2 for account context)
- **`aksenhq-x-reply-strategy` skill:** Mode 2 wraps this skill — run it with the tweet URL, apply account context on top
- **`aksenhq-x-brand-voice` rules:** Apply to all drafts (lowercase, no trailing punctuation, builder voice)

### accounts.json Format

```json
{
  "metadata": { "created": "...", "count": 18 },
  "accounts": [
    { "handle": "arvidkahl", "name": "Arvid Kahl", "niche": "...", "reason": "..." },
    ...
  ]
}
```

### Data Sources

- **Tweet scraping:** Use `scrape-x-profile` skill (returns tweet history + engagement metrics)
- **Account context:** Last 5 tweets, follower count, average engagement
- **Engagement metrics:** Calculate from scraped tweet data (likes + replies + retweets)

---

## Habit Integration

This skill is built for a 20-min morning session:

1. Run Mode 1: 5 min to review targets
2. Pick 1 account, 1 post
3. Run Mode 2 if stuck: 2 min to surface angles
4. Write 1 reply: 10 min max
5. Repeat 4 more times (goal: 5 replies)

---

## Post Filtering Rule

Before running Mode 2 on any post, apply this filter. Skip the post if it is:

- **Meme / reaction content** — image-only, joke format, no substantive argument
- **Personal lifestyle** — travel, food, personal milestone unrelated to building/product/growth
- **Off-niche** — topic has no connection to indie building, product, X growth, solopreneurship, or AI tools
- **Retweet without comment** — no original thought to engage with

If a post is filtered out: move to the next account. Do not generate angles for content with no niche relevance — engagement on off-niche posts doesn't compound toward the target audience.

**When in doubt:** ask "would someone who builds indie products care about the argument in this post?" If no, skip.

---

## What NOT to Do

- Don't generate angles before the human has confirmed the post is worth engaging with
- Don't draft before the human has picked an angle and contributed their specific detail
- Don't rank angles by how clever they sound — rank by authenticity ceiling + reply-back potential
- Don't engage with posts from accounts >100K followers (outside sweet spot)
- Don't generate generic templates — every angle must come from the specific tweet
- Don't surface off-niche posts (see Post Filtering Rule above)

---

## Success Metrics (Personal X Growth Phase)

- Mode 1: User engages with ≥1 suggested post per session
- Mode 2: User reports "angles felt specific to the tweet, not generic"
- Habit: 5 replies per session × 5 days/week = 25 replies/week
- Outcome: Follower growth + reply-back rate tracked in weekly Notion value receipt
