---
name: decode-x-content
description: Use when you have X/Twitter content — a video, a transcript, a plain text post, a quoted article, or a whole scraped corpus — and want to know what is actually working and why: which posts get bookmarked/saved and reach, what hooks, captions, formats, and timing drive it, and what to replicate or avoid. Triggers on "why did this go viral on X", "what content works on X", "decode this post/clip", "analyze my X dataset", or building/refreshing the yt-shorts-for-x playbook.
---

# decode-x-content

## Overview

Decode **what content is actually working on X, and why** — then turn it into reusable
do's/don'ts. The atomic unit is one piece of content; the default scale is a **corpus**. It
runs on whatever input you have and **decodes as deep as that input allows** — a video gets
six layers, a bare text post gets two — never faking the layers it cannot see.

**Core principle — the bookmark is the signal.** X ranking weights a bookmark ~10× a like, so
the **bookmark:like ratio** (and bookmarks-per-1k-views), not raw likes, tells you what people
found *save-worthy*. High bm:like = reference/utility/ammunition (replicate for product &
tutorials); high reach + low bm:like = funny/relatable (likes, not saves). Always decode for
the metric that matters.

**Grounding rule — never invent benchmarks.** A capable agent will confidently assert
"bookmarks usually run 5–15% of likes." That is a hallucinated prior. Compute the real bm:like
distribution from the corpus in front of you and judge each post against *that*.

## When to use

- "Why did this clip/post go viral on X?" · "What's working on X right now?"
- "Decode this post" — a URL, an mp4, a transcript, or just the text
- "Analyze the whole scraped dataset for overall insights"
- Building or refreshing the **yt-shorts-for-x** playbook — this skill writes it

**Not for:** producing clips (→ `yt-shorts-for-x`), scraping (→ `scrape-x-profile`), or generic
video summarization (→ `gemini-youtube` MCP).

## Workflow contract — file-based, decoupled

| # | Step | Tool | In → Out |
|---|---|---|---|
| 0 | **Recall** | `brain-recall` (skill) | initiative / playbook / dataset context → warm start |
| 1 | **Ingest + detect** | Claude | URL / mp4 / transcript / text → `content_type` |
| 2 | **Enrich** | Claude | metrics → bm:like, bm/1k-views, post timestamp |
| 3 | **Decode (adaptive depth)** | Claude + `scripts/` | content → per-item decode JSON (6 levels + archetype) |
| 4 | **Aggregate** (corpus) | Claude | decodes → archetype clusters, corpus benchmarks, ranking |
| 5 | **Synthesize** | Claude + `brain-ingest --bg` | patterns → playbook (do's/don'ts + samples) |
| 6 | **Present** | `/onepager` + `/visualize-via-html` | inline catch-up + full visual report |

**REQUIRED REFERENCE — read before Step 3:** `references/decode-framework.md` — the metric that
matters, the six levels, depth-by-content-type, the archetype taxonomy, corpus tiering, aggregation.

**REQUIRED REFERENCE — read before Steps 5–6:** `references/outputs.md` — the playbook format
(with real samples), the `/visualize-via-html` partition-plan view, brain-ingest registration.

## Decode depth by content type (summary)

| content_type | Levels reached | Media pipeline |
|---|---|---|
| **video** | L1–L6 (full) | download → audio + keyframes → transcript → caption/visual read |
| **text-post** | L1, L5, L6 + archetype | none |
| **link-article** | L1, L5, L6 + the linked thing | `WebFetch` the link |
| **quote-repost** | borrowed content + quoter's framing | as the inner content allows |

Missing layers are stamped `n/a (no audio)` / `n/a (no video)`. **A silent screen-rec is a
finding (a top product/tutorial format), not a failure.**

## Media pipeline (deterministic — `scripts/`)

Run `bash scripts/setup.sh` once (verifies yt-dlp, static ffmpeg, whisper-cli + model). Then per video:

```bash
mp4=$(bash scripts/fetch_media.sh <tweet_url> <work>/media)      # yt-dlp + chrome cookies (X needs auth)
python3 scripts/make_media.py "$mp4" <work>/media --frames 6     # 16k wav + keyframe contact sheet
bash scripts/transcribe.sh <work>/media/audio/<tid>.wav          # Meetily whisper-cli large-v3-turbo
```

Then **you** read the contact sheet (L4 visual) and transcript (L2), web-verify timing (L6),
and write the decode (`scripts/decode_schema.json`). `scripts/embed_media.py <sheet>` →
base64 data-URI for the self-contained HTML report. Each script prints its output path and
`--help`/header documents its flags. (Homebrew ffmpeg is broken here — scripts use the static one.)

## Common mistakes (seeded from baseline testing)

| Mistake | Fix |
|---|---|
| Inventing benchmark ratios ("usually 5–15%") | Compute the bm:like distribution from the actual corpus; judge against it |
| Trusting the poster's description of the media | Download + transcribe + read keyframes — decode the **ground truth**, not the claim |
| Faking a layer you can't see | Stamp `n/a (no audio/video)` — it's a real signal |
| Prose-only output that can't aggregate | Emit the decode JSON so N items compose into a corpus view |
| Decoding for likes | Decode for **saves** (bm:like) — what the algorithm and the playbook care about |
| Insights that evaporate | Write the playbook + `brain-ingest --bg`; cite evidence (sheet / transcript / source) |
| Hand-rolling the HTML | Use `/visualize-via-html` (base64-embed sheets to stay self-contained) |

## Corpus / batch

For a whole dataset see `references/decode-framework.md` → "Corpus tiering": **Tier 1**
(text + metrics + timing + archetype) for *every* item cheaply; **Tier 2** (full A/V) for the
top items by bookmark-weighted score, spread across archetypes; long-form reshares get
hook + curation only. Drive large runs with a **Workflow** (pipeline per item). Aggregate →
playbook + partition-plan report. Log what you tiered out — never imply full depth on Tier-1 items.
