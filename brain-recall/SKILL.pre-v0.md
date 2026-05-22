---
name: brain-recall
description: Use when the user gives Claude an artifact (PR/Jira URL, ENG-XXXXX, error, freeform topic) plus a goal — test, ship, fix, debug, review, brainstorm, understand. Reads the artifact semantically (PR body / ticket description, not just metadata), recalls related prior knowledge from `~/opensource/vault/wiki/`, surfaces findings in prose with cited paths, and chains into the right next skill with that context loaded. Pairs with `/brain-ingest`.
---

# brain-recall

A context-aware preface for any task. When the user hands Claude an artifact and a goal, `/brain-recall` reads the artifact semantically, pulls related prior knowledge from the second-brain wiki, summarizes what it found in plain prose, and chains into the next skill armed with that context.

**The goal isn't to produce a structured retrieval bundle. The goal is to make Claude smarter for whatever comes next.**

The wiki has two halves:
- **Durable** (primary): `projects/<repo>/{overview,decisions,runbooks}.md`, `projects/<repo>/initiatives/<slug>/{charter,decisions,learnings,e2e-flow}.md`, `patterns/`, `friction-log/`.
- **RAM** (only when query touches current/unresolved state): `hot.md`, `open-threads.md`, `log.md`.

Beta: manual invocation only.

---

## When to use

- User pastes a PR URL, Jira URL, or ticket key with a verb: "help me test", "let's ship", "fix this", "review this", "brainstorm on", "walk me through".
- "What do we know about X?" / "X vs Y" / "How was X built?" / "Prior art on Y?"
- Before any of `/test-live-api`, `/work-on-jira-task`, `/ship-task`, `/think`, `/get-pr-ready-to-merge`, `/debug-api` — to prime context first.
- Anytime Claude would otherwise dive into action without checking what the brain already knows.

## When NOT to use

- "What's active right now?" → `/today` or read `hot.md`. brain-recall is for prior knowledge, not live state.
- External artifact someone else owns (other people's PR, blog post, RFC) → `/explain-anything`.
- Updating the wiki → that's the session protocol in `wiki/CLAUDE.md`.

## Inputs

Any combination:
- Jira URL / `ENG-XXXXX` / GitHub PR URL
- Freeform topic ("agent-builder testing", "manager-agent-v2 vs agent-builder")
- An **action verb** signaling the goal: test, ship, fix, debug, brainstorm, review, understand
- Optional `<repo>` hint

---

## Steps

### 1. Read the artifact semantically — content over metadata

The artifact's *content* is the meat. Always start here:

- **PR URL** → `gh pr view <num> --json title,body,headRefName,number`. Read the **SUMMARY** / title to understand what the change actually does (e.g. *"Flask-RESTX proxy endpoints in tether_api.py for agent builder admin panel"*) — not just the PR number.
- **Jira URL/key** → `python3 ~/.claude/work_hq/update.py get <key>` first; if not on board, Atlassian MCP `getJiraIssue` for title + description.
- **Freeform topic** → use as-is.

Output of this step is a **one-line semantic summary** of what the artifact is *about*. That summary, not the IDs, drives Step 3.

Metadata (PR#, branch, stage, ticket key) is a shortcut for board lookup. It is not the meat. If metadata doesn't resolve, fall through to topic search — never give up.

### 2. Identify the user's goal

Look at the verb in the prompt. The goal shapes what *adjacent* knowledge to pull alongside the artifact's own context.

| Goal verb | Also recall |
|---|---|
| test, smoke-test, verify | `projects/<repo>/runbooks.md`, prior testing of similar features, env/test entries in `friction-log/recurring-corrections.md` |
| ship, merge, get-ready | PR-ops corrections, sandbox flow in `patterns/workflow-patterns.md`, `gh` discipline in friction-log |
| fix, debug, investigate | initiative `e2e-flow.md`, similar past bugs in `learnings.md`, error-handling conventions |
| brainstorm, think, explore, weigh | initiative `decisions.md` + `learnings.md`, related/sibling initiatives |
| review, check | `patterns/code-conventions.md`, `projects/<repo>/decisions.md` for the area, recent corrections |
| understand, explain, walk me through | `e2e-flow.md`, `charter.md`, `overview.md` |
| (no verb) | default — initiative bundle |

The goal verb is **mandatory input** — never ignore it. "help me test" implies *both* "tell me about this PR" *and* "tell me how testing works for this kind of change in this repo".

### 3. Recall — topic first, metadata second

**Topic-first navigation.** Take the semantic summary from Step 1 and find candidate initiative slugs:

1. **Mandatory:** open `~/opensource/vault/wiki/index.md` and grep the **Initiatives** section for slugs matching topic words from the summary (e.g. "agent-builder", "manager-agent-v2", "rag-pipeline").
2. The path listed in `index.md` is **canonical**. An initiative's primary docs may live under a *different repo* than the ticket repo. Example: `agent-builder` is wipdp-primary (`wiki/projects/wipdp/initiatives/agent-builder/`) even though tickets live on either side. **Never declare an initiative file missing without checking `index.md` first.**
3. Open `wiki/projects/<canonical-repo>/initiatives/<slug>/{charter, decisions, learnings, e2e-flow}.md` for the resolved slug.
4. Grep `wiki/projects/<repo>/decisions.md` for area keywords from the summary.

**Metadata shortcut.** If the artifact had a ticket key, the work_hq lookup gives `initiative_slug`, `repo`, `branch`, `PR`, `stage`, `tags`. Use it to skip topic search. If it returns nothing, do the topic search anyway.

**Goal-driven adjacent reads** (per Step 2 table). Do these in addition to the artifact's own context — that's the whole point of being goal-aware.

Budget roughly 8 file reads. If more candidates exist, mention them in prose ("there's also a `manager-agent-v2` initiative I didn't open — say the word") rather than expand.

### 4. Fall back only when the vault has gaps

Only after durable + RAM didn't answer:
1. `~/.claude/plans/*.md` matching slug or ticket
2. `~/.claude/projects/<encoded-cwd>/memory/*.md` for current cwd
3. Mention `/search-history <keyword>` as a suggestion; don't run it inline by default.

**Track every fallback hit.** Keep a list `fallback_hits = [(path, one_line_summary), ...]` for Step 7.

State the fallback in plain prose: *"Vault didn't have a test pattern for proxy endpoints; checked `~/.claude/plans/agent-builder.md` and found the dev-server + presigned-URL flow."* or *"No prior testing notes — falling back to /test-live-api defaults."*

### 5. Surface findings in Claude's own words

Write prose, not a fixed template. Cite paths inline so the user can verify and edit at source.

Shape (illustrative — adapt to the situation):

> The PR is the vscode-proxy side of the **agent-builder** initiative — Flask-RESTX endpoints in `tether_api.py` so the React admin panel can manage agent configs via the wipdp operator platform. Initiative docs live at `wiki/projects/wipdp/initiatives/agent-builder/` (cross-repo: ticket in vscode, docs in wipdp).
>
> Prior decisions on this initiative: operator platform owns agent-config CRUD; admin docs upload uses presigned S3 (`agent-builder/decisions.md`). The closest sibling ticket is ENG-191692 (S3 source filename, wipdp side, merged 2026-04-30).
>
> For testing in vscode: pytest runs on EC2 (`ssh ec2-user@172.31.27.248`), targets `apps/tether_app/tests/test_tether_api.py` — see `projects/vscode/runbooks.md`. No documented live-API test pattern specifically for proxy endpoints; closest prior art is the ENG-191692 test setup.
>
> Gap: no `learnings.md` for agent-builder yet — worth `/brain-ingest` after this PR ships.
>
> I'll chain into `/test-live-api` with the pytest target and PR body's endpoint list pre-loaded.

That's the whole deliverable. No `Resolved` block, no `Gaps` section header, no `Suggested next step` line. Plain prose with cited paths and a clear next move.

### 6. Chain (or ask, if uncertain)

End with the next move. If the goal is clear and context is sufficient, **chain into the right skill immediately**:
- `test` / `verify` → `/test-live-api`
- `ship` / `merge` → `/get-pr-ready-to-merge`
- ticket implementation → `/work-on-jira-task`
- end-to-end → `/ship-task`
- exploratory → `/think`
- failing endpoint → `/debug-api`

If unclear (multiple candidate slugs, ambiguous goal, missing repo), name the choices in one sentence and wait.

**Chaining is part of the job.** brain-recall is a preface, not a terminator. The whole point is that the next skill starts smarter.

### 7. Backfill the brain when fallback yielded info

If `fallback_hits` from Step 4 is non-empty, the wiki had a real gap and the answer lived in a fallback source. Backfill the wiki so next time it's a Step 3 hit, not a Step 4 fallback.

**How:** chain `/brain-ingest` with the fallback paths as scope. `/brain-ingest` already knows how to route plans (its "Plans" phase) and auto-memory (its "Auto-memory sweep" phase) into the right wiki destinations — it dedupes against existing entries and stages anything ambiguous to `wiki/inbox/` for review. brain-recall does **not** decide where the content lands; brain-ingest owns that.

**When to chain:**
- The fallback content was load-bearing for the answer (you cited it in Step 5 prose).
- Single-fact / trivial mentions: skip ingest, just note the path inline.

**Order of operations:**
- If Step 6 chained an action skill (test/ship/etc.), let that skill run first. brain-ingest happens **after** the action completes so it doesn't block your goal.
- If Step 6 didn't chain (pure recall query), invoke `/brain-ingest` immediately with scope = fallback paths.

**Surface this in prose:** *"Pulled the missing test pattern from `~/.claude/plans/agent-builder-testing.md` — that's a wiki gap. After we finish testing, I'll run `/brain-ingest` scoped to that file so it lands in `wiki/projects/wipdp/initiatives/agent-builder/` and we don't fall back next time."*

**Don't ceremonialize.** No headers, no checklists. One sentence. The point is the loop closes — fallback today becomes durable knowledge tomorrow.

---

## Guardrails

- **Step 1 is non-negotiable.** Always read the artifact's content before navigating the wiki. The difference between "PR #105712" and "Flask-RESTX proxy endpoints for agent builder admin panel" is the difference between metadata-matching and actually retrieving the right knowledge.
- **`index.md` lookup before "not found".** Initiative paths can cross repos; don't trust the ticket repo to determine the docs repo.
- **Goal verb shapes adjacent recall.** Ignoring the verb is the most common failure mode — it makes brain-recall feel useless on action prompts like "help me test".
- **Cite paths inline.** Always.
- **Prose, not template.** Beta priority is the meat (right knowledge surfaced + acted on), not cosmetics.
- **State gaps in plain language.** "I didn't find X — falling back to defaults" is correct. A `Gaps:` heading is not.
- **Chain when the next move is obvious.** If you'd otherwise wait for the user to say "ok now do the thing", just do the thing.

## Beta notes

- Manual invocation only; no auto-trigger by other skills yet.
- RAM-file reads (`hot.md`, `open-threads.md`, `log.md`) are soft — bias toward including when the goal touches current state or in-progress work.
- If a particular gap appears across multiple sessions, mention it as a `/brain-ingest` priority candidate. Don't formalize until patterns emerge.

---

## Composes with

- `/test-live-api` — preload PR body, pytest target, runbooks, prior testing patterns; chain.
- `/work-on-jira-task` — preload initiative charter/decisions/e2e-flow; chain.
- `/think` — preload related decisions/learnings to avoid relitigating; chain.
- `/ship-task`, `/get-pr-ready-to-merge`, `/debug-api` — same shape.
- `/explain-anything` — distinct: external artifacts; brain-recall is the user's own brain.
- `/brain-ingest` — counterpart. When Step 4 fallback yields load-bearing info, brain-recall actively chains `/brain-ingest <fallback-paths>` (after the action skill, or immediately for pure-recall queries) so the gap closes. brain-ingest owns routing into the wiki.

---

## Data Contract

### Reads (durable / primary)
- `~/opensource/vault/wiki/index.md` — slug discovery (mandatory before declaring "not found")
- `~/opensource/vault/wiki/projects/<repo>/{overview,decisions,runbooks}.md`
- `~/opensource/vault/wiki/projects/<repo>/initiatives/<slug>/{charter,decisions,learnings,e2e-flow}.md`
- `~/opensource/vault/wiki/patterns/{code-conventions,workflow-patterns,skills-catalog,setup}.md`
- `~/opensource/vault/wiki/friction-log/recurring-corrections.md`

### Reads (RAM, soft)
- `~/opensource/vault/wiki/hot.md`
- `~/opensource/vault/wiki/projects/<repo>/open-threads.md`
- `~/opensource/vault/wiki/log.md`

### Reads (anchor)
- `python3 ~/.claude/work_hq/update.py get <ticket_key>` — canonical board lookup

### Reads (fallback on vault gap)
- `~/.claude/plans/*.md`
- `~/.claude/projects/<encoded-cwd>/memory/*.md`

### Live external (artifact resolution — required, not optional)
- `gh pr view <num> --json title,body,headRefName,number` — for any PR URL
- Atlassian MCP `getJiraIssue` — when ticket key not on the board

### Writes
- None.
