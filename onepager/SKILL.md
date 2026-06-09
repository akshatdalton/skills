---
name: onepager
description: Use when the user fires `/onepager`, or asks for a "one pager", "tech-executive summary", "tech exec summary", "catch me up", "where are we", "what's done / remaining / next", or a tight scannable status of the work in progress. Produces a self/driver-facing technical one-pager (NOT a manager/business summary) of done · remaining · next, with an auditable artifact link on every claim. Pulls from the current session first; reaches for PR/git/Jira/vault only when the session can't supply or verify a fact. Opt into `/onepager --audit` for the synthesis-first / TTS-friendly variant, or `/onepager --intern` to teach an unfamiliar feature/ticket bottom-up (reader is expert-in-role but new to this area).
---

# /onepager

## Purpose

The user is the driver; you are the assistant catching them up. Produce ONE scannable page — **what's done · what's remaining · what's next** — so they can get the picture without re-reading everything, then act.

This is the **self / tech-operator** one-pager. It is for the person driving the work, not their manager. Surface the few technical details that matter (the blocker, the gotcha, the pending decision) and suppress the rest. End pointing at action.

The first invocation renders the full picture; after that it is **sticky and incremental** — subsequent progress updates stay in this format and show only what changed (see "Sticky mode" below).

**Three consumption modes — default is Done-first; `--audit` is synthesis-first; `--intern` is teach-the-reader:**
- **default** — `/onepager`: fast tactical handoff, Done up top with receipts inline. Best when you're driving on screen and want to glance, verify, act.
- **`--audit`** — `/onepager --audit`: chief-of-staff read. Bottom line → What matters → Decision → Next → Done. Top half is link-free (TTS-clean) so the output survives being read aloud. Best when you're listening, or you need the "what does this all MEAN and what's the call" pass. See [`/onepager --audit` mode](#onepager---audit--synthesis-first-mode) below.
- **`--intern`** — `/onepager --intern`: teach-the-reader, **bottom-up**. Builds understanding from primitives → ideal flow → what happened → verified-vs-open → next, defining every term. Best when you're **expert in your role but new to this feature/ticket** and need to *understand* it, not just get a status (on-call triage on an unfamiliar area; "explain it like I just joined").

**Not this skill:** manager/leadership/business summaries (outcome+implication, stripped tech names, manager action items) → that is `update-epic-note` + the exec-summary pattern. If the user wants a manager-facing summary, say so and stop.

## The two hard rules

These are what make this one-pager different from a generic status report. Get these wrong and the skill failed.

### Rule 1 — Every claim carries an auditable artifact

The user audits your work. Whenever you say something was done, changed, ran, or produced a result, **attach the artifact so they can open it and verify themselves** — inline, right on the claim. Never make an unsourced claim of work.

Artifact = whatever lets them check it:
- file path you edited — link it with an **absolute** target so it opens in the Claude desktop file panel
- PR / commit / issue URL (`https://github.com/.../pull/142`)
- the specific failing CI check (link to the check run, not just "CI is red")
- a run/log/output file path (`/home/ec2-user/runs/ccep-eu-preview.txt`)
- an S3 / uploaded-artifact URL, a worktree path, a dashboard link, a Slack permalink
- the vault progress file, a Jira key

**Every file path MUST be rendered as a markdown link whose target is an ABSOLUTE path.** Never write a file path as bare text or as an inline-code span (`` `src/foo.rs` ``) — those are not clickable, so the user opens *nothing*. The user clicks these in the Claude desktop file panel, which cannot resolve a relative path either. The display label may stay short and readable; only the link target must be absolute.

- ✅ `[src/headless_rec.rs](/Users/akshat.v/opensource/meetily/src/headless_rec.rs)` — short label, absolute target
- ❌ `` `src/headless_rec.rs` `` — inline code, not a link, opens nothing
- ❌ `[src/headless_rec.rs](src/headless_rec.rs)` — relative target, opens nothing
- ❌ `src/headless_rec.rs` — bare text, not a link at all

This applies to EVERY path you mention — files edited, log/output files, scripts, the vault progress file. If it's a path on disk, it's a link with an absolute target.

Resolve the absolute path before writing the link: prepend the repo root / `pwd` (e.g. `git rev-parse --show-toplevel`, or the cwd you edited in) to any relative path. Paths that are already absolute (`/home/...`, `/tmp/...`, `~/...` → expand the `~` to the real home) are used as-is. If you genuinely cannot resolve the absolute path, say "path unresolved" rather than emit a bare or relative path.

If a claim has no artifact, that is a signal: either you didn't actually do/verify it, or you must say "unverified — no artifact" out loud. Do not silently drop the citation.

(`--audit` mode amends this rule for the top half of the page — see the `--audit` section.)

### Rule 2 — Driver altitude, not manager altitude

Write for the operator who will act next, not for a stakeholder being briefed.

- ✅ Keep tech names, file paths, the actual blocker, the actual decision.
- ❌ No "Business impact", "Outcome / implication", "Audience: exec" framing. That is the wrong skill.
- Pick the **details that matter** — the 20% the user should focus on. Not vague ("some cleanup remains"), not exhaustive (every micro-step). The consequential thing: what's blocking, what changed, what needs their judgment.

## Source priority (provenance)

Pull in this order; stop as soon as the fact is covered and verifiable:

1. **Current session** — the live work thread is the primary source. Summarize what actually happened here.
2. **The thing under discussion** — if a ticket/PR/URL/path is in scope or passed as an arg, read it (PR diff & checks, git log, Jira) to fill or *verify* what the session asserts.
3. **Vault brain** — only when the session is thin or you need older context: `brain-recall` (`progress/<ticket>/progress.md`, `learnings.md`) and `git log`.

Add one short **provenance line** at the top stating what you drew from and, critically, **what you could not verify this session** (e.g. "couldn't repro upload in eu-central-1 — no test env access"). Do not present an unverifiable claim as done.

## Output shape (inline markdown, ~1 screen)

> **FORMATTING CONTRACT (non-negotiable):** every on-disk path is a markdown link `[short label](/absolute/path)`. No bare paths. No inline-code paths (`` `src/foo.rs` ``). If you typed a backtick around a file path, you did it wrong — make it a link with an absolute target.

Default to inline terminal markdown — fast, scannable in under two minutes (BLUF: bottom line first). Structure:

```
# /onepager — <work thread in a few words>
_source: <session / PR#142 / brain-recall> · unverified: <what you couldn't confirm, or "none">_

**Bottom line:** 2–3 sentences. What this thread is, where it stands, the single thing
that matters most right now. Optionally a health word: on-track / at-risk / blocked.

## ✅ Done
- <outcome, not narration> — [<short label>](</absolute/path/or/url>)
- e.g. Headless recorder, no GUI — [src/headless_rec.rs](/Users/akshat.v/opensource/meetily/src/headless_rec.rs) · [commit 0aee2eb](https://github.com/akshatdalton/meetily/commit/0aee2eb)
- ... (3–6 bullets)

## 🔧 Remaining
- <what's left> — <the detail that matters: the blocker / gotcha / dependency> — <artifact if any>
- mark **Blocked** items that need a decision or input from someone else

## → Next
1. <concrete move> (because <why>) — <who: you / me>
2. ... (2–4 actions, ordered, the focus-bringing 20%)

## ⚠️ Watch  (only if real)
- risks, open questions needing the user's judgment, "what changed" / RCA when relevant
```

Drop any section that would be empty (no fake risks). Keep it to one screen — if it overflows, you're including things that don't matter.

### HTML on request only

Default is inline. If the user adds `--html`, says "show me visually / as HTML", or the picture is large enough to benefit from interactivity, hand off to `/visualize-via-html` instead. Otherwise stay inline.

## `/onepager --audit` — synthesis-first mode

The default shape above is the fast tactical handoff: Done up top, receipts inline. There's a second consumption pattern that needs a different shape:

- you're consuming the output **by ear** (TTS / voice mode) and clickable links butcher how the page reads aloud
- you want the **chief-of-staff pass** — what does this all MEAN, what's the actual decision, where should the operator focus — not a what-got-built recap
- you've been away from the thread and need to re-orient before choosing direction

Fire `/onepager --audit` for this. It re-orders the page to **synthesis-first**, splits it into a link-free cognition half and a link-carrying audit half, and dials tone to neutral-flat.

### When the default is wrong and `--audit` is right

| Situation | Mode |
|---|---|
| Driving on screen, want to glance + verify + act | default |
| Reading aloud or voice mode | `--audit` |
| Need the "what does this mean / what's the call" pass | `--audit` |
| Fast incremental handoff after a chunk of work | default |
| Re-orienting after time away | `--audit` |

### Output shape (`--audit`)

> **FORMATTING CONTRACT under `--audit` (in addition to Rule 1):**
> 1. Top half (Bottom line / What matters / The decision) — prose only. NO markdown links, NO file paths, NO URLs, NO bullets.
> 2. Bottom half (Done) — every line still carries an absolute-path artifact link per Rule 1.
> 3. Section headers are sober single words ("Bottom line.", "What matters.", "The decision.", "Next.", "Done.", "Watch.") — no emojis.

Order (Done sinks to the tail — synthesis leads):

```
# /onepager · audit — <work thread in a few words>
_source: <session / PR#142 / brain-recall> · unverified: <what you couldn't confirm, or "none">_

Bottom line.
2–3 sentences. State the picture flat. Optional health word
(on track / at risk / blocked).

What matters.
3–5 sentences of interpretation. What changed in our understanding?
What assumption got validated or invalidated? What is the mental
model the operator should walk away with? No links, no paths,
no bullets. This is the section that gets read aloud — it must
stand on its own as prose.

The decision.   (include ONLY if a real decision is pending — else omit the whole section)
One line naming the call: continue / stop / pivot / scale.
  Option A — <terse> (cost · gain)
  Option B — <terse> (cost · gain)
Recommendation: <which>. Confidence: <low / medium / high — and the hedge driving it>.

Next.
1. <concrete move> (because <why>) — <who: you / me>
2. … (2–4 actions, ordered, the focus-bringing 20%)

Done.
- <outcome> — [<short label>](</absolute/path/or/url>)
- e.g. Headless recorder, no GUI — [src/headless_rec.rs](/Users/akshat.v/opensource/meetily/src/headless_rec.rs)
- … (3–6 bullets)

Watch.   (only if real — risks, open questions needing the user's judgment, "what changed" / RCA)
- <risk / open question / RCA>
```

Drop any section that would be empty (no fake risks, no manufactured decisions). One screen.

### Tone under `--audit` (medium / neutral-flat)

- No section emojis (✅ 🔧 → ⚠️ 🔑) — sober single-word headers instead.
- Sober verbs: delivered · running · blocked on · not yet verified · pending.
- Banned phrases: "the money in one breath", "pipeline proven", "your call", "we crushed it", "in one breath", exclamation marks, "🚀", and similar performative cheer.
- No celebration subheaders. State outcomes flatly.

### Mandatory under `--audit`

- **"What matters" is mandatory and is interpretation** — not a prose restatement of Done. It says what the work TAUGHT, what assumption moved, what the mental model is now.
- **"The decision" is conditional** — include ONLY when one is genuinely pending. When present, it carries options with cost·gain, a recommendation, and a confidence with the hedge driving it.

### Sticky behavior under `--audit`

Once `/onepager --audit` has been fired, sticky mode continues in the audit shape (synthesis-first incremental updates) for the rest of the session. Incremental shape mirrors the baseline; **the lead is interpretation of what the latest chunk TAUGHT** ("What's clearer now"), not narration of what got built.

```
# /onepager · audit update — <thread>  (since last)
_source: <session/PR/…> · unverified: <still-unverified, or "none">_

Since last.
1–2 sentences flat — what actually moved.

What's clearer now.
2–3 sentences of interpretation. What does the latest chunk of work
TEACH us? Not "I built X" — "X confirmed Y" or "X invalidated Y".
What's the updated mental model?

The decision.   (include only if it changed or one just emerged)
<same shape as baseline>

Next (revised).
1. <next move> — <who>

Δ Done.   (incremental receipts, tail — every line still carries an absolute-path link)
+ <new item> — [<label>](</absolute/path/or/url>)
✓ <cleared item>

Watch.   (only if it changed)
- <new or escalated risk>
```

### Red flags under `--audit`

- A link, file path, URL, or bullet appeared in Bottom line / What matters / The decision → STOP, move it to Done.
- "What matters" just restated the Done block in prose → it's not interpretation. Rewrite to say what the work TAUGHT, what assumption moved, what the mental model is now.
- A Decision section appeared but no real decision is pending → manufactured theater. Remove it.
- Uplifting verbs / celebration emojis / "🚀" / "the money in one breath" / "pipeline proven" → flatten. State the outcome.

### Switching modes

- `/onepager` (no flag) → returns to default Done-first shape from the next render onward.
- `/onepager --audit` → switches to audit shape (sticky for the rest of the session).
- `/onepager --intern` → switches to teach-the-reader / bottom-up shape (sticky; see next section).
- `/onepager off` → exits sticky mode entirely (default, audit, or intern).
- `/onepager --html` → render the current state (whichever mode is active) as HTML via `/visualize-via-html`.

## `/onepager --intern` — teach-the-reader / bottom-up mode

The default is a status handoff for someone who already knows the domain. There's a third pattern this skill gets used for constantly in on-call / unfamiliar-feature work: **the reader is expert-in-role but NEW to this feature/ticket** — they know the product only at an overview level and need to *understand* what's going on, not just receive a status. (Born from CS-17128, where the driver had to ask twice for "explain it like I'm an intern, bottom-up" — this mode makes that the default behaviour instead of a correction.)

Fire `/onepager --intern` for this. It **builds understanding from the floor up** before stating the finding, defines every term, and enforces the verify-before-assert discipline visibly.

### When the default is wrong and `--intern` is right

| Situation | Mode |
|---|---|
| You know the domain; want status to glance + act | default |
| Reading aloud / "what's the call" | `--audit` |
| You DON'T know this feature/ticket; need to understand it | `--intern` |
| On-call triage handoff on an unfamiliar product area | `--intern` |
| "Explain this to me like I just joined" | `--intern` |

### Calibrate the reader FIRST (don't guess altitude)
State in the source line what you assume the reader knows and what you do NOT. **Default the floor LOW** (assume they don't know the feature) and pin it there for the session — don't guess high and get corrected twice. This is a startup action, not a styling default.

### Output shape (`--intern`) — bottom-up

> **FORMATTING CONTRACT (in addition to Rule 1):** define every term on first use; **no undefined internal jargon** — table/model/endpoint/namespace names get a plain-words gloss immediately, or stay out. Every load-bearing claim is labeled **observed / inferred / verified** and carries a re-runnable artifact; **never assert presence/absence from a single source**; if not yet grounded, say so and name the query/source that would ground it (don't assert flat).

```
# /onepager · intern — <the thing, in plain words>
_source: <…> · unverified: <…> · altitude: assumes you know <role-level X>, NOT <this feature/ticket>_

**In one line (plain):** what this is + the punchline, zero jargon.

## The setup — what you need to know first
Build from the floor: the entities defined in plain words, then how they relate.
- <term> = <plain definition>   (observed: <artifact>)
- … only the primitives needed to understand the rest

## How it's supposed to work (the ideal / happy path)
- the normal flow in plain words; where the feature in question sits in it

## What actually happened
- the finding, grounded. Label each claim — (verified: <re-runnable artifact>) / (observed: <log/row>) / (inferred: <from what>).
- if it's a code / mechanism story: a file:line TREE showing the path (per the code-trace rule), with the failure / ▶change node marked.

## Verified vs still-open
- ✅ verified — <claim> — [<artifact>](</abs/or/url>)
- ❓ open / inferred — <claim> — the source/query that WOULD settle it (do not assert it flat)

## → Next
1. <concrete move> (because <why>) — <who: you / me>

## To forward — plain + self-validatable   (include whenever this gets shared downstream)
- the jargon-free version a non-expert (CS / customer / another team) can read, AND the link/SQL they can run themselves to confirm. No internal names here.
```

### Tone under `--intern`
Patient teacher. Short sentences. Analogies welcome. Define-then-use. Zero performative cheer. Teach the *why*, and drill into more *why* when it helps. You may offer a teach-back (have the reader restate, or a quick quiz) — **offer, don't force**.

### Mandatory under `--intern`
- **Altitude pinned at the start** (in the source line), not guessed mid-stream.
- **Bottom-up order** — the setup / primitives BEFORE the finding. Never lead with "Done" / status.
- **Every load-bearing claim labeled** observed/inferred/verified + artifact; **verify-before-assert** (≥2 sources for any *absence*; flag the unverified and name the grounding query; pick evidence by fitness-for-claim, not what's open).
- **No undefined jargon** — gloss or omit internal names.
- **"To forward" block** whenever the finding will reach a non-expert downstream (the dual-audience rule).

### Sticky behavior under `--intern`
Once fired, sticky continues in intern shape. Incremental updates lead with **"What's clearer now (plain)"** — what the latest work let you *understand*, in plain words — then Δ verified/open, then next. Not a "what I built" recap.

### Red flags under `--intern`
- Led with Done / status before the reader understands the machine → build up first.
- An undefined internal term (table / model / endpoint name) with no plain gloss → define it or cut it.
- A flat claim with no observed/inferred/verified label or no artifact → label + cite, or mark open.
- Asserting present/absent from ONE source → cross-check, or mark inferred + name the grounding query.
- Jargon leaked into the "To forward" block → it's for a non-expert; translate.

## Sticky mode: keep updating incrementally

**Once `/onepager` has been invoked in a session, it becomes the standing format for progress updates for the rest of that session — and updates are INCREMENTAL, not full re-renders.** The first invocation produces the full one-pager (the baseline). After that, whenever you'd normally hand back a "here's what I did" progress wrap-up, render an **incremental update** against the most recent one-pager in the conversation instead.

(If `--audit` was the last mode fired, sticky updates use the audit incremental shape above instead of the default incremental shape below.)

**When to render an incremental update (an "update moment"):**
- You finished a chunk of work, fixed something, ran a check, hit a blocker, or are handing control back to the user.

**When NOT to (stay conversational — no one-pager):**
- Answering a direct factual/clarifying question, a quick acknowledgement, or mid-task narration. Don't force the format onto every message.

**Incremental shape** — only what moved since the last one-pager. The baseline is already in context; do not restate unchanged items.

```
# /onepager · update — <thread>  (since last)
_source: <session/PR/…> · unverified: <still-unverified, or "none">_

**Since last:** 1–2 sentences — what actually moved.

## ✅ Just done   (new since the last one-pager)
- <outcome> — [<label>](</absolute/path/or/url>)

## 🔧 Remaining (Δ)
- ✓ cleared: <item that's now done>
- ＋ new: <item that appeared>
- still blocked: <only if it's STILL the thing to focus on — else omit>

## → Next (revised)
1. <next move> — <who>
```

- If **nothing material changed**, don't re-render — say one line: *"No material change since last update — still on <X>."*
- Drop empty sections. Keep absolute-path links (the FORMATTING CONTRACT still applies).
- Every ~4–5 incremental updates, or whenever the user asks for "the full picture", re-render the **complete** baseline one-pager so drift is corrected, then resume incremental.

**Controls:**
- `/onepager` (re-invoke) → force a fresh full baseline now.
- `/onepager --audit` → switch to synthesis-first / TTS-friendly shape (sticky).
- `/onepager --intern` → switch to teach-the-reader / bottom-up shape (sticky).
- `/onepager off` / "stop the one-pager" → exit sticky mode, return to normal updates.
- `/onepager --html` → render the current state as HTML via `/visualize-via-html`.

**Durability caveat:** sticky mode lives in the session context, so `/clear` or a context compaction resets it — re-invoke `/onepager` to restart. (If you want it to survive compaction automatically, a Stop hook can re-assert the mode; ask and I'll wire it via `/update-config`.)

## Red flags — you're doing it wrong

- A "Done" bullet with no artifact link → STOP, add the artifact or mark it unverified.
- A file link with a relative target (`](src/foo.rs)`) → broken in Claude desktop, opens nothing. Make the target absolute.
- A "Business impact" / "what this means for leadership" section → wrong skill, you've drifted to manager altitude.
- Vague remaining items ("polish", "some cleanup") → name the actual blocker or cut it.
- Claiming something works that you couldn't verify this session → must appear under `unverified:` provenance, not under Done.
- Longer than one screen → you're dumping everything; keep only what the user should focus on.
- Asking the user to wait while you write a file → this is an inline catch-up; render it directly unless `--html`.
- Under `--audit`: link / path / URL / bullet leaked into Bottom line / What matters / The decision → move to Done.
- Under `--audit`: "What matters" just restated Done → rewrite as interpretation of what the work TAUGHT.
- Under `--audit`: Decision section forced when none is pending → remove it.

## Quick reference

| Concern | Rule |
|---|---|
| Audience | The user (driver/operator), never their manager |
| Default mode | Done-first tactical handoff. Every claim carries a clickable artifact (file/PR/log/S3/link) or is marked unverified. |
| `--audit` mode | Synthesis-first / TTS-friendly. Order: Bottom line → What matters → [Decision] → Next → Done → [Watch]. Top half link-free; Done retains absolute-path links. Neutral-flat tone. |
| When to use `--audit` | Reading aloud / voice mode; need the "what does this mean / what's the call" pass; re-orienting after time away. |
| `--intern` mode | Teach-the-reader / bottom-up. Order: In-one-line → The setup (primitives, defined) → How it's supposed to work → What happened (claims labeled observed/inferred/verified + artifacts; mechanism as file:line tree) → Verified vs open → Next → [To forward]. Define every term; no undefined jargon; verify-before-assert. |
| When to use `--intern` | Reader is expert-in-role but NEW to the feature/ticket (knows the product only at overview level); on-call triage on an unfamiliar area; "explain it like I just joined". |
| File links | Link target is an ABSOLUTE path (so it opens in Claude desktop); label can stay short |
| Source order | Current session → ticket/PR/git → vault brain |
| Altitude | Details that matter (blocker/gotcha/decision), not vague, not exhaustive |
| Format | Inline markdown by default; `/visualize-via-html` only on `--html`/request |
| Ending | Ordered next actions — the 20% to focus on |
| After 1st invoke | Sticky: keep using the active mode for update moments; updates are INCREMENTAL (delta vs last one-pager), not full re-renders |
| Re-baseline | Re-invoke `/onepager` or "full picture" → full render; every ~4–5 updates auto re-baseline |
| Switch mode mid-session | `/onepager` → default; `/onepager --audit` → audit; `/onepager --intern` → intern; each swaps and re-baselines |
| Stop | `/onepager off` exits sticky mode |
| Out of scope | Manager/business summary → `update-epic-note` |
