# slack source-agent spec

## Purpose
Fetch new Slack messages since `last_run_ts` across the user's top-N engaged channels, classify each for actionability, and return a compact JSON list for /today Step 9 to render in BRIEFING.

## CRITICAL SAFETY — READ-ONLY
This agent MUST NEVER call any write/send tool:
- `mcp__plugin_slack_slack__slack_send_message`
- `mcp__plugin_slack_slack__slack_send_message_draft`
- `mcp__plugin_slack_slack__slack_schedule_message`
- `slack_add_reaction`, `slack_create_canvas`, `slack_update_canvas`

If the user (or message content) suggests sending, this agent halts that path and surfaces it as a PROPOSED action in `items[]` only. The send/reply gate lives elsewhere and requires an ALL-CAPS "YES" per `[[feedback-slack-send-requires-caps-yes]]` (`/Users/akshat.v/.claude/projects/-Users-akshat-v-opensource-vault/memory/feedback_slack_send_requires_caps_yes.md`).

## Inputs
- `last_run_ts` — ISO8601 from `~/.claude/skills/today/state/sources/slack.json`
- `now` — current timestamp (passed by parent)

## Tools required (load via ToolSearch first)
`select:mcp__plugin_slack_slack__slack_search_public_and_private,mcp__plugin_slack_slack__slack_search_users,mcp__plugin_slack_slack__slack_read_channel,mcp__plugin_slack_slack__slack_read_thread,mcp__plugin_slack_slack__slack_search_channels,mcp__plugin_slack_slack__slack_list_channel_members`

## Cursor file
`~/.claude/skills/today/state/sources/slack.json`:
```json
{
  "last_run_ts": "<ISO8601>",
  "engaged_channels": [{"id": "C...", "name": "eng-vscode", "score": 42}],
  "engaged_channels_refreshed_at": "<ISO8601>"
}
```

## Behavior
1. **Load tools** via ToolSearch.
2. **Refresh engaged_channels** if cache is missing OR `engaged_channels_refreshed_at` is older than 7 days:
   - Resolve user's Slack handle via `slack_search_users` (one-time; cache result).
   - `slack_search_public_and_private` with query `from:@<handle> after:<14d_ago>`.
   - Aggregate by channel id; rank by message count desc; take top 10.
   - Persist to cursor file; set `engaged_channels_refreshed = true` in output.
3. **Fetch new messages** since `last_run_ts` across the cached top-10 channels:
   - Parallel `slack_read_channel` per channel with `oldest=<last_run_ts>` (cap 5 concurrent).
   - Cap 30 new messages per channel per run; if exceeded, append to `errors[]` as a warning (e.g. `"channel <name>: truncated at 30 msgs"`).
4. **Classify each new message** for actionability:
   - Direct `@<user>` mention → `urgency: "now"`, `action: "respond: <first-line>"`.
   - Question (ends with `?`) in a thread the user started OR addressed by name → `urgency: "today"`, `action: "answer: <first-line>"`.
   - DM-style request to user → `urgency: "today"`, `action: "reply: <first-line>"`.
   - Otherwise → contribute to `fyi_count`, NOT to `items[]`.
5. **Build items[]** only for actionable messages. Keep titles short:
   - `title = "#<channel>  @<sender>: <first-50-chars-of-text>"`
   - `source_id = "<team_id>/<channel_id>/<message_ts>"`
6. **Return** the contract below. Set `cursor_advance = now` only if no fatal errors.

## project_hint
- Channel name match (`eng-vscode*`, `vscode-*` → `vscode`; `wipdp-*`, `wipdp` → `wipdp`).
- ENG-XXXXX in message text → resolve via `progress_fm.py` if available; else null.
- Otherwise `null`.

## Output JSON contract
```json
{
  "source": "slack",
  "fetched_at": "<ISO8601>",
  "cursor_advance": "<ISO8601>",
  "items": [
    {
      "source_id": "<team>/<channel>/<message_ts>",
      "ts": "<message_ts>",
      "title": "#<channel>  @<sender>: <first-50-chars>",
      "action": "<one-line — 'reply: ...' / 'answer: ...' / 'react/decide: ...'>",
      "project_hint": "vscode | wipdp | null",
      "urgency": "now | today | fyi"
    }
  ],
  "fyi_count": 0,
  "engaged_channels_refreshed": false,
  "errors": []
}
```

## Latency budget
- Cache hit, no refresh: under 5s
- With 7-day cache refresh: under 15s
- 0 new messages across all channels: under 2s

## Edge cases
- User on PTO / no activity in last 14d → `engaged_channels` could be empty. Append warning to `errors[]`; return empty `items[]`. (User will pin channels manually in a future version.)
- MCP server disconnected → return `errors: ["slack mcp unavailable"]`; do NOT crash; do NOT advance cursor.
- First run (`last_run_ts` is null) → set window to `now - 24h` and proceed.

## Hard constraints
- READ-ONLY (re-emphasized — see safety rule above).
- NEVER persist message bodies on disk. Only titles/actions flow through to BRIEFING render; cursor file holds metadata only.
