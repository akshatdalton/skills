---
name: work-on-jira-task
description: Structured workflow for working on Jira tasks — fetches ticket details, creates feature branch, discovers context, collaboratively plans the implementation, then implements after approval. Use when the user provides a Jira ticket URL (e.g., https://eightfoldai.atlassian.net/browse/ENG-12345), says "let's work on ENG-XXXXX", "pick up this ticket", or pastes any eightfoldai.atlassian.net URL.
---

# Work on Jira Task

Understand → plan → implement. Order matters.

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

Tests via `/run-on-ec2`. Fix lint after implementing.

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

## Workflow ending

Before completing, run `/project-context:update` with key decisions, relevant files discovered, and approach taken.

```
───── workflow ─────
✓ Ticket: ENG-XXXXX
✓ Branch: akshat/ENG-XXXXX-short-name
✓ Implemented + tests passing
→ Next: /submit-pr
────────────────────
```
