---
name: work-on-jira-task
description: Structured workflow for working on Jira tasks — fetches ticket details, creates feature branch, discovers context, collaboratively plans the implementation, then implements after approval. Use when the user provides a Jira ticket URL (e.g., https://eightfoldai.atlassian.net/browse/ENG-12345), says "let's work on ENG-XXXXX", "pick up this ticket", or pastes any eightfoldai.atlassian.net URL.
---

# Work on Jira Task

Understand → plan → implement. Order matters.

## Step 0 — Lazy-load context (auto)

Before fetching the ticket, auto-fire `Skill(skill="project-context", args="branch:read")`. This loads any existing branch + project context for the current branch (so we don't re-discover what was already known). If nothing exists yet, that's fine — it returns a "seed me" message and we proceed.

**Cross-repo sibling check:** after branch:read transitively loads the parent project, scan its `## Branches in flight` list. If any sibling branch is in a DIFFERENT repo than current `pwd` AND its PR is still open (not merged), surface ONCE:

```
↳ sibling work in flight: <repo>:<branch> → PR #<n> (<state>). Load that branch's context for cross-reference?
```

Default no — wait for user. Skip if no project, no siblings, or all siblings are merged.

## Step 1 — Fetch ticket

Extract ticket ID. Atlassian MCP `getJiraIssue` (cloudId: `eightfoldai.atlassian.net`). Display summary, description, acceptance criteria, linked docs.

**IMPL-\*:** Check `issuelinks` for linked ENG-\*. None → tell user to transition IMPL to "Code Fix Needed". No branch without ENG number.

## Step 2 — Branch

`akshat/ENG-<number>-<short-name>` (always ENG; 2-4 word suffix)

```bash
git checkout master && git pull origin master
git checkout -b akshat/ENG-[NUMBER]-[short-name]
```

Stacked: `git checkout -b akshat/ENG-[NUMBER]-[short-name] [parent-branch]`

Create only. No push yet.

## Step 3 — Discover context

1. Grep repo for ticket ID/keywords
2. Check subdirs matching domain
3. Confluence via MCP if ticket links page
4. Fetch linked design docs/PRs

"See X for pattern" / "matches how Y works" → read references immediately. Simplest way to apply same pattern. Vague mentions ≠ refactoring scope.

**Inline context provided** → merge with findings, skip asking for more.
**No inline context + broad scope** → ask for class/component/file/CSS class to start from.

## Step 3.5 — Check existing plan

Check both before writing new:
1. `~/.claude/plans/tickets/{TICKET_ID}.md`
2. `~/.claude/projects/.../branches/{branch_name}/`

Exists → display, ask reuse or new. No plan → Step 4.

**Always persist** to `~/.claude/plans/tickets/{TICKET_ID}.md` immediately on create/modify.

## Step 4 — Plan

No production code yet. Plain English first, code second. Save plan immediately (`mkdir -p`) before asking user review.

Use template from [references/plan-template.md](references/plan-template.md).

**Scope gate:** Ticket mentions APIs "not ready", wiring "handled by team", patterns to "match" → state IN scope vs deferred, confirm before full plan.

*"Does this approach make sense? Anything to adjust?"* — do not implement until explicit approval.

## Step 5 — Implement

Follow approved plan. Deviate only if unexpected — explain first.

- Only modify ticket-relevant files
- Stacked: `git diff [parent-branch] --name-only` to verify no drift

For code conventions (method ordering, imports, testing, docs): read [references/code-conventions.md](references/code-conventions.md).

Grep codebase before inventing. Match existing patterns.

### Test before declaring done

Before Step 6 (commit + PR), do this in order:

1. **Identify test files** for the code being changed:
   - vscode → look for `*.test.ts(x)`, `*.spec.ts(x)`, or `__tests__/` adjacent to each modified file
   - wipdp → look for `tests/test_<modname>.py` or `tests/<area>/test_*.py`
   - **If none exist** → record once in branch context: `↳ saved to branch context: no test files for <component> — skipped test run` and skip to step 4.

2. **Do NOT run lint on EC2** — pre-commit hook (vscode: husky; wipdp: ruff) handles lint before commit. EC2 time is for actual tests, not lint.

3. **Run identified tests**:
   - vscode → invoke `/run-on-ec2` (mandatory if test files exist AND VPN is up). If VPN down or EC2 unreachable → record `↳ saved to branch context: EC2 unreachable, tests deferred — risk: <test files>` and proceed.
   - wipdp → local pytest is sufficient.

4. **Surface manual verification** — if branch context has a `## Test Environment` section with sandbox URL + nav steps, surface them: "Verify manually at <sandbox>: <steps>" before declaring done. Do not block — just remind.

The skill never claims "tests passing" without evidence. "No test files exist" or "infra unavailable" are valid skip reasons ONLY when recorded in branch context.

## Step 6 — Commit and PR

Show: (1) files to stage, (2) commit message, (3) PR description. Single approval → add+commit+push+`/submit-pr` without pausing.

```bash
git add <file1> <file2> ...     # ticket-relevant only
git commit -m "ENG-XXXXX: Brief summary

What changed and why.
Fixes IMPL-XXXXXX."

git push -u origin <branch>
```

**Auto-detect repo** via `git remote get-url origin`:
- **wipdp** → prose: Summary (2-4 sentences) + JIRA TASK + TEST PLAN (bash block). Write to temp file, use `--body-file`.
- **vscode** → `/submit-pr` (own checklist)

After push: *"Ready? I'll run `/submit-pr`."*

---

## Passive context updates throughout

Per the passive-context-updates feedback rule (auto-loaded via MEMORY.md), invoke `Skill(skill="project-context", args="branch:update <info>")` immediately whenever you learn a material fact during this skill — a key file, a root cause, a design decision. Notify via one-liner `↳ saved to branch context: ...`. For scope-changing findings, also `project:update`. Never ask first.

## Workflow ending

```
───── workflow ─────
✓ Ticket: ENG-XXXXX
✓ Branch: akshat/ENG-XXXXX-short-name
✓ Implemented + tests passing
→ Next: /submit-pr (which will auto-add PR to /pr-watcher)
────────────────────
```

PR watching is handled by `/submit-pr` — no separate step here.
