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

**Purpose:** Morning habit kickstart. Surface 5 posts from your target accounts that are high-intent engagement targets for immediate reply.

### Critical: Reply Within the First 1-2 Hours

Replies to posts older than 2 hours have near-zero distribution value. The goal is to reply while the post still has momentum — algorithmic and social. **Recency is the primary filter.**

### Preferred Approach: Live Timeline Scan

Scan the X home timeline directly for fresh posts from target accounts rather than scraping profiles (which surfaces posts from days ago).

**Step 1 — Open X timeline**

Navigate to x.com/home in Chrome. The timeline will contain posts from accounts the user follows. Most of these will be from niche-relevant accounts.

**Step 2 — Extract posts from timeline (JS injection)**

Use `javascript_tool` to extract tweet articles from the DOM. For each tweet:
- Extract: text, handle, timestamp (datetime attribute), likes, replies, retweets, URL
- Filter ads: tweet articles with no datetime attribute are ads — skip them
- Deduplicate using a seen Set on tweet IDs

Scroll the timeline 2-3 times to load more posts. Re-run extraction after each scroll.

**Step 3 — Filter by recency**

Keep only posts posted within the last 2 hours. Discard everything older.

**Step 4 — Cross-reference accounts.json**

From the fresh posts, prioritize handles that appear in `~/.claude/skills/magnetx-engage/accounts.json`. Non-list accounts can be included if they're niche-relevant (builder/founder/product/AI/X growth topics).

**Step 5 — Cross-reference surfaced_log.json**

Check `~/.claude/skills/magnetx-engage/surfaced_log.json`. Skip any tweet IDs or handles already in `surfaced_posts` or `replied_posts`.

**Step 6 — Score and rank fresh posts**

For each qualifying post:
- **Engagement rate** = `(likes + replies + retweets) / max(views, 1)` (if views available)
- **Reply count signal** = replies > 0 → shows tweet is sparking conversation
- **Recency bonus** = posts under 30 min score higher than 30–120 min

**Step 7 — Surface top 5 posts**

Apply **Post Filtering Rule** (see below) — skip memes, off-niche, no-argument content.
Stop when 5 qualifying posts found.

**Step 8 — Output**

Format and display using the output format below.

### Fallback: Profile Scrape (if timeline is sparse)

If the timeline yields fewer than 5 qualifying posts (e.g., off-peak hours, no activity), fall back to profile scraping:

For each account in accounts.json, invoke `/scrape-x-profile @{handle} 15`. Same recency filter applies — only surface posts from the last 2 hours. If none qualify, skip that account.

> Scraper output format: each tweet has `metrics: { replies, retweets, likes, bookmarks, views }` (nested).

### Output Format

```
🧲 YOUR DAILY ENGAGEMENT TARGETS (5 posts)

---

1. [@handle] — [post age] — [likes/replies/retweets]
   📄 Post: [quote of post text, first 100 chars]
   🔗 [URL to tweet]
   Why: [one-line reason — reply count, engagement signal, niche fit]
   Angle to explore: [One-line thinking direction]

[repeat for posts 2-5]

---

⏱️ Session: [N posts scanned, N qualified, N skipped (logged)]
```

### Notes

- **Always include the tweet URL** — every single time, no exceptions
- **Suggested angle is NOT a draft** — it's a thinking direction, not a reply
- **Refresh timeline between replies** — scroll and re-scan to catch newer posts during the session
- **After surfacing**, proceed directly into Mode 2 for each post the user picks

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

**Step 0 — Search before decode (MANDATORY when tweet references a product, project, or person by name):**
Run WebSearch for `[product/project/person name] + context`. Never decode blind. The @garrytan/GBrain incident: decoded without knowing GBrain was Garry's own open-source personal AI memory system — all 3 angles were wrong. One search would have fixed it.

**Step 1 — Decode + Angles in one output (Steps 1+2 together):**
Output decode block immediately followed by the 3 angles. Do NOT stop after decode and wait. User preference: surface the full picture at once.

Format:
```
Real argument: [one line]
Gap: [one line]
Reply signal: [viral-adjacent | niche | cold] + [post age] + [why worth replying]
🔗 [tweet URL]
```
Then immediately surface 3 angles (directions, not drafts). End with recommended angle + one-line reason.

Cold signal = flag it in the signal line, then continue to angles anyway. Do NOT stop and ask.

**Step 2 — Recommend an angle:**
After surfacing all 3, always state: `Recommended: [1/2/3] — [one-line reason]`. Never make the user ask for a recommendation.

**Step 3 — Draft:**
After user picks + contributes their specific detail.

- 3a: Write draft with detail integrated from the first word. Brand voice applied inline.
- 3b: Run humanizer audit internally before outputting — ask "what makes this obviously AI-generated?" and fix it. Check: uniform rhythm, em dashes, abstract closers, slogan parallelism, transitional overload. Only show the reply after it passes.
- 3c: Stress-test (overclaiming / too closed / generic / false parallel). Note any flag in one line after the draft.

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
