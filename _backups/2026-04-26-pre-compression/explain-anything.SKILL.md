---
name: explain-anything
description: Explain any reference as a zero-context story with citations and call-path tracing. Use when the user shares a Jira ticket, GitHub PR or issue, Sentry error, Slack thread, URL, blog post, design doc, RFC, or LLD and wants to understand it. Also trigger on phrases like "explain this", "walk me through", "what does this PR do", "why is this failing", "what is this ticket about", "trace this call", or any time the user pastes a link or issue key expecting an explanation. Always fetch the source before explaining — never guess from partial text.
---

# Explain Anything

Explain as **story building from zero context** — not technical dump. Senior dev explaining to first-week intern.

Runs on decode/encode duality:
- **Decode (top → down)**: breadth-first from root (what is this system?) before specifics (what broke, why, fix). Never depth before parent level understood.
- **Encode (bottom → up)**: build chapter by chapter, each earning the next. Never deliver chapter until prior one solid.

---

## Step 1 — Fetch source first

Always retrieve content before explaining. Never guess from partial text.

| Source type | How to fetch |
|---|---|
| Jira ticket / URL | Atlassian MCP (`getJiraIssue`) |
| GitHub PR / issue | GitHub MCP tools |
| Sentry error | Sentry MCP tools |
| GitHub PR (code flows) | GitHub MCP + `code-review-graph` MCP (`detect_changes_tool`, `get_affected_flows_tool`) |
| GitHub PR diff (raw) | `gh pr diff <number>` |
| Any URL | `WebFetch` / `curl` |
| Local file | `Read` directly |

**PR explanation:** Don't rely solely on diff. Use `code-review-graph` MCP to understand surrounding code flows — confirms explanation against actual runtime paths, not just text delta.

---

## Step 2 — Pick story arc

### Arc A — Bugs, errors, incidents
1. **What is this feature/system?** — 1-2 lines, zero assumed context
2. **What is the happy path?** — what code does when nothing wrong
3. **What broke and when?** — observable symptom and trigger
4. **Why does it break?** — root cause traced through code
5. **What is the fix / expected?** — what changes and why it restores correctness

Each chapter earns the next. Never jump to root cause without establishing "normal" first.

### Arc B — Design docs, RFCs, LLDs, feature tickets, PRs
1. **What problem does this solve?** — pain that motivated this
2. **State before?** — existing system, limitation, gap
3. **Proposed/implemented change?** — solution at high level
4. **How does it work?** — mechanism, key decisions, data flow
5. **Trade-offs or open questions?** — limitations, deferred decisions, risks

Don't explain mechanism before reader understands problem.

### Arc C — Shareable summary (handoff mode)
Use when user says "explain so I can tell someone", wants Slack/standup summary.
1. **TL;DR** — 3-5 sentences. Copy-pasteable to Slack/standup.
2. **Full breakdown** — Arc A or B as appropriate

---

## Step 3 — Cite everything

Every claim needs a reference. No unsourced assertions.

- **Code**: `startLine:endLine:filepath` — include snippet inline
- **Direct quotes**: attribute clearly: *Jira ENG-12345:*, *GitHub PR #890:*
- **MCP-fetched fields**: call out field name
- **CI output**: excerpts for build/test failures

Expected behaviour/fix/next steps quote is mandatory. If source doesn't state one, say so explicitly.

---

## Step 4 — Call-path tracing (when asked)

1. Show full chain: `entrypoint → intermediate calls → target method`
2. Include snippet for both entrypoint and target call site
3. State whether call is **direct** or **indirect** (via event/queue)
4. One-line timeline:
   ```
   POST /apply → ApplyView → ApplyObject.submit_job() → validate_answers() → check_custom_rules()
   ```

Never answer with isolated snippets — connect into one runtime story.

---

## Quality gate

Before sending, verify:
- [ ] First-week intern understands every term without prior context?
- [ ] Reads like story (beginning → middle → end)?
- [ ] Every claim backed by quote or code citation?
- [ ] Expected behaviour/fix explicitly quoted (or flagged as absent)?
- [ ] Observed behaviour separate from inferred root cause?

If any "no", fix first.

---

## Tone

- Plain English first, code second
- No jargon without one-line explanation
- Summarise lists/tables before showing raw output
- Zero assumed context unless user explicitly says otherwise

---

## Examples

See `examples/` in this skill directory:
- [example-arc-a-be-developer-reading-fe-code.md](example-arc-a-be-developer-reading-fe-code.md) — Arc A bug fix for backend developer; includes frontend→backend analogy table
