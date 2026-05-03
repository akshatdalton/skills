---
name: explain-anything
description: Explain any reference as a zero-context story with citations and call-path tracing. Use when the user shares a Jira ticket, GitHub PR or issue, Sentry error, Slack thread, URL, blog post, design doc, RFC, or LLD and wants to understand it. Also trigger on phrases like "explain this", "walk me through", "what does this PR do", "why is this failing", "what is this ticket about", "trace this call", or any time the user pastes a link or issue key expecting an explanation. Always fetch the source before explaining — never guess from partial text.
---

# Explain Anything

Explain as **story from zero context** — senior dev to first-week intern.

Decode/encode duality:
- **Decode (top → down)**: breadth-first from root. Never depth before parent understood.
- **Encode (bottom → up)**: chapter by chapter, each earning the next.

---

## Step 0 — Vault prior context (light, conditional)

Before fetching the source, try to resolve the repo from one of:
- `cwd` → `git remote get-url origin` → repo slug
- pasted Jira URL → board.json[task_id].repo
- pasted GitHub PR URL → repo from URL path

If repo resolves, read **last 30 lines** of `~/opensource/vault/wiki/projects/<repo>/decisions.md` and scan `~/opensource/vault/wiki/projects/<repo>/open-threads.md` for any reference to the artifact being explained (ticket ID, PR number, file paths from diff if available). If a relevant entry exists, surface inline at the top of the explanation:

```
↳ Prior context: <1-line citation from decisions.md or open-threads.md>
```

Skip silently if nothing relevant. NEVER block the explanation on this step. NEVER write DB files from this skill — explanations don't make decisions.

---

## Step 1 — Fetch source first

Always retrieve before explaining. Never guess.

| Source type | How to fetch |
|---|---|
| Jira ticket | Atlassian MCP (`getJiraIssue`) |
| GitHub PR/issue | GitHub MCP tools |
| Sentry error | Sentry MCP tools |
| PR code flows | GitHub MCP + `code-review-graph` MCP (`detect_changes_tool`, `get_affected_flows_tool`) |
| PR diff (raw) | `gh pr diff <number>` |
| Any URL | `WebFetch` / `curl` |
| Local file | `Read` directly |

**PR explanation:** Don't rely solely on diff. Use `code-review-graph` MCP for surrounding flows — confirms against actual runtime paths.

---

## Step 2 — Pick story arc

### Arc A — Bugs, errors, incidents
1. **What is this system?** — 1-2 lines, zero assumed context
2. **Happy path?** — what code does when nothing wrong
3. **What broke?** — observable symptom + trigger
4. **Why?** — root cause traced through code
5. **Fix / expected?** — what changes and why

Each chapter earns the next. Never jump to root cause without establishing "normal".

### Arc B — Design docs, RFCs, LLDs, PRs
1. **Problem?** — pain that motivated this
2. **State before?** — limitation, gap
3. **Change?** — solution at high level
4. **How?** — mechanism, key decisions, data flow
5. **Trade-offs?** — limitations, deferred decisions, risks

Don't explain mechanism before reader understands problem.

### Arc C — Shareable summary (handoff)
Use when "explain so I can tell someone", Slack/standup summary.
1. **TL;DR** — 3-5 sentences, copy-pasteable
2. **Full breakdown** — Arc A or B

---

## Step 3 — Cite everything

Every claim needs reference. No unsourced assertions.

- **Code**: `startLine:endLine:filepath` — snippet inline
- **Quotes**: attribute: *Jira ENG-12345:*, *GitHub PR #890:*
- **MCP fields**: call out field name
- **CI output**: excerpts for failures

Expected behaviour/fix/next steps quote mandatory. If absent in source, say so.

---

## Step 4 — Call-path tracing (when asked)

1. Full chain: `entrypoint → intermediate → target`
2. Snippet for both entrypoint and target call site
3. Direct or indirect (event/queue)?
4. One-line timeline:
   ```
   POST /apply → ApplyView → ApplyObject.submit_job() → validate_answers() → check_custom_rules()
   ```

Never isolated snippets — connect into one runtime story.

**Variant — data lineage / field tracing** (when a value is wrong at the output): follow the field forward layer by layer, annotating each assignment with `→ "value"`, marking the terminal node ✓/✗. Show broken path first, then fixed. See [examples/example-arc-d-data-lineage-field-tracing.md](examples/example-arc-d-data-lineage-field-tracing.md).

---

## Quality gate

Before sending:
- First-week intern understands every term?
- Reads as story (beginning → middle → end)?
- Every claim backed by quote/citation?
- Expected behaviour/fix quoted (or flagged absent)?
- Observed separate from inferred root cause?

If any "no" → fix first.

---

## Tone

- Plain English first, code second
- No jargon without one-line explanation
- Summarise before showing raw output
- Zero assumed context

---

## Examples

See `examples/`:
- [example-arc-a-be-developer-reading-fe-code.md](example-arc-a-be-developer-reading-fe-code.md) — Arc A bug fix; frontend→backend analogy table
- [examples/example-arc-d-data-lineage-field-tracing.md](examples/example-arc-d-data-lineage-field-tracing.md) — Step 4 variant; field tracing broken vs fixed path with ✓/✗

---

## Workflow ending

After explanation, offer next action based on source type:
- Bug/error → *"/work-on-jira-task to fix? /create-jira-ticket-with-reference to track?"*
- PR → *"/review-pr-architecture to review? /get-pr-ready-to-merge to address?"*
- Design doc/RFC → *"/create-tech-doc to document? /work-on-jira-task to implement?"*

If on a branch, run `work_hq append-context` with key findings from explanation.

**Vault writeback (Memory-only):** append one line to `~/opensource/vault/wiki/log.md`:
```
<ISO-ts> explain-anything: explained <source-type> <ref> via Arc <A|B|C>
```
Example: `2026-05-03T18:42 explain-anything: explained PR vscode#5821 via Arc B`.

If the explanation surfaced an unresolved question (user asked "wait, why is X?" with no answer in source), append H2 to `~/opensource/vault/wiki/projects/<repo>/open-threads.md` per the CLAUDE.md template. Otherwise skip.

NEVER write to `decisions.md` or `learnings.md` from this skill.

---

## Data Contract

### Reads (DB)
- `~/opensource/vault/wiki/projects/<repo>/decisions.md` — last 30 lines, only if repo resolves (Step 0)
- `~/opensource/vault/wiki/projects/<repo>/open-threads.md` — scan for ref to artifact, only if repo resolves (Step 0)
- `~/opensource/vault/wiki/projects/<repo>/code-conventions.md` — only when explaining code style/patterns

### Reads (Memory)
- `~/.claude/work_hq/board.json[task_id]` — if branch has an ENG-* ticket, used to resolve repo

### Writes (Memory)
- `~/opensource/vault/wiki/log.md` — one-line append per explanation
- `~/opensource/vault/wiki/projects/<repo>/open-threads.md` — append H2 only if unresolved question surfaces (per CLAUDE.md)

### Local (skill-only)
- (none)

### Live external (not stored)
- Atlassian MCP, GitHub MCP / `gh`, Sentry MCP, code-review-graph MCP, WebFetch — per Step 1 fetch table
