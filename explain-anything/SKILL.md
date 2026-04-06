---
name: explain-anything
description: Explain any reference as a zero-context story with citations and call-path tracing. Use when the user shares a Jira ticket, GitHub PR or issue, Sentry error, Slack thread, URL, blog post, design doc, RFC, or LLD and wants to understand it. Also trigger on phrases like "explain this", "walk me through", "what does this PR do", "why is this failing", "what is this ticket about", "trace this call", or any time the user pastes a link or issue key expecting an explanation. Always fetch the source before explaining — never guess from partial text.
---

# Explain Anything

Explain any reference as a **story that builds from zero context** — not a technical dump. Think senior dev explaining to a first-week intern.

This skill runs on the same decode/encode duality as `create-tech-doc`:

- **Decode (top → down)**: traverse the source breadth-first — start at the root (what is this system?) before descending into specifics (what broke, why, what's the fix). Never jump into depth before the parent level is understood.
- **Encode (bottom → up)**: build the explanation chapter by chapter, each one earning the next. Never deliver a chapter until the prior one is solid. Assemble the full story only once all pieces are clear.

The story arcs below are the decode map. The "each chapter earns the next" rule is the encode constraint.

---

## Step 1 — Fetch the source first

Always retrieve the content before explaining. Never guess from partial text in the chat.

| Source type | How to fetch |
|---|---|
| Jira ticket / URL | Atlassian MCP tools (`getJiraIssue`) |
| GitHub PR / issue | GitHub MCP tools |
| Sentry error | Sentry MCP tools |
| Any URL (blog, doc, Slack archive, tweet) | `WebFetch` / `curl` |
| Local file in codebase | `Read` the file path directly |

---

## Step 2 — Pick the right story arc

### Arc A — Bugs, errors, and incidents

Use when the source is a Sentry error, a failing CI check, an incident report, or a bug ticket.

1. **What is this feature/system?** — 1–2 lines, zero assumed context
2. **What is the happy path?** — what the code does when nothing is wrong
3. **What broke and when?** — observable symptom and trigger condition
4. **Why does it break?** — root cause traced through the code
5. **What is the fix / what is expected?** — what changes and why it restores correctness

Each chapter earns the next. Never jump to root cause without establishing "normal" first. Never jump to solutions without establishing context first.

---

### Arc B — Design docs, RFCs, LLDs, feature tickets, PRs

Use when the source is describing something new being built or proposed.

1. **What problem does this solve?** — the pain that motivated this, in plain terms
2. **What was the state before?** — existing system, current limitation, or gap
3. **What is the proposed/implemented change?** — the solution at a high level
4. **How does it work?** — mechanism, key design decisions, data flow
5. **What are the trade-offs or open questions?** — limitations, deferred decisions, risks called out

Each chapter earns the next. Don't explain the mechanism before the reader understands the problem it's solving.

---

## Step 3 — Cite everything

Every claim needs a reference. No unsourced assertions.

- **Code citations** — `startLine:endLine:filepath` — include the snippet inline so the user can navigate directly
- **Direct quotes** from the source — attribute clearly: *Jira ENG-12345:*, *GitHub PR #890:*, *Sentry event abc123:*
- **MCP-fetched fields** (status, assignee, priority, stack trace) — call out the field name
- **CI output excerpts** for build/test failures

The **expected behaviour / fix / next steps** quote is mandatory. If the source doesn't state one, say so explicitly — don't invent it.

---

## Step 4 — Call-path tracing (when asked)

When the user asks "where is this called?" or "when does this run?":

1. Show the full chain: `entrypoint → intermediate calls → target method`
2. Include a snippet for both the entrypoint and the target call site
3. State whether the call is **direct** or **indirect** (e.g. via event/queue)
4. One-line timeline format:
   ```
   POST /apply → ApplyView → ApplyObject.submit_job() → validate_answers() → check_custom_rules()
   ```

Never answer with isolated snippets — always connect them into one runtime story.

---

## Quality gate

Before sending, verify:
- [ ] Would a first-week intern understand every term without prior context?
- [ ] Does the explanation read like a story (beginning → middle → end)?
- [ ] Is every claim backed by a quote or code citation?
- [ ] Is the expected behaviour / fix explicitly quoted (or explicitly flagged as absent)?
- [ ] Is observed behaviour kept separate from inferred root cause?

If any is "no", fix it first.

---

## Tone

- Plain English first, code second
- No jargon without a one-line explanation
- Summarise lists and tables before showing raw output
- Zero assumed context unless the user explicitly says otherwise

---

## Examples

See the `examples/` files in this skill directory for reference explanations:

- [example-arc-a-be-developer-reading-fe-code.md](example-arc-a-be-developer-reading-fe-code.md) — Arc A bug fix explained to a backend developer; includes frontend→backend analogy table
