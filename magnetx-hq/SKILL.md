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

## Step 0: Load Context (Cache-First)

**Cache file:** `~/.claude/skills/magnetx-hq/cache.json`

### Read path (fast):
1. Read `cache.json` with the Read tool
2. If file exists and valid JSON → use cached data, skip Notion calls entirely
3. If file missing or malformed → fall back to Notion fetch (see below), then write cache

### Fallback (cold start only):
Fetch three Notion sources (parallel) — only when cache is missing:

1. **HQ Context page** — phase status, decisions, completed log
   - Page ID: `34eecb1d-39d0-814e-b03e-c39f13d1c254`
   - `mcp__claude_ai_Notion__notion-fetch` with page ID

2. **Task Board** — live task counts grouped by Phase
   - Data Source ID: `a119bf6a-603e-4f51-b602-fc7ffb4e445e`
   - Search all tasks, group by Phase + Status

3. **X Tracker** — streak data
   - Data Source ID: `4b9b90de-9252-4da7-a76c-f40fa89c610f`
   - Search recent entries for last session date + streak count

After fetching, write `cache.json` (see Cache Format below).

### Cache Format (`cache.json`):
```json
{
  "updated_at": "2026-04-27T12:00:00Z",
  "hq_context": {
    "active_phase": "Build MVP",
    "phases": [
      { "name": "Personal X Growth", "done": 7, "total": 8, "last_activity": "2026-04-12", "last_work": "..." },
      { "name": "Validate", "done": 2, "total": 3, "last_activity": "2026-04-18", "last_work": "..." },
      { "name": "Concierge", "status": "SKIPPED", "last_activity": "2026-04-17", "last_work": "..." },
      { "name": "Build MVP", "done": 0, "total": 7, "last_activity": "2026-04-19", "last_work": "..." },
      { "name": "Launch", "done": 0, "total": 5, "blocked_on": "MVP completion" }
    ],
    "open_decisions": [ { "num": 1, "question": "...", "context": "...", "options": "...", "status": "Open" } ],
    "settled_decisions": [ "..." ],
    "completed_log": [ { "date": "...", "task": "...", "note": "..." } ],
    "mvp_segments": [ "Skeleton", "Core loop", "Polish", "Production" ]
  },
  "x_tracker": {
    "streak": 1,
    "last_session_date": "2026-04-12"
  },
  "tasks": [
    { "id": "...", "title": "...", "phase": "...", "status": "...", "notes": "..." }
  ]
}
```

Notion remains source of truth. Cache = read-only snapshot for fast startup.

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


SOURCES
───────
    HQ Context: [notion link]
    Task Board: [notion link]
    X Tracker:  [notion link]


PICK
────
    [1-5] Phase    [d] Daily X engagement    [q] Decisions
```

### Notion Links

Always include a SOURCES section at the bottom of the dashboard with clickable Notion links.
Format: `https://www.notion.so/<page-or-db-id-without-dashes>`

| Source | Link |
|--------|------|
| HQ Context | `https://www.notion.so/34eecb1d39d0814eb03ec39f13d1c254` |
| Task Board | `https://www.notion.so/a119bf6a603e4f51b602fc7ffb4e445e` |
| X Tracker | `https://www.notion.so/4b9b90de92524da7a76cf40fa89c610f` |

When referencing specific data from Notion mid-conversation (e.g., a task, decision, or streak),
include the relevant Notion link inline so the user can cross-check the source.

### ★ Recommendation Logic

Pick one phase with ★:
1. Active phase from HQ Context (default: Build MVP)
2. Blocked → recommend unblock action
3. X streak cold (>7d) → mention, don't override phase rec
4. Always explain "Why now" in one line

### Recommendation Narrative

After the dashboard + PICK menu, **always** present a recommendation section with reasoning.
Format — conversational, not bullet soup:

```
MY RECOMMENDATION
─────────────────
**[Phase name]** is the move. Here's why:

1. [Strongest reason — what's the leverage?]
2. [Why other phases can wait or benefit from this going first]
3. [What becomes easier/better once this is done]

**First task: [task name].** [One line on why this task specifically.]

Want me to pick up that task? Or [alternative option]?
```

Rules:
- Lead with the phase, then justify (don't bury the recommendation)
- Connect phases to each other — show why ordering matters
- End with a clear call-to-action
- Keep it to 3-5 lines of reasoning, not a wall of text

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

1. **Immediately** update conversation context (you already know the task details)
2. **Show refreshed dashboard** using in-memory state (no Notion call, no cache read)
3. **Background agent** (single agent, all writes batched):
   - Notion task → "Done"
   - HQ Context → append completed log: date, task, note
   - HQ Context → update "Last Activity" for phase
   - After all Notion writes succeed → **refresh cache**: fetch all 3 Notion sources, write `cache.json`

All writes + cache refresh = one background agent. Never block the user.
The user continues working with conversation context. Next `/magnetx-hq` invocation reads fresh cache.

---

## Step 4: Capture Decisions

Product decision made or new question mid-session:
- Settled → append "Key Strategic Decisions" in HQ Context (background agent)
- Open → append "Open Product Decisions" table (background agent)
- After Notion write → refresh cache in same background agent

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
