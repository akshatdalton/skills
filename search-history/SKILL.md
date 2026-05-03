---
name: search-history
description: >
  Search past Claude Code conversation sessions using vague hints. Greps
  ~/.claude/history.jsonl, extracts the matching thread, and summarizes it.
  Trigger when user says "find that chat where...", "search my history for...",
  "remember when we did X", or asks to locate a past session.
---

# Search Chat History

Find past sessions or summarize recent activity.

---

## Default Mode — Activity Summary

For "what have I worked on?", "what did I do this week?", date ranges without keywords.

### 1 — Date range
Parse: "this week" → Mon 00:00 to now, "past 3 days" → 3d ago, "last week" → prev Mon-Sun. Convert relative → absolute timestamps.

### 2 — Extract sessions
```bash
python3 -c "
import json
from datetime import datetime
cutoff = datetime(YYYY, MM, DD).timestamp() * 1000
for line in open('$HOME/.claude/history.jsonl'):
    try: obj = json.loads(line)
    except: continue
    if obj.get('timestamp', 0) >= cutoff:
        print(line.strip())
" > /tmp/filtered_history.jsonl
```

### 3 — Aggregate by topic
Group by: ticket IDs (ENG-*, IMPL-*), PRs, skills invoked, repos. Earlier messages = context, later = resolution.

### 4 — Present
```
## Activity: [date range]
### By Ticket
- ENG-XXXXX: [what done] (dates)
### PRs
- repo#123: [status] (date)
### Key Decisions
- [notable decisions/learnings]
```

### 5 — Offer git log cross-reference
After summary: *"Check `git log --author=Akshat --since=DATE` for commits not in chat?"*
Run automatically if user asked in prompt.

---

## Keyword Mode — Find specific session

For "find that chat where...", "remember when we...".

### 1 — Extract keywords
2-4 concrete: function names, emails, errors, filenames, endpoints.

### 2 — Grep
```bash
grep -n "keyword1\|keyword2" ~/.claude/history.jsonl -i | head -50
```
Too many → narrow. Zero → synonyms or shorter substrings.

### 3 — Get sessionId
Most relevant line → extract `sessionId`.

### 4 — Extract thread
```bash
grep "SESSION_ID" ~/.claude/history.jsonl
```
Parse `display` field in timestamp order.

### 5 — Present
- **Session ID** + **date** (timestamp ms → human)
- **Summary**: what was debugged/built/discussed
- **Messages** in order: user asked, action taken
- Note hashed `pastedContents` (unrecoverable) vs readable

### 6 — Deduplicate
Multiple matches → group by topic (same ticket/PR). One entry per topic with all session dates.

---

## `current-id` Mode — Get the Current Session ID

For `/search-history current-id`.

The current session is the one whose most recent entry in `~/.claude/history.jsonl` matches the current project directory AND has the latest timestamp.

### Steps

1. Run:
```bash
python3 -c "
import json, os
project = os.getcwd()
latest = None
with open(os.path.expanduser('~/.claude/history.jsonl')) as f:
    for line in f:
        try: obj = json.loads(line)
        except: continue
        if obj.get('project') == project:
            if latest is None or obj['timestamp'] > latest['timestamp']:
                latest = obj
if latest:
    print(latest['sessionId'])
"
```

2. Print the session ID and confirm the project path it matched against.

3. Also show the last user message from that session so the user can verify it's the right one.

No further steps needed — output and stop.

---

## Limitations

- Chat titles not stored — only in Claude UI sidebar
- Hashed pasted content (`contentHash`) unrecoverable
- Multiple matches → group by topic, let user pick

---

## Workflow ending

After presenting results, offer: *"Load findings into current branch context via work_hq append-context?"*
