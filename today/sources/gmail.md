# /today source agent — gmail

Fetch unread Gmail since last run, LLM-classify into action/fyi/noise, return action items only.

## Account
- akshat25iiit@gmail.com (personal Google)

## Cursor
- File: `~/.claude/skills/today/state/sources/gmail.json`
- Fields: `last_run_ts` (ISO8601), `last_thread_id` (str)
- First run (no cursor): window = last 24h
- Subsequent: window = since `last_run_ts`

## Tools (deferred — load via ToolSearch `select:<name>` before calling)
- `mcp__claude_ai_Gmail__search_threads` — list unread in window
- `mcp__claude_ai_Gmail__get_thread` — headers + first message snippet only
- `mcp__claude_ai_Gmail__list_labels` — optional, for context

## READ-ONLY hard constraint
MUST NOT call: `create_draft`, `label_thread`, `unlabel_thread`, `label_message`, `unlabel_message`, `create_label`, `delete_label`, `update_label`. Even if the broader request implies a mutation, this agent ignores it.

## Steps
1. Load cursor. Compute `after:<last_run_ts_epoch>` (or last 24h if first run).
2. `search_threads` with query `is:unread after:<epoch>`. Cap at 50 results.
3. If results > 50: take first 50, append `errors[]` note "truncated at 50".
4. For each thread: `get_thread` and pull sender, subject, first-message snippet. Avoid full-body fetch unless snippet ambiguous.
5. Classify each thread into action / fyi / noise (heuristics below).
6. Build `items[]` from action threads only. Tally `fyi_count`, `noise_count`.
7. Set `cursor_advance = now`. /today writes the cursor on success.

## Classification heuristics
- **action** — direct ask to you; signed PDF needed; response expected; renewal/deadline; calendar invite needing decision; $$ expiry; legal/compliance ask; manager/director sender; your name in body asking for input.
- **fyi** — company announcements; broadcast updates; "for your awareness"; standup digests; status reports; dashboards.
- **noise** — newsletters; marketing; GitHub notification digests (PRs/issues are covered by github-review agent); Calendly auto-emails; Substack; no-reply senders.

When ambiguous between action and fyi, prefer **fyi** (false-positive action items are noisier than missed FYIs).

## project_hint
- Sender domain `@eightfoldai.com` OR thread mentions `ENG-XXXXX` → resolve project (vscode | wipdp) via `progress_fm.py` ticket lookup
- Otherwise `null`

## Output JSON contract
```json
{
  "source": "gmail",
  "fetched_at": "<ISO8601>",
  "cursor_advance": "<ISO8601>",
  "items": [
    {
      "source_id": "<thread_id>",
      "ts": "<thread_last_msg_ts>",
      "title": "<sender>: <subject>",
      "action": "<one-line action verb, e.g. 'reply by EOD' or 'sign-off on legal v3'>",
      "project_hint": "vscode | wipdp | null",
      "urgency": "now | today | fyi"
    }
  ],
  "fyi_count": <int>,
  "noise_count": <int>,
  "errors": []
}
```

`noise_count` is gmail-specific (extension of base contract). /today renders it collapsed as `(N noise filtered)`.

## Latency budget
- 0 unread: < 1s
- 1–10 unread: < 5s
- 10–50 unread: < 30s
- > 50: warn, fetch first 50, append truncation note to `errors[]`

## Failure modes
- MCP auth error → return empty `items[]`, `errors: ["gmail auth failed: <msg>"]`, do NOT advance cursor.
- Tool timeout → return partial `items[]` from threads classified so far, `errors: ["partial: timeout after N threads"]`, do NOT advance cursor.
- Thread fetch fails for individual thread → skip it, append `errors[]` note with thread id, continue.
