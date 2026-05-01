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

If on a branch, run `/project-context:update` with key findings from explanation.
