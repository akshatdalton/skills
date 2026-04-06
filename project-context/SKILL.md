---
name: project-context
description: Store and retrieve per-branch project context — ticket details, relevant files, key findings, decisions, test environment. Use /project-context:read to surface context for the current branch, /project-context:update to save new context.
---

# Project Context

Per-branch context storage. Each branch gets a structured markdown file under `memory/branches/` in the active project's memory directory.

**Sub-commands:**
- `/project-context:read` — surface context for the current branch
- `/project-context:update <info>` — create or update context for the current branch

---

## How to invoke

The user will call either `/project-context:read` or `/project-context:update`. Look at the sub-command suffix after the `:` to decide which flow to run.

---

## Common: detect the branch and resolve the context file path

```bash
git rev-parse --abbrev-ref HEAD
```

Take the branch name (e.g. `akshat/ENG-187846-notes-btn-fix`) and derive a safe filename:
- Strip the `akshat/` prefix (or any `user/` prefix)
- Replace remaining `/` with `-`
- Append `.md`

Example: `akshat/ENG-187846-notes-btn-fix` → `ENG-187846-notes-btn-fix.md`

Context file lives at:
```
~/.claude/projects/-Users-akshat-v-eightfold-vscode/memory/branches/<filename>
```

---

## /project-context:read

1. Detect the branch and resolve the context file path (see above).
2. Check if the file exists.
   - **Exists** → Read it and surface the full contents, formatted clearly.
   - **Does not exist** → Tell the user: "No context file found for branch `<branch>`. Use `/project-context:update` to create one."
3. After surfacing contents, briefly note what's missing (empty sections) so the user knows what to fill in.

---

## /project-context:update

1. Detect the branch and resolve the context file path.
2. If the file **exists**, read it first — preserve all existing content and merge new info in.
3. If the file **does not exist**, create it fresh with the full template.
4. Parse the user's `<info>` argument and slot the content into the appropriate section(s).
   - If the argument is ambiguous about which section it belongs to, use judgment based on section names.
   - If the argument covers multiple sections, update each one.
5. Write the updated file.
6. Confirm: "Updated context for `<branch>` → `memory/branches/<filename>`"

### Context file template

```markdown
# Branch: <branch-name>

## Ticket
- **ENG**: https://eightfoldai.atlassian.net/browse/ENG-XXXXX
- **IMPL**: https://eightfoldai.atlassian.net/browse/IMPL-XXXXXX  ← remove if not applicable
- **Summary**: <one-line summary of what the ticket is about>

## Relevant Files / Components
<!-- Key files to read/modify for this branch. file:line format where known. -->

## Key Findings
<!-- What you've discovered about how the code works — root causes, patterns, constraints -->

## Decisions
<!-- Approach decisions made, and why -->

## Test Environment
<!-- Sandbox URL, login credentials, navigation steps to reproduce/verify -->

## Open Questions / Notes
<!-- Unresolved questions, deferred items, gotchas to remember -->
```

Omit sections with no content — don't leave empty section headers.

---

## Notes

- This skill only reads/writes the local `memory/branches/` file. It does not call Jira, GitHub, or any external system.
- When invoked at the start of a session, `/project-context:read` gives instant context without re-fetching tickets or searching the codebase.
- When invoked after discovering something new, `/project-context:update` persists the finding so it's available next session.
