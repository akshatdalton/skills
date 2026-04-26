---
name: work-on-jira-task
description: Structured workflow for working on Jira tasks — fetches ticket details, creates feature branch, discovers context, collaboratively plans the implementation, then implements after approval. Use when the user provides a Jira ticket URL (e.g., https://eightfoldai.atlassian.net/browse/ENG-12345), says "let's work on ENG-XXXXX", "pick up this ticket", or pastes any eightfoldai.atlassian.net URL.
---

# Work on Jira Task

Sequence: understand fully → plan fully → implement. Order matters.

---

## Step 1 — Fetch ticket

Extract ticket ID. Use Atlassian MCP `getJiraIssue` (cloudId: `eightfoldai.atlassian.net`). Display: summary, description, acceptance criteria, linked docs/tickets.

**IMPL-\* ticket:** Check `issuelinks` for linked ENG-\*. If none exists, tell user to transition IMPL to "Code Fix Needed" first (auto-creates ENG ticket). Do not create branch without ENG number.

---

## Step 2 — Create feature branch

Format: `akshat/ENG-<ticket_number>-<very-short-name>` (always ENG, never IMPL; 2-4 word suffix)

**From master (default):**
```bash
git checkout master
git pull origin master
git checkout -b akshat/ENG-[NUMBER]-[short-name]
```

**Stacked (user says "keep current branch as base"):**
```bash
git checkout -b akshat/ENG-[NUMBER]-[short-name] [parent-branch]
```

Create branch only. Do not push yet.

---

## Step 3 — Discover context

Search before planning. Understand what exists before writing anything.

1. Grep repo for ticket ID or keywords from summary
2. Check subdirectories matching ticket's domain
3. Check Confluence via Atlassian MCP if ticket links to a page
4. Fetch linked design docs or PRs

When ticket says "see X for the pattern" or "matches how Y works": read those references immediately. Identify simplest way to apply same pattern. Default to minimal extension — vague mentions (e.g. "wiring already exists") do not imply refactoring scope.

Present findings: `Here's what I found as relevant context: [list]`

**If user provided inline context** alongside ticket URL: merge with search results, skip asking for more.

**If no inline context and scope is broad** (large shared module, no file-level hints): ask for a class name, component, file path, or CSS class to start from. Skip if scope already clear.

---

## Step 3.5 — Check for existing plan

Check both locations before writing new plan:
```
1. ~/.claude/plans/tickets/{TICKET_ID}.md
2. ~/.claude/projects/.../branches/{branch_name}/
```

**Plan exists:** Read and display. Ask: "Use existing plan, or create new one?"
- **Reuse** → skip to Step 5
- **New** → proceed to Step 4 (overwrite file at end)

**No plan:** proceed to Step 4.

**Always persist plans** to `~/.claude/plans/tickets/{TICKET_ID}.md` immediately when created or modified. Never leave plan only in conversation.

---

## Step 4 — Plan before implementing

Stop and plan. No production code yet. Write like colleague explaining to another engineer — plain English first, code second.

**Save plan immediately** to `~/.claude/plans/tickets/{TICKET_ID}.md` before asking user for review. Use `mkdir -p`.

```markdown
# [Feature/Fix Name] — Implementation Plan

## What We're Building
[Plain English: what problem, why?]

## Starting Point: What Already Exists
[Infrastructure, patterns, files — with file:line references]

## The Approach
[Core design decision and why — mention alternatives considered]

## Implementation Details

### [Component 1]
[What it does and why]

```python
# Actual approach, not pseudocode
def example(arg):
    # Comments on non-obvious decisions
    return result
```

**Why this way:** [Rationale for non-obvious parts]

## Testing Strategy
**What we're testing:** [our logic — transformations, error handling, edge cases]
**What we're NOT testing:** [framework behaviour, dataclass construction, etc.]

## Files to Create / Modify
- `path/to/file.py` — [what and why]

## Known Limitations
[Deferred work, accepted trade-offs]
```

**Scope gate:** If ticket mentions APIs "not yet ready", wiring "handled by the team", or patterns to "match" — state what is IN scope vs deferred, ask user to confirm before writing full plan.

After presenting: *"Does this approach make sense? Anything to adjust before I start?"*

Update plan file immediately on changes. **Do not implement until user explicitly approves.**

---

## Step 5 — Implement

Follow approved plan exactly. Deviate only if unexpected — explain before changing course.

**Scope discipline:**
- Only modify ticket-relevant files
- If stacked: `git diff [parent-branch] --name-only` to verify no drift into parent's files

**Code conventions (`operator_platform` — Python):**
- Method ordering: constructor → public → private (`_` prefix)
- Tightly coupled helpers: `@staticmethod` inside class, not module-level
- Shared enums/types: in base classes, not per-implementation files
- Module-private constants: `_` prefix
- `from mock import patch` (not `unittest.mock`)
- `datetime.now(UTC)` (not deprecated `datetime.utcnow()`)
- Dataclasses for structured return values over raw dicts
- Keyword arguments for calls with >1 parameter
- No `from __future__ import absolute_import`

**Documentation:**
- Module docstrings: skip
- Class docstrings: architecture intent ("Why") only
- Method docstrings: only for non-obvious contracts
- Test docstrings: never

**Testing:**
- Before each test: what distinct behavior breaks without it? No answer → don't write it.
- One behavior = one test. Never same check twice with different inputs.
- Collapse redundant cases: mixed-input test replaces separate tests proving both sides.
- Cover: (1) happy path, (2) no-op/backwards-compat path, (3) new data contracts.
- Skip: framework behaviour, dataclass construction, wiring-only tests.
- Class-level decorators over per-test repetition.

**Patterns first:** Grep codebase before inventing. Match existing import style, logging, abstractions (`settings.x` over `os.getenv('X')`).

After implementing: run tests, fix lint errors.

**Running tests — EC2 required:** Use `/run-on-ec2` for all test execution.

---

## Step 6 — Commit and PR

Show user: (1) files to stage, (2) proposed commit message, (3) proposed PR description. Ask for single approval to run add+commit+push+/submit-pr together. After approval, run all four without pausing.

```bash
git add <file1> <file2> ...     # only ticket-relevant — never git add .
git commit -m "ENG-XXXXX: Brief summary

What changed and why.
Fixes IMPL-XXXXXX."             # include if from customer IMPL ticket

git push -u origin <branch>    # or git push if already tracking
```

**Auto-detect repo for PR format** via `git remote get-url origin`:
- **wipdp** → prose format below
- **vscode** or other → use `/submit-pr` (has own checklist format)

**PR description — wipdp repo:**
```
## Summary

[2–4 sentences of prose. What changed and why — key files/components and motivation.]

## JIRA TASK:
https://eightfoldai.atlassian.net/browse/ENG-XXXXX

## TEST PLAN:
[runnable bash block for backend changes]
```

Write body to temp file, pass `--body-file` to `gh pr create` — never interpolate backtick-containing markdown into shell string.

TEST PLAN is runnable bash block. For blocked infrastructure deps, append plain-text note after block.

Do not raise PR unless user approves. If PR already exists for branch, skip creation and mention it.

**After commit + push, always offer:** *"Ready to create the PR? I'll run `/submit-pr`."*
