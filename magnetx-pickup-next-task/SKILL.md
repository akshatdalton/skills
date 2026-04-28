---
name: magnetx-pickup-next-task
description: >
  Pick next "To Do" task from MagnetX Task Board, fetch context, set "In Progress".
  Usage: /magnetx-pickup-next-task or /magnetx-pickup-next-task [phase].
  If user seems lost or no active task, suggest /magnetx-hq first for phase overview.
---

# /magnetx-pickup-next-task — Task Picker

Pick next task from Notion board. Set In Progress. Show context.

**No active task + no args?** Suggest `/magnetx-hq` for phase overview first.

---

## Step 0: Read Context (Cache-First)

**Cache file:** `~/.claude/skills/magnetx-hq/cache.json`

1. Read `cache.json` with the Read tool
2. If file exists and valid JSON → use cached data (active phase, tasks, decisions)
3. If file missing or malformed → fall back to Notion fetch:
   - **Page ID:** `34eecb1d-39d0-814e-b03e-c39f13d1c254`
   - `mcp__claude_ai_Notion__notion-fetch` with page ID

Cache contains: active phase, task list with statuses, settled decisions, completed log.

---

## Step 1: Parse Input

- No arg → phase = active phase from HQ Context (currently: "Build MVP")
- Arg provided → phase = argument (e.g., "Validate", "Personal X Growth")

## Step 2: Query Task Board

Data Source ID: `a119bf6a-603e-4f51-b602-fc7ffb4e445e`
- Filter: Status = "To Do" AND Phase = [parsed phase]
- Sort: Priority DESC (High first), created ASC (oldest first)
- Return first result

Also check: any "In Progress" task in phase → recommend resume instead.

## Step 3: Fetch Task Details

`mcp__claude_ai_Notion__notion-fetch` with task ID:
- Get: Task, Phase, Type, Priority, Status, Notes, URL
- Read Notes completely (contains context + rationale)

## Step 4: Set In Progress

`mcp__claude_ai_Notion__notion-update-page`:
- Status → "In Progress"
- Keep other properties

## Step 5: Enrich

- Type = "Skill" → check `~/.claude/skills/[name]/SKILL.md` exists
- List file paths or URLs from Notes

## Step 6: Output

```
NEXT TASK: [title]

  Phase:    [phase]
  Type:     [type]
  Priority: [priority]
  Status:   In Progress

CONTEXT:
  [notes text]

FILES:
  [paths/URLs]

PREP:
  1. [first step]
  2. [second step]

NOTION: [task URL]
```

## Step 7: Offer

```
Ready to work? Say "done" when finished.
```

---

## On "Done" / "Finished" / "Complete"

1. **Immediately** show next task from conversation context (no Notion call)
2. **Background agent** (single agent, all writes batched):
   - Notion task → Status = "Done"
   - HQ Context page → append to "Recently Completed Tasks Log": date, task name, one-line note
   - HQ Context → update "Last Activity Per Phase" row
   - After all Notion writes → refresh `~/.claude/skills/magnetx-hq/cache.json` (fetch all 3 sources, rewrite cache)
3. Auto-run next task pickup (back to Step 1, reads from cache or conversation context)

---

## Rules

- Never mark task Done without user saying so
- Priority: High > Medium > Low
- Same priority: oldest first
- No To Do tasks → report back, suggest `/magnetx-hq`

## Git Identity

GitHub: **akshatdalton** (personal). Eightfold → `gh auth switch` first.
