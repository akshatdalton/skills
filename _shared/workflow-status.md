# Workflow Status Block (shared)

Every skill in the dev chain should end with a status block + project-context update.

## Status block format

```
───── workflow ─────
✓ Ticket: ENG-XXXXX
✓ Branch: akshat/ENG-XXXXX-short-name
✓ [completed step]
→ Next: /[next-skill]
────────────────────
```

Only show steps relevant to current chain progress. Include ticket + branch always.

## Project-context persistence

Before presenting the status block, update project-context with what was accomplished:

```
/project-context:update [key finding or decision from this skill invocation]
```

This carries knowledge across sessions. Next skill invocation on same branch starts with `/project-context:read` for instant context.

## Chain order

```
/create-jira-ticket-with-reference
  → /work-on-jira-task
    → /submit-pr
      → /get-pr-ready-to-merge (if CI fails or comments pending)
```

Side entries:
- `/explain-anything` → any of the above
- `/debug-api` → `/create-jira-ticket-with-reference` or `/work-on-jira-task`
- `/create-tech-doc` → `/create-jira-ticket-with-reference` or `/work-on-jira-task`
- `/search-history` → `/project-context:update` (load findings)
