---
name: brain-ingest
description: Use when running the weekly second-brain refresh that distills new Claude Code session transcripts and Obsidian inbox notes into the vault wiki at ~/opensource/vault/wiki/
---

# brain-ingest

Weekly distillation of new Claude Code activity into the vault wiki. Manual — user runs when they want to compress recent activity into durable knowledge.

## Overview

The vault at `~/opensource/vault` holds:
- `raw/sessions/` — exported Claude Code transcripts
- `wiki/` — distilled knowledge (auto-loaded into CC sessions via `--add-dir`)
- `wiki/inbox/` — free-form notes the user dropped during the week

This skill processes new sessions + inbox items into the wiki, refreshes the active-state files, and appends an event line to the log. **Idempotent**: re-running with no new inputs is a no-op.

## When to Use

- User runs `/brain-ingest` (typically Sunday/end-of-week)
- User says "ingest this week's activity" / "refresh the brain" / "compress recent sessions"
- After a milestone (PR shipped, ticket closed) where user wants knowledge captured before context fades

**Do NOT use** for:
- Single-session writebacks (those happen in real time during the session via direct file edits)
- One-off "save this decision" requests (just edit the relevant `decisions.md` directly)

## Quick Reference

| Phase | Action | Targets |
|---|---|---|
| Bootstrap | Read `wiki/log.md` to find last-ingest timestamp | `wiki/log.md` |
| Refresh | Run `export_sessions.py --since <last-ingest>` | `raw/sessions/` |
| Classify | For each new session: project (vscode/wipdp/magnetx), themes | per-session |
| Distill | Extract decisions, threads, corrections, summaries | per-project files |
| Inbox | Process each `wiki/inbox/*.md` | route + move to `processed/` |
| Plans | Distill `~/.claude/plans/*.md` newer than cutoff | per-project files; orphans → `wiki/inbox/plan-orphan-*.md` |
| Auto-memory sweep | Run parallel-store classifier; stage drift to `wiki/inbox/` | `wiki/inbox/auto-memory-{merge,promote,unknown}-<date>.md` |
| Refresh hot | Update `wiki/hot.md` with current state | `wiki/hot.md` |
| Sessions index | Append UUID-keyed entries | `wiki/sessions-index.md` |
| Log | Append summary line | `wiki/log.md` |
| Report | Print human diff to console | stdout |

## Implementation

### 1 — Bootstrap

Read `~/opensource/vault/wiki/log.md`. The last `brain-ingest` line gives the cutoff. If none exists (first run), use the last 14 days.

### 2 — Refresh raw sessions

```bash
python3 ~/opensource/vault/claude-code/scripts/export_sessions.py --since YYYY-MM-DD
```

This exports new session transcripts to `~/opensource/vault/raw/sessions/`. The script is idempotent — already-exported sessions are skipped.

List the files newer than the cutoff. **Only process those.** Do not re-process old sessions even if they're sitting in the directory.

### 3 — Classify each new session

For each new transcript:
- **Project**: detect from path/content. `vscode` if filename or `cwd` references `eightfold/vscode`. `wipdp` if `eightfold/wipdp`. `magnetx` if magnetx repo or `/magnetx-*` skills. Other → tag as `other` and skip per-project distillation.
- **Themes**: scan for ticket IDs (ENG-XXXXX), PR numbers, prominent file paths.

### 4 — Distill (per session)

Extract four signal types and route them. Each signal must be **deduped against existing entries** before appending.

#### a) Decisions → `wiki/projects/<project>/decisions.md`

Trigger phrases: "we decided", "let's go with", "the right call is", "instead of X we'll do Y".

Format (append, never overwrite):
```markdown
## YYYY-MM-DD — <one-line decision>
- Why: <rationale, one sentence>
- Trade: <what we give up, optional>
- Source: raw/sessions/<filename>
```

**Dedup**: if a decision with the same first-line title exists already, skip (or update only the `Source:` line if it adds a new session).

#### b) Open threads → `wiki/projects/<project>/open-threads.md`

Trigger: blockers ("blocked on", "stuck on", "we'll come back to"), parked questions ("we should figure out", "TBD"), unresolved discussion.

Format (one H2 per thread):
```markdown
## ENG-XXXXX <short title> (or descriptive title if no ticket)
- Status: <not-started | in-progress | blocked | awaiting-review | parked>
- Blocker: <what's blocking>
- Last touched: YYYY-MM-DD
- Next action: <concrete next step>
- Source: <session UUID or PR link>
```

**Dedup**: match on H2 title (or ticket ID inside it). If exists, update `Last touched` and `Status` only — never duplicate the section.

**Resolution detection**: if a recent session contains "PR merged", "shipped", "closed ENG-XXXXX", "resolved", remove the matching thread (or move under a `## Resolved` section at the bottom of the file).

#### c) Corrections → `wiki/friction-log/recurring-corrections.md`

Trigger lexemes (verbatim from history): "don't", "actually", "no,", "stop", "wrong", "I told you", "we already", "always", "never", "remember".

For each, capture:
- The verbatim correction text (or paraphrased if too long, but prefer verbatim)
- One-line context
- Date

**Dedup**: if the same lexical pattern appears more than 2x across sessions, increment a count tag in the entry rather than adding a new one. Keep the catalog growing carefully — top items get promoted to `wiki/CLAUDE.md` (mention this in the report; don't promote automatically).

#### d) One-line session summary → `wiki/sessions-index.md`

For every new session (regardless of project):
```markdown
## YYYY-MM-DD
- `<sessionId-short>` — <project> — <one-line summary>
```

Group by date. Append under the most recent date heading; create a new heading if needed. Don't overwrite previous entries.

### 5 — Process inbox

For each `~/opensource/vault/wiki/inbox/*.md` (NOT under `processed/`):
- Read the note
- Classify: decision? thread? correction? cross-cutting concept?
- Route to the right destination using the same dedup rules as above
- Move the file to `~/opensource/vault/wiki/inbox/processed/YYYY-MM-DD-<original-name>.md`

**Important**: do NOT delete inbox items. Move them. The user may want to audit what was processed.

### 5a — Process plans (`~/.claude/plans/*.md`)

Distill structured plan files written by `/think` and plan-mode invocations into vault decisions / charter / learnings. Plans are durable raw sources — never modified or deleted.

#### Inputs
Every `*.md` in `~/.claude/plans/` whose mtime > cutoff (same cutoff as Bootstrap).

#### Skip filter
Skip plan files smaller than 500 bytes whose name matches the auto-generated pattern (`[a-z]+-[a-z]+-[a-z]+\.md`, e.g. `can-you-develop-a-ethereal-naur.md`). These are abandoned drafts from plan mode where the user exited without writing real content. Larger or named plans always process.

#### Resolve repo + initiative slug

For each plan:
- Look for `> Generated from /think session ... Initiative: \`<slug>\`` in the frontmatter quote block → that's the slug.
- Look for `cwd` references inside the plan or the slug→repo mapping in `~/.claude/work_hq/board.json` to resolve `<repo>`.
- Fallback: filename stem as slug; repo unresolved → stage to `plan-orphan-<plan-name>.md` (see below).

#### Extract section by section

| Plan section | Vault target | Dedup rule |
|---|---|---|
| `## Decisions (this session)` or `## Decisions Made` | `wiki/projects/<repo>/initiatives/<slug>/decisions.md` (or `wiki/projects/<repo>/decisions.md` if no initiative) | Match on first-line title; skip if exists. |
| `## Constraints (from charter)` | `wiki/projects/<repo>/initiatives/<slug>/charter.md` under `## Constraints` H2 (create if missing) | Skip identical bullets. |
| `## Prior Learnings Honored` | `wiki/projects/<repo>/initiatives/<slug>/learnings.md` | Skip if entry already there (usually a no-op since these were originally pulled from learnings.md). |
| `## Approach`, `## Critical Files to Modify`, `## Sequencing`, `## Verification` | NOT promoted | Lives in plan file (durable). Promoting would duplicate. |

When repo or initiative cannot be resolved, stage the plan's full Decisions block in `wiki/inbox/plan-orphan-<plan-name>.md` for human routing. Don't guess.

#### Sessions index entry

For each plan processed, append one line under the relevant date heading in `wiki/sessions-index.md`:
```
- plan: <plan-name> — <N> decisions absorbed → <vault-target-paths>
```

#### Idempotence

Plans are NEVER moved or deleted from `~/.claude/plans/`. The mtime cursor (Bootstrap) prevents re-processing. If a plan is edited after first ingest, mtime changes and it re-processes — the dedup rules above prevent duplicate vault entries.

### 5b — Sweep auto-memory (`~/.claude/projects/*/memory/`)

Reuse the parallel-store classifier from `--lint` mode (steps 7-8 below). In ingest mode, take action per category instead of just reporting. **This phase reuses the classifier defined in `--lint` mode — both modes call the same classification function; only the action differs (`--lint` reports, ingest stages).** This is the DRY guarantee.

Auto-memory files are NEVER modified or deleted. Per the "vault primary; auto-memory fallback" rule in `wiki/CLAUDE.md`, auto-memory is a parallel store kept as fallback. Ingest only stages drift to inbox for human review.

#### Action per classifier output

| Classifier output | Ingest action |
|---|---|
| `DuplicateVaultRicher` | Skip — vault already wins. Increment skip counter. |
| `DuplicateRoughEqual` | Skip — no value in re-merge. Increment skip counter. |
| `DuplicateVaultPoorer` | **Stage** in `wiki/inbox/auto-memory-merge-<YYYY-MM-DD>.md`. Per file: auto path, vault target, byte delta, 5-line content sample of what's richer in auto. **Do NOT auto-merge** — content judgment required (proven by manual migration on 2026-05-03). |
| `LegacyOnly` (in scope: `feedback_*`, `learnings_*`, `project_*`, `projects/<slug>/*`) | **Stage** in `wiki/inbox/auto-memory-promote-<YYYY-MM-DD>.md`. Per file: auto path, suggested vault target (per `--lint` step 7 mapping table), 3-line content preview. |
| `LegacyOnly` (operational: `branches/`, `**/checkpoints/`) | Skip silently. Operational state belongs in `~/.claude/work_hq/`, not vault. |
| `Unknown filename pattern` | Stage in `wiki/inbox/auto-memory-unknown-<YYYY-MM-DD>.md` for human classification. |

#### Inbox staging file format

One file per category per day. If `/brain-ingest` runs twice in one day, the file is **overwritten** with current classifier output (not appended) — the classifier is deterministic, so overwriting just refreshes the snapshot.

```markdown
---
type: auto-memory-staging
category: <merge | promote | unknown>
date: YYYY-MM-DD
---

# Auto-memory <category> — <date>

<count> file(s) flagged. Review and route to vault, or delete this file once handled.

---

## <auto-file-path>
- Vault target: <suggested-vault-path>
- Auto bytes: <N>  ·  Vault bytes: <M>  ·  Delta: +<D>
- Sample (lines unique to auto):
  ```
  <up-to-5-lines>
  ```

## <next file>
...
```

#### Idempotence

Once a user merges a `DuplicateVaultPoorer` file (manually or via next `/brain-ingest --inbox-only`), the next sweep reclassifies it as `DuplicateVaultRicher` and silently skips it. No flag, no marker — the classifier output is the source of truth.

### 6 — Refresh `wiki/hot.md`

Rewrite (not append) sections:
- **Active Right Now**: detect from most-recent session(s) — what tickets/PRs are in flight, what state they're in. Pull from `open-threads.md` H2 statuses.
- **Open Threads (top 3)**: 3 most-recently-touched H2 entries across all `open-threads.md` files.
- **Last Session**: 2-line summary of the most recent meaningful session (skip pure-meta or skill-design sessions).
- **Recent Corrections (last 5, verbatim)**: 5 most recent verbatim correction entries from session distillation. **Verbatim** is non-negotiable — paraphrasing defeats the purpose (preventing recurrence by re-exposure).

### 7 — Append `wiki/log.md`

```
YYYY-MM-DDTHH:MM brain-ingest processed N sessions, M inbox items, +X decisions, +Y threads, +Z corrections
```

Use ISO-8601 timestamp.

### 8 — Report

Print a human-readable summary to stdout:
```
brain-ingest complete (cutoff: 2026-04-26)
  Sessions processed: 7 (vscode: 4, wipdp: 2, magnetx: 1)
  Inbox items: 3 → all routed
  Added: 2 decisions, 4 threads, 3 corrections
  Threads resolved: 1 (ENG-4801)
  Promotion candidates for wiki/CLAUDE.md: ["don't post needs_ci after push" — 4 occurrences]

Run `/brain-ingest --lint` to check skill ↔ data contracts for orphans and tier breaches.
```

## Common Mistakes (Red Flags)

| Mistake | Counter |
|---|---|
| Processing all sessions in `raw/sessions/` | Read `log.md` first to find cutoff. Only process newer files. |
| Overwriting `decisions.md` instead of appending | New decisions go AFTER existing ones. Never rewrite the file. |
| Creating duplicate `open-threads.md` H2 entries | Match by ticket ID or H2 title; update existing instead of adding. |
| Paraphrasing corrections in `hot.md` | Corrections must be verbatim — that's their entire purpose. |
| Forgetting `log.md` append | Always append, even on "no new activity" runs (write `no-op` line). |
| Deleting processed inbox items | Move to `inbox/processed/`, never delete. |
| Confusing `raw/sessions/` (auto-exported) with `wiki/inbox/` (user-written) | They're processed differently. Sessions = transcripts (signal extraction). Inbox = formed thoughts (route + move). |
| Auto-promoting corrections to `wiki/CLAUDE.md` | NEVER auto-edit `CLAUDE.md`. Report candidates; let user promote. |
| Touching `wiki/sessions-index.md` is excluded from `wiki/index.md` discovery | That's intentional. Don't add it to `index.md`. |
| Auto-merging auto-memory `DuplicateVaultPoorer` files | Always stage to inbox. Merge requires content judgment that an unattended run can't do reliably (proven by manual migration on 2026-05-03). |
| Re-processing already-distilled plans | Cursor by mtime > last `brain-ingest` log line. Plans are durable; never modified. |
| Modifying `~/.claude/plans/*.md` or auto-memory files | These are raw sources. Vault is the write target. Never edit raw sources during ingestion. |
| Creating one inbox staging file per source file | Stage per-day per-category (`auto-memory-merge-<date>.md`, etc.), not per-file. Reduces noise. |

## Files Read / Written

**Read:**
- `~/opensource/vault/wiki/log.md`
- `~/opensource/vault/raw/sessions/*.md` (only new since cutoff)
- `~/opensource/vault/wiki/inbox/*.md` (not under `processed/`)
- `~/opensource/vault/wiki/projects/<X>/{decisions,open-threads}.md` (for dedup)
- `~/opensource/vault/wiki/projects/<X>/initiatives/<slug>/{decisions,charter,learnings}.md` (for dedup during Plans phase)
- `~/opensource/vault/wiki/friction-log/recurring-corrections.md` (for dedup)
- `~/.claude/plans/*.md` (mtime > cutoff — Plans phase)
- `~/.claude/projects/*/memory/**/*.md` (full enumeration — Auto-memory sweep)

**Written (append unless noted):**
- `~/opensource/vault/wiki/projects/<X>/decisions.md`
- `~/opensource/vault/wiki/projects/<X>/open-threads.md`
- `~/opensource/vault/wiki/projects/<X>/initiatives/<slug>/{decisions,charter,learnings}.md` (Plans phase)
- `~/opensource/vault/wiki/friction-log/recurring-corrections.md`
- `~/opensource/vault/wiki/sessions-index.md`
- `~/opensource/vault/wiki/hot.md` (REWRITE specific sections)
- `~/opensource/vault/wiki/log.md` (append)
- `~/opensource/vault/wiki/inbox/processed/<...>.md` (mv from inbox/)
- `~/opensource/vault/wiki/inbox/auto-memory-{merge,promote,unknown}-<date>.md` (REWRITE per day; staging from Auto-memory sweep)
- `~/opensource/vault/wiki/inbox/plan-orphan-<plan-name>.md` (when plan can't be routed to a known initiative/repo)

**Never touched:**
- `~/opensource/vault/wiki/CLAUDE.md` (manual user promotion only)
- `~/opensource/vault/wiki/index.md` (manual when structure changes)
- Any `~/eightfold/` repo files
- `~/.claude/plans/*.md` (raw source — read-only during ingestion)
- `~/.claude/projects/*/memory/**` (raw source — auto-memory is fallback per `wiki/CLAUDE.md`)

## Arguments

- No args → process since last `brain-ingest` log line
- `--since YYYY-MM-DD` → override cutoff
- `--dry-run` → run classification + report, but write nothing
- `--inbox-only` → skip session processing, only route inbox items
- `--project <name>` → only process sessions for one project
- `--skip-plans` → opt out of Plans phase (5a)
- `--skip-auto-memory` → opt out of Auto-memory sweep (5b)
- `--plans-only` → only run Plans phase (skips sessions / inbox / auto-memory)
- `--auto-memory-only` → only run Auto-memory sweep (similar to `--lint` but takes action — stages drift to inbox instead of just reporting)
- `--lint` → contract lint mode; skips ingestion, only audits skill `## Data Contract` sections (see below)

---

## `--lint` mode (contract audit)

Audits the skill ↔ data contracts across all skills. Use to catch orphan reads/writes, missing contracts, or DB tier breaches.

### Flow

1. Discover skills: `ls ~/.claude/skills/*/SKILL.md` AND `ls ~/.claude/skills/*.md` (legacy single-file skills).
2. For each skill, parse the `## Data Contract` section. Extract path lists from sub-sections:
   - `### Reads (DB)` → `R_db[skill]`
   - `### Reads (Memory)` → `R_mem[skill]`
   - `### Writes (Memory)` → `W_mem[skill]`
   - `### Local (skill-only)` → `L[skill]`
   If no `## Data Contract` section exists, record skill in `MissingContract[]`.
3. Build inverted graph:
   - `readers[path]` = all skills with `path` in any `R_*`
   - `writers[path]` = all skills with `path` in `W_mem`
4. Tier classification (used to flag breaches). DB tier paths match these patterns:
   - `~/opensource/vault/wiki/CLAUDE.md`
   - `~/opensource/vault/wiki/index.md`
   - `~/opensource/vault/wiki/projects/<repo>/{overview,decisions,runbooks,code-conventions}.md`
   - `~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/{charter,decisions,learnings,e2e-flow}.md`
   - `~/opensource/vault/wiki/patterns/*.md`
   - `~/opensource/vault/wiki/friction-log/*.md`
   - `~/opensource/vault/wiki/sessions-index.md`
   Memory tier: `~/opensource/vault/wiki/{hot,log}.md`, `~/opensource/vault/wiki/projects/<repo>/open-threads.md`, `~/opensource/vault/wiki/inbox/`, `~/.claude/work_hq/*`, `~/.claude/scheduled/state/*`.
5. Compute findings:
   - **OrphanWrite[path]** — `path ∈ writers AND readers[path] = ∅` AND `path` not consumed by `/brain-ingest` itself (sessions-index.md, log.md exempt). Wasted capture target.
   - **OrphanRead[path]** — `path ∈ readers AND writers[path] = ∅` (excluding paths that humans edit in Obsidian: vault DB tier and `wiki/inbox/`). Stale reference candidate.
   - **MissingContract** — list of skills without `## Data Contract` section.
   - **TierBreach[path]** — `path ∈ DB tier AND writers[path] ⊄ {/brain-ingest}` (any non-brain-ingest skill writing to a DB-tier file is a breach).
6. Print human report:

```
=== brain-ingest --lint ===

Skills scanned: <N>
Skills missing Data Contract: <M>
  - <skill-name-1>
  - <skill-name-2>

Orphan writes (file is written but no skill reads):
  - <path>  (writers: <skill-1>, <skill-2>)

Orphan reads (file is read but no skill writes; possibly stale):
  - <path>  (readers: <skill-1>)

DB tier breaches (DB file written by skill other than /brain-ingest):
  - <path>  (writer: <skill-name>)
    → consider: move write to /brain-ingest, or reclassify path as Memory tier

Healthy contracts: <K>
```

7. **Parallel-store check** — detect Claude Code auto-memory duplicating vault DB content.
   - Enumerate `~/.claude/projects/*/memory/` (every encoded-cwd auto-memory dir).
   - For each file matching DB-equivalent shapes, classify and pair with a vault path:

     | Auto-memory pattern | Inferred vault counterpart |
     |---|---|
     | `<auto>/projects/<slug>/charter.md` | `wiki/projects/<repo>/initiatives/<slug>/charter.md` (resolve `<repo>` from auto-memory dir name) |
     | `<auto>/projects/<slug>/decisions.md` | `wiki/projects/<repo>/initiatives/<slug>/decisions.md` |
     | `<auto>/projects/<slug>/learnings.md` | `wiki/projects/<repo>/initiatives/<slug>/learnings.md` |
     | `<auto>/projects/<slug>/e2e-flow.md` | `wiki/projects/<repo>/initiatives/<slug>/e2e-flow.md` |
     | `<auto>/projects/<slug>.md` | `wiki/projects/<repo>/initiatives/<slug>/charter.md` (top-level project descriptor; charter is closest match) |
     | `<auto>/project_overview.md` | `wiki/projects/<repo>/overview.md` |
     | `<auto>/project_guidelines.md` | `wiki/projects/<repo>/runbooks.md` or `wiki/patterns/code-conventions.md` |
     | `<auto>/project_active_work.md` | `wiki/hot.md` (active state) |
     | `<auto>/project_architecture_decisions.md` | `wiki/projects/<repo>/decisions.md` |
     | `<auto>/project_learnings.md` | `wiki/projects/<repo>/decisions.md` (or new `learnings.md`) |
     | `<auto>/project_references.md` | none — review for migration |
     | `<auto>/feedback_*.md` | `wiki/friction-log/recurring-corrections.md` |
     | `<auto>/learnings_*.md` | `wiki/projects/<repo>/decisions.md` or `wiki/patterns/*.md` |
     | `<auto>/MEMORY.md` | none — auto-memory's own index, not vault content |
     | `<auto>/branches/**`, `<auto>/**/checkpoints/**` | operational — `~/.claude/work_hq/board.json` (do NOT migrate to vault) |

   - For each pair, compare:
     - **DuplicateVaultRicher** — vault file exists AND `wc -c vault > wc -c auto`. Delete-safe (auto is older).
     - **DuplicateVaultPoorer** — vault file exists AND `wc -c vault < wc -c auto`. Migrate then delete.
     - **DuplicateRoughEqual** — both exist, sizes within ±10%. Delete auto-memory copy.
     - **LegacyOnly** — auto exists, vault path does not. Migration candidate (or operational/skip per table above).
     - **Operational** — branches/checkpoints; not for vault. Skip without flagging.

8. Print parallel-store section in the report:

```
=== Parallel-store audit (auto-memory vs vault) ===

Duplicates where vault is RICHER (delete auto-memory copy after final diff):
  - <auto-path>  vs  <vault-path>  (auto=<bytes> vault=<bytes>)

Duplicates where vault is POORER (migrate auto → vault, then delete):
  - <auto-path>  vs  <vault-path>  (auto=<bytes> vault=<bytes>)

Legacy-only (in auto-memory, no vault counterpart) — migration candidates:
  - <auto-path>  → suggested vault target: <path>

Operational (branch checkpoints, NOT for vault):
  - <count> files under branches/ or checkpoints/ — leave or move to ~/.claude/work_hq/
```

The report is the **input to a one-time cleanup**; this skill does NOT auto-delete or auto-migrate. User reviews, then either edits/deletes manually or runs `/brain-ingest --import-legacy-memory` (separate, future mode).

9. Do NOT write any data files in lint mode (no log.md append, no sessions-index, no Memory writes). Lint is read-only audit.

### End-of-run hint (added to standard `/brain-ingest`)

After the standard distillation report, print:
```
Run `/brain-ingest --lint` to check skill ↔ data contracts for orphans and tier breaches.
```

This prompts the user to validate contracts opportunistically — the lint itself stays manual (no auto-run).
