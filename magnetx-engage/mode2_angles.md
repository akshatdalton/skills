# Mode 2: Reply Coach — Angle Generation Logic

## Workflow (Executed by Claude)

When user calls `/magnetx-engage <tweet-url>`:

### Step 1: Parse & Decode the Tweet

Extract:
1. **Real argument** vs literal words
2. **Emotional trigger** (validation, outrage, curiosity, aspiration, fear, contrarian)
3. **What's debatable/missing**
4. **Distribution potential** (viral-adjacent, niche signal, cold)
5. **Likely audience**

### Step 2: Generate 7 Angles

For each of the 7 types below, generate:
- **Why this tweet unlocks it:** (one line)
- **Angle:** (thinking direction, not a draft)
- **Maps to:** (Add/Position/Ask framework)

#### Angle Type 1: Domain Reframe
- **Maps to:** Add
- **What it does:** Maps the tweet's insight to your niche (X growth, indie building)
- **Trigger:** Direct structural parallel exists

#### Angle Type 2: Personal Data Point
- **Maps to:** Add
- **What it does:** Grounds the take in your lived experience
- **Trigger:** Tweet makes general claim you can make specific

#### Angle Type 3: Mild Provocation
- **Maps to:** Position
- **What it does:** Validates in one clause, then makes slightly uncomfortable
- **Trigger:** Tweet is right but incomplete — sharper version exists

#### Angle Type 4: Terminology Correction
- **Maps to:** Position
- **What it does:** Redefines a word or phrase the tweet used loosely
- **Trigger:** Tweet's framing is doing unnecessary work

#### Angle Type 5: Question Disguised as Statement
- **Maps to:** Ask
- **What it does:** Poses implicit question through declarative observation
- **Trigger:** Tweet leaves obvious gap people want to fill

#### Angle Type 6: Specific Contrast / Numbers
- **Maps to:** Add
- **What it does:** Makes abstract concrete with real comparison or stat
- **Trigger:** Tweet is vibes-only, a number lands harder

#### Angle Type 7: Extrapolated View
- **Maps to:** Position
- **What it does:** Takes premise, extends one step further into different domain
- **Trigger:** Tweet is right as far as it goes, but more interesting truth hiding behind

### Step 3: Rank by Engagement Potential

Score each angle on:
- **Impression potential** — stops a scroll? creates tension?
- **Reply-bait** — invites response, pushback, question?
- **Brand fit** — reinforces @aksenHQ positioning (builder, practitioner, solopreneur)?
- **Authenticity ceiling** — can be backed with real experience?

### Step 4: Surface Top 2–3 Angles

Output only the ranked angles, NEVER drafts.

## Output Format

```
🎯 REPLY ANGLES FOR [TWEET]

Tweet: "[quote, first 150 chars]"
Account: [@handle] — [follower count] followers
Audience signal: [type of person likely to engage]

---

🥇 TOP ANGLE — [Type]
Maps to: [Add/Position/Ask]
Why this tweet unlocks it: [one line]
Angle: [thinking direction — one sentence]
Why it works: [one line — engagement mechanic]
Authenticity check: [honest concern — does this feel real for you?]

---

2. [Type] — [one-line summary]
Maps to: [Add/Position/Ask]
Angle: [thinking direction]

3. [Type] — [one-line summary]
Maps to: [Add/Position/Ask]
Angle: [thinking direction]

---

💡 Next step: Pick an angle, add your specific data point, write 2 min max.
```

## Key Constraints

- **NEVER output a drafted reply** — angles are thinking fodder only
- **Maximum 3 angles** — depth over breadth
- **Apply aksenhq brand voice** (lowercase, no fluff, builder voice)
- **Authenticity check every top angle** — can you back this with real experience?
- **If tweet has low signal** → flag it: "this tweet has low engagement upside"

## Integration with aksenhq-x-reply-strategy

This mode reuses the 7 angle types from aksenhq-x-reply-strategy but:
- Stops BEFORE draft generation
- Maps each angle to Add/Position/Ask framework
- Surfaces angles as thinking fuel, not finished replies

## Implementation Notes

When implementing this in Claude:

1. Use `aksenhq-x-reply-strategy` Stage 1 (Decode) to deeply read the tweet
2. Generate angles using the 7 types — adapt descriptions for @aksenHQ context
3. Apply stress-test: does this angle feel authentic for you?
4. Rank top 2–3 only
5. Output ONLY angles (no replies, no samples, no next steps beyond "go write it")
