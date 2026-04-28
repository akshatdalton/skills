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

## CI watch cron (offer whenever CI is triggered)

After any step that starts CI — `needs_ci` posted in `/get-pr-ready-to-merge`, or PR created in `/submit-pr`/`/work-on-jira-task` — always ask:

> "Want me to set up a cron to watch CI? When it completes I'll auto-prompt a fresh `/get-pr-ready-to-merge` run."

If yes → use `/local-schedule` to create a hourly cron (`0 * * * *`) that:
1. Runs `gh api repos/ORG/REPO/commits/{sha}/check-runs` — GitHub Actions jobs
2. Runs `gh api repos/ORG/REPO/commits/{sha}/status` — external CI suite (Eightfold: Prerequisites, ESLint, Pytest, etc.)
3. If any still pending/in_progress → exit silently (runs again next hour)
4. If all complete → remove itself from crontab + send ntfy.sh push notification (pass or fail) with message: "Run: /get-pr-ready-to-merge <PR URL>"
