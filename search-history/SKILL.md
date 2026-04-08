---
name: search-history
description: >
  Search past Claude Code conversation sessions using vague hints. Greps
  ~/.claude/history.jsonl, extracts the matching thread, and summarizes it.
  Trigger when user says "find that chat where...", "search my history for...",
  "remember when we did X", or asks to locate a past session.
---

# Search Chat History

Find a past Claude Code session from vague hints.

---

## Step 1 — Extract keywords from the hint

From what the user remembers, pull out 2–4 concrete keywords: function names,
email addresses, error messages, file names, API endpoints, or any specific term
they mention.

---

## Step 2 — Grep history.jsonl

```bash
grep -n "keyword1\|keyword2" ~/.claude/history.jsonl -i | head -50
```

If too many results, narrow with more keywords. If zero results, try synonyms or
shorter substrings.

---

## Step 3 — Identify the sessionId

From the results, find the most relevant line. Extract its `sessionId`.

---

## Step 4 — Extract the full thread

```bash
grep "SESSION_ID" ~/.claude/history.jsonl
```

Parse each message's `display` field in timestamp order to reconstruct the conversation.

---

## Step 5 — Present the thread

Show:
- **Session ID** and approximate **date** (convert timestamp ms → human date)
- **Thread summary**: what was being debugged/built/discussed
- **Each message** in order: what the user asked, what action was taken
- Note which `pastedContents` are hashed (content not recoverable) vs readable

---

## Limitations

- **Chat titles not stored** — only visible in the Claude UI sidebar
- **Hashed pasted content** (`contentHash` field) means the actual pasted text is unrecoverable — only the surrounding message is readable
- **Multiple matches**: if several sessions match, list them all with their dates and a one-line summary, let the user pick
