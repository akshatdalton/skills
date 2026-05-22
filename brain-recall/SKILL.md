---
name: brain-recall
description: Use when the user fires `/brain-recall` alongside or before any state-machine skill (work-on-jira-task, submit-pr, get-pr-ready-to-merge, ship-task) — or any time they want project context loaded into the session. Resolves the active project from cwd / branch / ticket arg, reads `~/opensource/vault/wiki/projects/<project>/learnings.md` (the project brain), and reads `progress/<ticket>/progress.md` + `progress/<ticket>/plan.md` if a ticket is in scope. READ-ONLY — never writes. Pairs with `/brain-ingest`.
---

# /brain-recall (v0.1)

## Purpose

Stateless skills lose context across `/clear`. `/brain-recall` is the read-side of Akshat's vault brain — load the relevant `learnings.md`, `progress/<ticket>/progress.md`, and `progress/<ticket>/plan.md` into the session so whatever skill fires next has full project + task context.

**Never writes.** Read-only. Pair with `/brain-ingest` for the write side.

## Vault layout (v0.1)

```
~/opensource/vault/wiki/
  CLAUDE.md, index.md                                    # standing instructions + catalog
  projects/
    vscode/                                              # active v0 project (control plane)
      learnings.md                                       # the brain (project overview, runbooks, conventions, decisions, initiatives)
      progress/
        <ticket>/                                        # per-ticket directory
          progress.md                                    # task state + in-flight learnings
          plan.md                                        # original plan from ~/.claude/plans/ (if any)
        archive/
          <ticket>/                                      # merged tickets — still readable for adjacent future work
            progress.md
            plan.md
    wipdp/                                               # active v0 project (data plane)
      learnings.md
      progress/<ticket>/{progress.md, plan.md}
      progress/archive/<ticket>/{progress.md, plan.md}
  _archive/                                              # pre-v0 vault — do not read
```

Active v0 projects: **vscode** and **wipdp** ONLY. magnetx, magnetx-landing, claude-code-sessions, tweet-analysis are out of scope until v0 stabilizes.

## Invocation forms

| Form | Behavior |
|---|---|
| `/brain-recall` | Auto-resolve project from cwd. If branch matches `akshat/ENG-XXXXX-*`, also load the ticket's progress + plan. |
| `/brain-recall ENG-XXXXX` | Explicit ticket. Resolve project by checking which project's `progress/<ticket>/` directory exists. Load learnings, progress, and plan. |
| `/brain-recall <project>` | Load project's `learnings.md` only. Useful when reading without ticket context. |
| `/brain-recall <PR URL or Jira URL>` | Extract ticket → resolve project → load everything. |

## Read order

1. **Resolve `<project>`** (first hit wins):
   - cwd → `git remote get-url origin` → repo slug (`vscode` or `wipdp`)
   - ticket arg `ENG-\d+` → check `~/opensource/vault/wiki/projects/{vscode,wipdp}/progress/<ticket>/` and `progress/archive/<ticket>/` for existence; whichever path contains the directory determines the project (single source of truth).
   - branch name `akshat/ENG-XXXXX-*` → same as above
   - user-pasted artifact URL → extracted ticket → directory lookup
   - Fallback only if directory not found: `~/.claude/work_hq/board.json[task_id].repo` (deprecated; will be removed)

   If no resolution and no explicit `<project>`, ask which project (vscode or wipdp), or load global `CLAUDE.md` only.

2. **Read `~/opensource/vault/wiki/projects/<project>/learnings.md`** — the project brain (overview, runbooks, conventions, decisions, initiatives).

3. **If a ticket is in scope, probe the ticket directory with explicit filesystem checks** (mandatory — never skip or infer absence from memory):
   - Run: `ls ~/opensource/vault/wiki/projects/<project>/progress/<ticket>/`
   - If that returns nothing or errors, run: `ls ~/opensource/vault/wiki/projects/<project>/progress/archive/<ticket>/`
   - Only after BOTH commands return nothing should you conclude "no progress directory yet for <ticket>".
   - Once the directory is located, read:
     - `progress.md` — active task state + in-flight learnings
     - `plan.md` — initial plan from `/work-on-jira-task` (if exists)

4. **Surface as prose summary in the session**:
   - One short paragraph: what this project is, what's active, what's relevant from learnings to the user's current task (if discernible).
   - List which files were read with paths.
   - If progress file exists: surface the current state (state field), what's been done, what's next.
   - If plan file exists: highlight the plan structure (sections / step list).
   - If user gave an artifact (Jira/PR URL), fetch its content (`gh pr view`, `mcp__claude_ai_Atlassian__getJiraIssue`) and weave into the summary.

5. **Never write anything.**

## What NOT to read

- `~/opensource/vault/wiki/_archive/**` — pre-v0 vault; ignore even if relevant.
- `~/.claude/work_hq/**` — operational state, not knowledge (single-source-of-truth is the vault).
- `~/.claude/sessions/**`, `~/.claude/history.jsonl` — raw inputs for `/brain-ingest`, not for recall.
- Auto-memory `~/.claude/projects/<encoded-cwd>/memory/` — fallback only. Only surface if a fact isn't in `learnings.md`, and prefix with `↳ note: read from auto-memory fallback (<path>) — vault gap`.

## Output structure

```
**Project:** <vscode|wipdp>
**Read:**
- `projects/<project>/learnings.md`
- `projects/<project>/progress/<ticket>/progress.md` (or "no progress yet")
- `projects/<project>/progress/<ticket>/plan.md` (or "no plan recorded")

**Project snapshot:**
<2-4 sentences from learnings.md — what this project is, what's most relevant>

**Task context (if ticket in scope):**
- State: <state from frontmatter>
- Branch / PR: <values from frontmatter>
- Done so far: <summary from progress.md body>
- Next: <next-action signals from progress.md>

**From the plan (if exists):**
<key bullets from plan.md — what was decided to build, in what order>

**Relevant prior learnings:**
- <bulleted, cited to specific section anchors in learnings.md>

**Next suggested step:**
<one line — typically the state-machine skill to fire next>
```

## Pairs with

- `/brain-ingest <ticket>` — write side. Distills the current session into `progress/<ticket>/progress.md`; on first ingest, copies any matching plan from `~/.claude/plans/` to `progress/<ticket>/plan.md`. Fire after state-machine skill sessions end.
- `/brain-ingest` (no arg) — catch-up sweep using `.brain-ingest-state.json` `last_sync_timestamp`.
