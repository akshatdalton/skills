# outputs — playbook, one-pager, and the HTML partition-plan report

Read this before Steps 5–6. Three outputs, each via its own skill — this skill never
reinvents them:

1. **Shared playbook** (persisted to the brain) — the durable do's/don'ts with real samples.
2. **`/onepager`** — the inline catch-up (per item, or the corpus summary).
3. **`/visualize-via-html`** — the full visual report, including the partition-plan view.

---

## 1. The shared playbook (the point of the whole exercise)

The playbook is what turns decodes into reusable guidance for **`yt-shorts-for-x`** (and any
X content work). It is data → product takeaways.

**Canonical location:** `~/opensource/vault/wiki/projects/magnetx/initiatives/yt-shorts-research/playbook.md`
Persist it via **`brain-ingest --bg`** so it lands in the brain and survives across sessions.
`yt-shorts-for-x` Step 04 (classify + rank) can read it from this path.

**It must be do's-and-don'ts with EVIDENCE, not abstractions.** The user's explicit ask:
attach the *samples themselves* so the producer skill has concrete patterns to imitate.

Structure:

```
# What's working on X — playbook (updated <date>, n=<corpus size>)

## The one rule
Decode for saves (bookmarks), not likes. <corpus median bm:like> is the baseline.

## Archetypes that win saves   (ranked by bm:like)
For each: name · bm:like band · when to use · ONE linked sample.

## DO — patterns that earn saves          ## DON'T — patterns that only earn likes (or nothing)
- <do>, because <metric>                   - <dont>, because <metric>
  ↳ sample: "<hook/caption verbatim>"        ↳ sample: "<hook verbatim>"  (<bm:like>, <views>)
    (<handle> <tweet_url>, <bm> bm / <lk> lk)

## Sample bank
### Text-post hooks that worked (verbatim, with metrics)
- "<hook text>" — <handle>, <bm:like>, <views>, <tweet_url>
### Caption / on-screen-text patterns (for video)
- "<caption>" — <archetype>, <tweet_url>
### Video examples (what actually works, by archetype)
- <archetype>: <one-line what-it-does> — <tweet_url> · contact-sheet: <path> · <bm:like>
```

**Attach the sample, not a paraphrase.** For text → the verbatim hook/caption + its metrics +
the tweet URL. For video → the archetype + a one-line "what it does" + the **contact-sheet path**
(local evidence) + the tweet URL + bm:like. The producer skill learns "people save THIS kind of
thing at THIS metric," which is exactly the do/don't signal it needs.

## 2. `/onepager` — inline catch-up

Invoke the **onepager** skill. Driver altitude. For a single item: the decode in one screen.
For a corpus: the headline (what's winning saves), the archetype ranking, and the playbook
delta. Receipts (decodes.json, report path, playbook path) go in the Done block as
absolute-path links. Inline by default; hand off to `/visualize-via-html` on `--html` or for
the full corpus report.

## 3. `/visualize-via-html` — the full visual report

Invoke the **visualize-via-html** skill (do not hand-roll HTML). It owns the styling
(Anthropic palette; dark is a fair override for a dense report), stable section `id`s, the
inline feedback widget, and the `~/.claude/html-artifacts/<slug>/index.html` home.

**Self-contained constraint:** zero external requests. Contact sheets must be **inlined as
base64 data-URIs** — run `python3 scripts/embed_media.py <sheet.jpg> ...` and drop the
data-URI into an `<img src="…">`. (This is the only job left from the old build_report.py.)

### The partition-plan view (required section)

The user wants to *see the content space partitioned by axis and how each partition performs* —
"what axes content is created on, and what they score on each axis." Build this as a first-class
section, `id="partition-plan"`:

- **Axes to partition by:** archetype · format (screen-rec / talking-head / b-roll / broadcast /
  metaphor) · has-audio (silent vs voiced) · duration band (<15s / 15–45s / 45–140s / long-form) ·
  aspect (9:16 / 4:5 / 1:1 / 16:9) · hook type (alarm / how-to / drama / flex / news) · topic ·
  account tier (official / creator).
- **Per axis:** show each value with its **median bm:like**, **bm/1k-views**, **reach**, and
  **n** — a small-multiples row of bars per axis, so the eye lands on where the winners cluster.
- **One 2-D heatmap:** archetype (rows) × format or duration-band (cols), cells colored by
  bookmark-weighted score — the "where does save-worthy content live" map.
- Keep it visual (bars, heatmap cells, color), not tables of numbers. Each value links/anchors
  to its exemplar decode card.

Also include: a **headline** (the one rule), **archetype cards** (hook · bm:like · the contact
sheet · why), and a **do/don't** panel mirroring the playbook. Give every section a stable `id`.

Surface on completion with both the path and a `file://` URL.

## 4. Register the run

After writing the playbook + report, fire **`brain-ingest --bg`** (background launcher,
`--resume "$CLAUDE_CODE_SESSION_ID"`) so the initiative's learnings/decisions capture what this
run found. Never block on it.
