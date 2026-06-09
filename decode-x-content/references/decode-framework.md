# decode-framework — the "answers" to learn from each piece of X content

Read this before Step 3 (decode). It defines the metric that matters, the six decode
levels, how deep to go per content type, the archetype taxonomy, and how to aggregate a
corpus. The atomic decode is one item; the schema is `scripts/decode_schema.json`.

---

## 1. The metric that matters: saves, not likes

X ranking weights a **bookmark ~10× a like** (a like is ~0.5, a bookmark ~10 in the
surfaced weights). So raw likes mislead. Decode for **save-worthiness**:

- **bm:like** = bookmarks / likes — the single best "what works" signal.
- **bm/1k-views** = bookmarks per 1000 views — reach-normalized save rate (compares a 60M-view
  post to a 800K-view post fairly).
- **reach** = views relative to the account's follower count — did the algorithm push it cold.

**Reading the bands (calibrate against the corpus, not these defaults):**

| bm:like | What it usually means | Replicate for |
|---|---|---|
| **≥ 0.8** | pure reference/utility — people file it to use later | tutorials, product demos, how-to |
| **0.4 – 0.8** | save-worthy news/proof — saved as evidence/ammunition | demos, news-explainers, before/after |
| **0.15 – 0.4** | mixed — interesting but mostly consumed | hot-takes, curation |
| **< 0.15** | funny/relatable — liked, rarely saved | humor, memes, reach-bait |

High reach + low bm:like = a *like* machine (humor), not a *save* machine. Both can be
goals — but say which one each post is, and never confuse a 40M-view joke for a teaching format.

## 2. Grounding rule (non-negotiable)

**Compute "typical" from the actual corpus. Never invent benchmarks.** A capable agent will
confidently assert "bookmarks usually run 5–15% of likes" — that is a hallucinated prior.
Instead: pool the dataset's bm:like values, take the median and quartiles, and judge each
post against *that distribution*. Every comparative claim ("unusually high saves") must trace
to a number you computed from the data in front of you.

## 3. The six decode levels

Answer each as deep as the input allows. Stamp `n/a (no audio)` / `n/a (no video)` for what
you cannot reach — a gap is a finding, never something to fabricate.

- **L1 · post text** — what the tweet copy does (hook type, claim, in-group signal, CTA).
- **L2 · transcript** — the spoken content (Whisper). What's actually said, VO vs dialogue, word count, pitch vs story. *Whisper emits filler ("you", "thank you", "[Music]") on non-speech audio — a transcript that is only repeated filler means music-only / no VO, not a failed run.*
- **L3 · captions** — on-screen text / burned captions / labels ("Prompt:", numbered steps). Often the real driver of saves.
- **L4 · visual** — what the keyframe contact sheet shows: UI screen-rec vs talking head vs b-roll vs broadcast; polish; watermark; aspect.
- **L5 · why it works** — synthesis: *why does this earn the saves/reach it got, for the metric that matters?* The causal claim.
- **L6 · timing** — was posting strategized around a launch/news? **Web-verify** (WebSearch) the relevant announcement date and compare to the post date; cite the source. "Rode the Opus 4.8 launch (posted +1 day)" beats "good timing."

## 4. Depth profile by content type

Detect the type from the input, then go as deep as it allows:

| content_type | Levels reached | Pipeline |
|---|---|---|
| **video** | L1–L6 (full) | `fetch_media.sh` → `make_media.py` (wav + contact sheet) → `transcribe.sh`; you read the sheet (L4) + transcript (L2) |
| **text-post** | L1, L5, L6 + archetype | none — pure text + metrics + timing |
| **link-article** | L1, L5, L6 + the linked thing | `WebFetch` the URL; decode the article's framing + why it was worth sharing |
| **quote-repost** | borrowed content + quoter's spin | decode the inner content as its type allows; L5 = what the quoter's framing adds |

A **silent screen-recording** (no audio stream) is one of the strongest product/tutorial
formats — `has_audio:false` is a key signal, not a failure.

## 5. Archetype taxonomy (seed — extensible)

Classify every item into a named archetype so decodes aggregate. These six emerged from the
pilot; **coin a new archetype when the data demands it** (the list is open):

1. **official product demo (silent screen-rec)** — polished UI screen-rec + captions, music or no audio. High saves. (e.g. Claude Design 80.8K bm)
2. **tutorial / how-to (silent terminal screen-rec)** — real terminal, numbered steps, "do this". Highest bm:like (~1.0). (e.g. ultracode tip)
3. **relatable overkill humor (visual metaphor)** — absurd metaphor for everyday AI use. Huge reach, low bm:like (~0.13). (e.g. blowtorch-to-rename-a-file 40M views)
4. **AI demo/news with before-after proof** — split-screen "look what AI can do" + on-screen prompts. Mid saves. (e.g. fake-crowd 0.39)
5. **drama-hook → product promo (mismatch)** — clickbait "BREAKING…" hook into a polished promo + giveaway CTA. Inflated bm:like via CTA.
6. **borrowed-authority news-explainer** — repurposed broadcast (CNN chyron) + VO over an alarming claim. Saved as "proof". (e.g. Microsoft-banned-AI 12K bm)
7. **curation of long-form** — "watch this instead of Netflix" reshare of a 1–2hr talk. Bookmark magnet (people save to watch later). (e.g. Stanford lecture 79.7K bm)

For each: name the archetype, its hook pattern, its typical bm:like band, and one corpus example.

## 6. Corpus tiering (so a whole dataset is tractable)

Decoding 130+ items at full depth is wasteful. Tier by value:

- **Tier 1 — all items, cheap:** L1 (post text) + metrics + bm:like + L6 timing (light) + archetype, straight from the scraped record (`<handle>/tweets.jsonl`: `text, datetime, video_duration_sec, video_aspect_ratio, metrics{}`). No download. This alone answers "what's working overall."
- **Tier 2 — full A/V, prioritized:** download + transcribe + keyframe-read only the **top items by bookmark-weighted score, spread across archetypes** (don't deep-dive five of the same). The pilot's 8 are already done — extend, don't repeat.
- **Long-form (>~10 min) reshares:** hook + curation archetype only — never transcribe a 104-min lecture for marginal signal; the *hook + the act of curation* is the lesson.

Drive a large run with a **Workflow** (`pipeline` per item: enrich → decode), with Tier-2's
heavy media work gated to the prioritized subset. Log what you tiered out — never imply full
depth on items that only got Tier 1.

## 7. Aggregate → what's working

After per-item decodes:

1. **Cluster by archetype**; per cluster compute median bm:like, bm/1k-views, reach, and count.
2. **Rank** items and archetypes by bookmark-weighted score (`bm*10 + lk*0.5`, or bm/1k-views for fairness across reach).
3. **Partition by each content axis** — format, archetype, has-audio, duration band, hook type, aspect, topic, account tier — and report how each value performs (this drives the HTML partition-plan view; see `outputs.md`).
4. **Surface the deltas:** what consistently wins saves, what only wins likes, what underperforms. These become the playbook do's/don'ts.

## 8. Honesty & evidence

Every decode carries auditable evidence: the contact-sheet path, the transcript path, and the
web sources for timing. Comparative claims trace to computed corpus numbers. Unreachable
layers are stamped `n/a`. A decode you cannot back with an artifact is marked unverified.
