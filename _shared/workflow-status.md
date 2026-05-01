# Workflow Status (slim — historical)

The CI-watch logic that used to live here has moved to the dedicated `/pr-watcher` skill (driven by `/loop`, not crontab). Each chained skill (`/submit-pr`, `/get-pr-ready-to-merge`, `/work-on-jira-task`) inlines its own status block + auto-add-to-watcher step now. There's nothing left to load lazily from this file.

If you're a future skill author looking for the chain order:

```
/create-jira-ticket-with-reference
  → /work-on-jira-task
    → /submit-pr  (auto-adds PR to /pr-watcher)
      → /get-pr-ready-to-merge  (auto-adds PR to /pr-watcher)
        → /pr-watcher  (loop-driven, posts shipit / merges / notifies)
```

Side entries: `/explain-anything`, `/debug-api`, `/run-on-ec2`, `/create-tech-doc`, `/search-history` can hook into any node above.
