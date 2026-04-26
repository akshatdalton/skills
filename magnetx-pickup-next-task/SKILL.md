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

## Step 0: Read HQ Context (Notion)

Fetch Notion HQ Context page for current phase + decisions:
- **Page ID:** `34eecb1d-39d0-814e-b03e-c39f13d1c254`
- `mcp__claude_ai_Notion__notion-fetch` with page ID

Source of truth for active phase, settled decisions, completed log.

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

1. Notion task → Status = "Done" (background)
2. HQ Context page → append to "Recently Completed Tasks Log":
   - Date, task name, one-line note (background)
3. HQ Context → update "Last Activity Per Phase" row (background)
4. Auto-run next task pickup (back to Step 1)

---

## Rules

- Never mark task Done without user saying so
- Priority: High > Medium > Low
- Same priority: oldest first
- No To Do tasks → report back, suggest `/magnetx-hq`

## Git Identity

GitHub: **akshatdalton** (personal). Eightfold → `gh auth switch` first.
