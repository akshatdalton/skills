---
name: local-schedule
description: >
  Schedule autonomous local Claude agents using OS crontab + claude -p. Runs completely
  independent of Claude Code session — no window needs to be open. Full tool access, push
  notifications via ntfy.sh on completion or failure. Unlike /schedule (cloud, 1hr min),
  /loop, or CronCreate (all session-dependent). Use for time-of-day scheduling, recurring
  agents, one-shot tasks, or any autonomous work that must run even when Claude Code is
  closed. Trigger when user says "schedule locally", "local cron", "run at [time]",
  "remind me", "set up recurring agent", "list my cron jobs", "cancel scheduled job",
  or invokes /local-schedule. Also trigger when user wants reliable scheduling that
  doesn't depend on keeping Claude Code open.
---

# local-schedule

OS crontab + `claude -p`. Runs **independent of Claude Code session** — no window needed.
Scripts in `~/.claude/scheduled/`. ntfy.sh push on ✓ done or ✗ fail.
For quick in-session reminders while actively working → use `/loop` instead.

## Actions

| Intent | Action |
|--------|--------|
| Schedule new agent | [CREATE](#create) |
| See scheduled jobs | [LIST](#list) |
| Cancel a job | [DELETE](#delete) |
| Run immediately | [RUN-NOW](#run-now) |

---

## CREATE

1. **Understand** — what to run, how often, which directory (default: current `pwd`)
2. **Draft prompt** — self-contained; `claude -p` starts fresh each run with no prior context:
   - Include file paths explicitly
   - State success criteria
   - State what to do with results (commit? write to file? just log?)
3. **Generate job slug** — short kebab-case (e.g., `pr-check`, `daily-standup`)
4. **Set cron** — local time; confirm with user; prefer off :00/:30 marks
5. **Capture env** — crontab runs with stripped HOME/PATH; must set explicitly:
   - `which claude` → full path (likely `/opt/homebrew/bin/claude`)
   - `which node` → full path (likely under `~/.nvm/versions/...`)
6. **Write script** to `~/.claude/scheduled/<slug>.sh`:

```bash
#!/bin/bash
export HOME=/Users/akshat.v
export PATH=/opt/homebrew/bin:/opt/homebrew/sbin:$(dirname $(which node)):/usr/local/bin:/usr/bin:/bin

cd /WORKING/DIR
if /opt/homebrew/bin/claude -p "PROMPT_HERE"; then
  curl -s \
    -H "Title: ✓ Claude: JOB_SLUG" \
    -H "Priority: default" \
    -H "Tags: white_check_mark" \
    -d "Done | Dir: /WORKING/DIR" \
    ntfy.sh/claude-code-reminders
else
  curl -s \
    -H "Title: ✗ Claude: JOB_SLUG" \
    -H "Priority: urgent" \
    -H "Tags: x" \
    -d "FAILED | Dir: /WORKING/DIR" \
    ntfy.sh/claude-code-reminders
fi
```

7. `chmod +x ~/.claude/scheduled/<slug>.sh`
8. **Add to crontab**:
```bash
(crontab -l 2>/dev/null; echo "CRON_EXPR $HOME/.claude/scheduled/<slug>.sh >> $HOME/.claude/scheduled/logs/<slug>.log 2>&1") | crontab -
```
9. Confirm: human-readable schedule + script path

### Cron cheatsheet (local time)

| Expression | Meaning |
|------------|---------|
| `*/5 * * * *` | every 5 min |
| `57 8 * * 1-5` | weekdays ~9am |
| `0 14 * * *` | daily 2pm |
| `30 9 * * 1` | Mondays 9:30am |
| `0 */2 * * *` | every 2 hours |
| `0 9 1 * *` | 1st of month 9am |

---

## LIST

```bash
crontab -l 2>/dev/null | grep "\.claude/scheduled"
```

Display each job: cron expression (human-readable) + slug + script path.

---

## DELETE

1. List: `crontab -l | grep "\.claude/scheduled"`
2. User picks slug
3. Remove from crontab:
```bash
crontab -l | grep -v "<slug>.sh" | crontab -
```
4. Ask: delete script + log too? If yes:
```bash
rm -f ~/.claude/scheduled/<slug>.sh ~/.claude/scheduled/logs/<slug>.log
```

---

## RUN-NOW

```bash
bash ~/.claude/scheduled/<slug>.sh
```

No script yet (new one-off)? Write script first → run → ask if they want it kept on a schedule.

---

## Constraints

- `claude -p` starts a **fresh session** each run — no memory of prior runs
- Working dir must be set explicitly via `cd` in script
- crontab PATH is minimal — always use `/opt/homebrew/bin/claude` not just `claude`
- Logs at `~/.claude/scheduled/logs/<slug>.log` — tail them to debug failures
- ntfy.sh topic: `claude-code-reminders`
