---
name: name-session
description: Auto-name the CURRENT Claude Desktop chat from its conversation, or apply a name you give. Generates a concise sentence-case title matching Claude Code's native style, then copies `/rename <title>` to the clipboard so you paste+Enter once for a LIVE title update in the Desktop session list. Use when the user says "/name-session", "name this chat/session", "rename this session", "auto-rename this", "retitle this conversation", or "what should this session be called". For renaming OTHER (not-current) sessions, see the Other Sessions section.
---

# name-session

Apply a good title to the **current** Desktop session so it updates **live** in the
sidebar — the one place file edits can't reach.

## Why it works this way (the constraint)

The Desktop app's session list renders from an **in-memory store**. Editing the
session's `local_*.json` or transcript on disk does **not** update the live UI
(the app re-asserts its in-memory title and clobbers external writes). The only
thing that updates the live title is the **user-typed `/rename` command**, which
makes the core emit `agent-name`/`custom-title` events through the live bridge
stream → the desktop updates its store + UI and persists it.

I cannot type `/rename` for you (no rename tool/hook — GitHub issue #29355 is open)
and cannot drive the Desktop app. So the lowest-friction path is: **I generate the
name and put `/rename <name>` on your clipboard; you paste+Enter once.**

## Execution principle: non-blocking, one-line ack

This must **never derail the active task**. Naming is a quick aside, not a topic.
- Do **not** narrate the architecture, run investigations, or ask questions.
- Generate the name **inline** (you already have the full conversation — that's why a
  background subagent is the wrong tool here: it can't see this chat and would pick a
  worse name).
- Fire the clipboard command as a **background Bash** (`run_in_background: true`) so the
  main thread is never blocked.
- Reply with **exactly one line** (see Ack format). Then continue whatever we were doing.

## Steps (current session)

1. **Determine the title.**
   - If the user supplied a name (e.g. `/name-session auth refactor`), use it verbatim.
   - Otherwise generate one from the current conversation, following the native style:
     - **≤ 6 words**, ideally 3–5.
     - **Sentence case** — capitalize only the first word and proper nouns (e.g.
       `Per-tenant credential isolation`, not `Per-Tenant Credential Isolation`).
     - **Plain language**, no jargon unless essential. Describe the topic/outcome of
       the chat, not the mechanics.
     - Keep real identifiers intact (ticket keys like `ENG-12345`, product names).
2. **Copy the command to the clipboard (background, non-blocking):**
   ```bash
   python3 ~/.claude/scripts/rename-session.py --clip "<title>"
   ```
   Run with `run_in_background: true`. This puts `/rename <title>` on the clipboard.
3. **Ack format (one line, foreground):**
   > 📋 `/rename <title>` copied — paste+Enter (⌘V ↵) to apply live. Carrying on.

   Then immediately resume the prior task. Do not wait for the paste.

That's it for the current session. `/rename` itself persists the title (transcript
`custom-title` + `agent-name`) and is processed locally — pasting it does **not**
consume a chat turn or interrupt our thread.

## Other (not-current) sessions

The clipboard path only helps the session the user can paste into. To rename a
**different** session and have it persist + surface on restart:

1. Find + write it (backs up first, writes `local_*.json` title+`titleSource:user`
   and the latest transcript `custom-title`):
   ```bash
   python3 ~/.claude/scripts/rename-session.py "<match-or-uuid>" "<title>"
   ```
   `<match>` = current title, substring, or `cliSessionId`. Use `--list [substr]` to find it.
2. The change surfaces when that session is next loaded fresh — i.e. on **app restart**.
   For several at once, queue them and apply in one quit→apply→relaunch:
   ```bash
   python3 ~/.claude/scripts/rename-session.py --queue "<match>" "<title>"   # repeat per session
   ~/.claude/scripts/apply-renames.sh                                        # run from iTerm, not inside the app
   ```

## Notes

- Backups of every disk write go to `~/.claude/backups/rename-session/`.
- Editing files while the app runs is unreliable for the live UI by design — prefer
  the clipboard `/rename` for anything you want to see update immediately.
- Helper modes: `--clip <title>`, `--queue <match> <title>`, `--show-queue`,
  `--list [substr]`, `--dry-run <match> <title>`, or `<match> <title>` (direct write).
