---
name: onepager
description: Use when the user fires `/onepager`, or asks for a "one pager", "tech-executive summary", "tech exec summary", "catch me up", "where are we", "what's done / remaining / next", or a tight scannable status of the work in progress. Produces a self/driver-facing technical one-pager (NOT a manager/business summary) of done · remaining · next, with an auditable artifact link on every claim. Pulls from the current session first; reaches for PR/git/Jira/vault only when the session can't supply or verify a fact.
---

# /onepager

## Purpose

The user is the driver; you are the assistant catching them up. Produce ONE scannable page — **what's done · what's remaining · what's next** — so they can get the picture without re-reading everything, then act.

This is the **self / tech-operator** one-pager. It is for the person driving the work, not their manager. Surface the few technical details that matter (the blocker, the gotcha, the pending decision) and suppress the rest. End pointing at action.

The first invocation renders the full picture; after that it is **sticky and incremental** — subsequent progress updates stay in this format and show only what changed (see "Sticky mode" below).

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

## Sticky mode: keep updating incrementally

**Once `/onepager` has been invoked in a session, it becomes the standing format for progress updates for the rest of that session — and updates are INCREMENTAL, not full re-renders.** The first invocation produces the full one-pager (the baseline). After that, whenever you'd normally hand back a "here's what I did" progress wrap-up, render an **incremental update** against the most recent one-pager in the conversation instead.

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

## Quick reference

| Concern | Rule |
|---|---|
| Audience | The user (driver/operator), never their manager |
| Every claim | Carries a clickable artifact (file/PR/log/S3/link) or is marked unverified |
| File links | Link target is an ABSOLUTE path (so it opens in Claude desktop); label can stay short |
| Source order | Current session → ticket/PR/git → vault brain |
| Altitude | Details that matter (blocker/gotcha/decision), not vague, not exhaustive |
| Format | Inline markdown by default; `/visualize-via-html` only on `--html`/request |
| Ending | Ordered next actions — the 20% to focus on |
| After 1st invoke | Sticky: keep using the format for update moments; updates are INCREMENTAL (delta vs last one-pager), not full re-renders |
| Re-baseline | Re-invoke `/onepager` or "full picture" → full render; every ~4–5 updates auto re-baseline |
| Stop | `/onepager off` exits sticky mode |
| Out of scope | Manager/business summary → `update-epic-note` |
