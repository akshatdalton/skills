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

For "what have I worked on?", "what did I do this week?", or date range without specific keywords.

### Step 1 — Determine date range
Parse: "this week" → Monday 00:00 to now, "past 3 days" → 3 days ago, "last week" → prev Mon-Sun, "past month" → 30 days ago. Convert relative to absolute timestamps.

### Step 2 — Extract sessions in range
```bash
python3 -c "
import json
from datetime import datetime
cutoff = datetime(YYYY, MM, DD).timestamp() * 1000
for line in open('$HOME/.claude/history.jsonl'):
    try:
        obj = json.loads(line)
    except: continue
    if obj.get('timestamp', 0) >= cutoff:
        print(line.strip())
" > /tmp/filtered_history.jsonl
```

### Step 3 — Aggregate by topic
Group by: ticket IDs (ENG-*, IMPL-*), PRs created/updated, skills invoked, repos worked in. Use timestamps to understand flow — earlier messages = context, later = resolution.

### Step 4 — Present summary
```
## Activity: [date range]

### By Ticket
- ENG-XXXXX: [what was done] (dates)
- ENG-YYYYY: [what was done] (dates)

### PRs
- repo#123: [status — created/merged/reviewing] (date)

### Key Decisions
- [notable decisions or learnings]
```

### Step 5 — Offer git log cross-reference
After summary, offer: *"Want me to also check `git log --author=Akshat --since=DATE` for commits not discussed in chat?"*
Run automatically if user asked in prompt.

---

## Keyword Mode — Find specific session

For "find that chat where...", "remember when we...".

### Step 1 — Extract keywords
Pull 2-4 concrete keywords from user's hint: function names, emails, error messages, file names, API endpoints.

### Step 2 — Grep history
```bash
grep -n "keyword1\|keyword2" ~/.claude/history.jsonl -i | head -50
```
Too many results → narrow with more keywords. Zero → try synonyms or shorter substrings.

### Step 3 — Identify sessionId
Find most relevant line, extract `sessionId`.

### Step 4 — Extract full thread
```bash
grep "SESSION_ID" ~/.claude/history.jsonl
```
Parse each message's `display` field in timestamp order.

### Step 5 — Present thread
- **Session ID** and **date** (convert timestamp ms → human)
- **Thread summary**: what was debugged/built/discussed
- **Each message** in order: what user asked, what action taken
- Note which `pastedContents` are hashed (unrecoverable) vs readable

### Step 6 — Deduplicate
Multiple matches → group by topic (same ticket, same PR) instead of listing separately. One entry per topic with all session dates.

---

## Limitations

- Chat titles not stored — only visible in Claude UI sidebar
- Hashed pasted content (`contentHash`) means actual text unrecoverable — only surrounding message readable
- Multiple matches: group by topic, let user pick
