---
name: magnetx-hq
description: >
  MagnetX command center — session start dashboard showing all phases with progress,
  recommended next action, open decisions, and X growth streak. Use this skill whenever
  the user starts a session in the magnetx directory, says "what should I work on",
  "where did I leave off", "show me status", "magnetx status", or invokes /magnetx-hq.
  Also trigger when user seems unsure what to do next in MagnetX context.
---

# /magnetx-hq — Command Center

Session entry point. Show status, recommend action, route to work.

---

## Step 0: Load Context

Fetch two Notion sources (parallel):

1. **HQ Context page** — phase status, decisions, completed log
   - Page ID: `34eecb1d-39d0-814e-b03e-c39f13d1c254`
   - `mcp__claude_ai_Notion__notion-fetch` with page ID

2. **Task Board** — live task counts grouped by Phase
   - Data Source ID: `a119bf6a-603e-4f51-b602-fc7ffb4e445e`
   - Count Done vs Total per phase

Notion = source of truth. Skip local memory files for status.

---

## Step 1: Dashboard

Clean, scannable. Generous spacing for iTerm2. No dense tables.

```
MAGNETX HQ — [date]

PHASES
──────

  ★ [recommended phase]          [done/total]    Last: [date]
    → Next: [task name]
    Why now: [one-line reasoning]

    [phase]                       [done/total]    Last: [date]
    → Next: [task name]

    [skipped phase]               SKIPPED
    → [reason]

    [blocked phase]               [done/total]    Blocked on [X]


X GROWTH
────────
    Streak: [N] days (last: [date])
    [nudge if >7d cold]


OPEN DECISIONS: [N]
───────────────
    [1-liners]


PICK
────
    [1-5] Phase    [d] Daily X engagement    [q] Decisions
```

### ★ Recommendation Logic

Pick one phase with ★:
1. Active phase from HQ Context (default: Build MVP)
2. Blocked → recommend unblock action
3. X streak cold (>7d) → mention, don't override phase rec
4. Always explain "Why now" in one line

---

## Step 2: Route

**Phase picked** →
1. Query task board: phase + Status "To Do" / "In Progress"
2. Show tasks with recommendation + reasoning:
   - High > Medium > Low priority
   - Same priority → oldest first
   - "In Progress" exists → recommend resume
3. User picks → set "In Progress" in Notion → show context → start

**[d] X engagement** → run `/magnetx-engage`
- After: update streak in Daily Tracker (DS: `4b9b90de-9252-4da7-a76c-f40fa89c610f`)

**[q] Decisions** → show open decisions, brainstorm, resolve
- Resolution → update HQ Context (background)

---

## Step 3: Task Complete

User says "done" / "finished" / "complete":

1. Notion task → "Done" (background)
2. HQ Context → append completed log: date, task, note (background)
3. HQ Context → update "Last Activity" for phase (background)
4. Show dashboard again with fresh counts

All writes = background. Don't block flow.

---

## Step 4: Capture Decisions

Product decision made or new question mid-session:
- Settled → append "Key Strategic Decisions" in HQ Context (background)
- Open → append "Open Product Decisions" table (background)

---

## References

| What | ID |
|------|----|
| HQ Context | `34eecb1d-39d0-814e-b03e-c39f13d1c254` |
| Task Board | `a119bf6a-603e-4f51-b602-fc7ffb4e445e` |
| X Tracker | `4b9b90de-9252-4da7-a76c-f40fa89c610f` |
| Parent page | `304ecb1d-39d0-80f2-849b-c46d97e80672` |
| GitHub | akshatdalton/magnetx (monorepo, landing in landing/) |
| Vercel | magnetx.co |

## Git Identity

GitHub: **akshatdalton** (personal). Eightfold account → `gh auth switch` first. Never eightfold creds here.
