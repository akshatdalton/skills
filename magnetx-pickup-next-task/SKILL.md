---
name: magnetx-pickup-next-task
description: >
  Pick the next "To Do" task from MagnetX Task Board, fetch context, set to "In Progress".
  Usage: /magnetx-pickup-next-task or /magnetx-pickup-next-task [phase]
---

# /magnetx-pickup-next-task Skill — EXECUTION STEPS

When user calls this skill, execute these steps:

## Step 1: Parse Input

- If no argument: phase = "Personal X Growth"
- If argument provided: phase = argument (e.g., "Validate", "Concierge", "Build MVP")

## Step 2: Query Notion Task Board

Use `mcp__claude_ai_Notion__notion-search` or direct data source query:
- Data Source ID: `a119bf6a-603e-4f51-b602-fc7ffb4e445e`
- Filter: Status = "To Do" AND Phase = [parsed phase from Step 1]
- Sort: Priority DESC (High first), then created time ASC (oldest first)
- Return: First result

## Step 3: Fetch Full Task Details

Use `mcp__claude_ai_Notion__notion-fetch` with task ID from Step 2:
- Get all properties: Task, Phase, Type, Priority, Status, Notes, URL
- Read the Notes field completely (contains context and decision rationale)

## Step 4: Update Status in Notion

Use `mcp__claude_ai_Notion__notion-update-page`:
- Set Status = "In Progress"
- Keep other properties unchanged

## Step 5: Enrich Output

Before displaying, check for related context:
- If Type = "Skill": check if `~/.claude/skills/[skill-name]/SKILL.md` exists
- Check `magnetx_build_system_completed_tasks.md` for related done tasks
- List any file paths or Notion URLs mentioned in Notes

## Step 6: Output Ready-to-Work Format

```
🎯 NEXT TASK: [Task Title]

📋 DETAILS:
  Phase: [Phase]
  Type: [Type]
  Priority: [Priority]
  Status: ✅ In Progress

📝 CONTEXT:
[Full Notes text]

📂 FILES/REFERENCES:
[List any files, URLs, or resources mentioned]

⚙️ PREP:
1. [First actionable step based on task type]
2. [Second step]
3. etc.

🔗 NOTION:
[Task URL from Notion]
```

## Step 7: Offer Next Steps

End with:
```
Ready to work? Let me know when you finish and I'll call /magnetx-pickup-next-task again.
```

---

## Notes

- **Do NOT mark task as Done** — only set to "In Progress"
- **If no To Do tasks found** → report back: "No To Do tasks in [phase]. What would you like to do?"
- **Priority order:** High → Medium → Low
- **Task queue order:** Within same priority, pick earliest created task (oldest first)
