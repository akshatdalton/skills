---
name: work-on-jira-task
description: Structured workflow for working on Jira tasks — fetches ticket details, creates feature branch, discovers context, collaboratively plans the implementation, then implements after approval. Use when the user provides a Jira ticket URL (e.g., https://eightfoldai.atlassian.net/browse/ENG-12345), says "let's work on ENG-XXXXX", "pick up this ticket", or pastes any eightfoldai.atlassian.net URL.
---

# Work on Jira Task

Structured workflow from Jira ticket to committed implementation. The sequence matters: understand fully before planning, plan fully before implementing.

---

## Step 1 — Fetch and understand the ticket

Extract the ticket ID from the URL or user input. Use Atlassian MCP `getJiraIssue` (cloudId: `eightfoldai.atlassian.net`) to fetch full details. Read and display:
- Summary and description
- Acceptance criteria
- Any linked docs, design docs, or related tickets

**If the ticket is IMPL-\*:** Check `issuelinks` for a linked ENG-\* issue — you'll need it for branch naming and the PR. If no ENG ticket exists yet, let the user know they need to transition the IMPL ticket to "Code Fix Needed" first (this auto-creates the ENG ticket). Do not create the branch until you have the ENG number.

---

## Step 2 — Create the feature branch

Branch naming: `akshat/ENG-<ticket_number>-<very-short-name>`

- Always use the **ENG ticket number** (not IMPL)
- Suffix: 2–4 words, hyphenated, describes the change
- Examples: `akshat/ENG-187846-notes-btn-fix`, `akshat/ENG-186208-text-normalization`

**Default — branch from master:**
```bash
git checkout master
git pull origin master
git checkout -b akshat/ENG-[NUMBER]-[short-name]
```

**Stacked — branch from another feature branch** (when user says "keep current branch as base"):
```bash
git checkout -b akshat/ENG-[NUMBER]-[short-name] [parent-branch]
```

Only create the branch. Do not push yet.

---

## Step 3 — Discover context

Search for relevant context before planning. The goal is to understand what already exists before writing anything.

**Search strategy:**
1. Grep the repo for the ticket ID or keywords from the ticket summary
2. Look in subdirectories matching the ticket's domain
3. Check Confluence via Atlassian MCP if the ticket links to a page
4. Fetch any linked design docs or PRs

When the ticket says "see X for the pattern" or "matches how Y works":
- Read those reference files immediately as part of context discovery.
- Identify the simplest way to apply the same pattern to this ticket.
- Default to minimal extension. Do not infer additional scope from vague mentions (e.g. "wiring already exists" ≠ refactor the wiring).

After searching, ask the user:
```
Here's what I found as relevant context:
[list discovered files / docs]

Do you have any additional resources (tech docs, design docs, related PRs) that would help?
```

**If the search scope is broad** — e.g. the ticket touches a large shared module, or the description gives no file-level hints — also ask:
```
Do you have a class name, component, file path, or CSS class I should start from?
Even a rough hint cuts exploration time significantly.
```
Skip this question if the scope is already clear from the ticket or your initial search.

---

## Step 3.5 — Check for existing plan

Before writing a new plan, check if one already exists for this ticket:

```
Plan path: ~/.claude/plans/tickets/{TICKET_ID}.md
Example:   ~/.claude/plans/tickets/ENG-188357.md
```

**If a plan file exists:**
- Read it and display it to the user
- Ask: "I found an existing plan for this ticket. Use it, or create a new one?"
  - **Reuse** → skip to Step 5 (Implement) with this plan as the source of truth
  - **New** → proceed to Step 4 (overwrite the file at the end)

**If no plan file exists:** proceed to Step 4 normally.

---

## Step 4 — Plan before implementing

Once context is gathered, **stop and plan**. Do not write production code yet.

Write the full plan as a structured document using the template below. Write it like a colleague explaining to another engineer — plain English first, code second. Show, don't just list.

**Save the plan immediately to `~/.claude/plans/tickets/{TICKET_ID}.md` as soon as it is written — before asking the user for review.** The file must be written even if the session ends or the user defers implementation. Use `mkdir -p` to ensure the directory exists.

```markdown
# [Feature/Fix Name] — Implementation Plan

## What We're Building
[Plain English: what problem does this solve and why?]

## Starting Point: What Already Exists
[Infrastructure, patterns, files this builds on — with file:line references]

## The Approach
[Core design decision and why — mention alternatives considered]

## Implementation Details

### [Component 1]
[What it does and why it's needed]

```python
# Actual approach, not pseudocode
def example(arg):
    # Comments on non-obvious decisions
    return result
```

**Why this way:** [Rationale for non-obvious parts]

[Continue per component...]

## Testing Strategy
**What we're testing:** [our logic — transformations, error handling, edge cases]
**What we're NOT testing:** [framework behaviour, dataclass construction, etc.]

## Files to Create / Modify
- `path/to/file.py` — [what and why]

## Known Limitations
[Deferred work, accepted trade-offs]
```

**Scope gate:** If the ticket mentions APIs "not yet ready", wiring "handled by the team", or patterns to "match" — state in one sentence what is IN scope vs deferred and ask the user to confirm before writing the full plan. This prevents a full round-trip on the wrong scope.

After presenting: *"Does this approach make sense? Anything to adjust before I start?"*

If the user requests changes, update the plan file immediately before responding, then display the updated plan.

**Do not implement until the user explicitly approves.**

---

## Step 5 — Implement

Follow the approved plan exactly. Deviate only if you hit something unexpected — and explain it before changing course.

**Scope discipline:**
- Only modify files relevant to this ticket
- If stacked: `git diff [parent-branch] --name-only` to verify you haven't drifted into the parent's files

**Code conventions (`operator_platform` — Python):**
- Method ordering: constructor → public → private (`_` prefix)
- Helpers tightly coupled to a class: `@staticmethod` inside, not module-level
- Shared enums/types: in base classes, not per-implementation files
- Module-private constants: `_` prefix
- `from mock import patch` (not `unittest.mock`)
- `datetime.now(UTC)` (not deprecated `datetime.utcnow()`)
- Dataclasses for structured return values over raw dicts
- Keyword arguments for calls with >1 parameter
- No `from __future__ import absolute_import` (Python 2 shim, meaningless in 3.11+)

**Documentation:**
- Module docstrings: skip
- Class docstrings: architecture intent ("Why") only, never "What"
- Method docstrings: only for non-obvious contracts
- Test docstrings: never

**Testing:**
- Before writing each test, ask: what distinct behavior breaks if this test doesn't exist? If you can't answer, don't write it.
- One behavior = one test. Never write the same logical check twice with different inputs.
- Collapse redundant cases: a mixed-input test (e.g. old + new objects in one run) replaces separate "skips old" and "includes new" tests — it proves both sides at once.
- Cover: (1) the happy path of new logic, (2) the no-op / backwards-compat path (nil input → original behavior unchanged), (3) any new data contracts (metadata fields downstream consumers depend on).
- Skip: framework behaviour (Pydantic validation, boto3/Django calls), dataclass construction, wiring tests that only assert a mock was called.
- Class-level decorators over per-test repetition.

**Patterns first:** Grep the codebase before inventing. Match existing import style, logging patterns, and abstractions (`settings.x` over `os.getenv('X')`).

After implementing: run tests and fix any lint errors before presenting to the user.

---

## Step 6 — Commit

Show the user:
1. The list of files to be staged
2. The proposed commit message

Then say you'll run `git add + commit + push` together and wait for one explicit approval. After approval, run all three without pausing.

```bash
git add <file1> <file2> ...     # stage only ticket-relevant files — never git add .
git commit -m "ENG-XXXXX: Brief summary

What changed and why.
Fixes IMPL-XXXXXX."             # include Fixes line if from a customer IMPL ticket

git push -u origin <branch>    # or git push if already tracking
```

Do not push unless the user approves. After pushing, let the user know it's ready for `/submit-pr` when they want to raise the PR.
