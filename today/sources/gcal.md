# gcal source-agent spec

## Purpose
Fetch upcoming Google Calendar events from the user's primary calendar and subscribed calendars for the next 24 hours, filter out declined/long-block events, and return a compact JSON list of meetings the user should attend, with a suggested action per event. Used by /today Step 9 to populate the BRIEFING block.

## Inputs
- `last_run_ts` — ISO8601 timestamp from cursor file (`~/.claude/skills/today/state/sources/gcal.json`). On first run, null → fetch from `now` through `now + 24h`.
- `now` — current timestamp (passed by parent)

## Tools required (load via ToolSearch first)
- `mcp__claude_ai_Google_Calendar__list_calendars`
- `mcp__claude_ai_Google_Calendar__list_events`

## Behavior
1. Load both MCP tools via ToolSearch using `select:mcp__claude_ai_Google_Calendar__list_calendars,mcp__claude_ai_Google_Calendar__list_events`.
2. Call `list_calendars` once to enumerate the user's primary + subscribed calendars.
3. Compute window: `start = max(last_run_ts, now)`, `end = now + 24h`.
4. For each calendar (in parallel where possible, cap at 5 concurrent), call `list_events` with `timeMin=start`, `timeMax=end`, `singleEvents=true`, `orderBy=startTime`.
5. Merge all events, dedupe by event id.
6. Filter OUT:
   - Events where user's `responseStatus` is `declined`
   - All-day events whose duration spans more than 1 day (vacation/OOO blocks)
   - Events with no attendees AND no conference link (likely personal blocks unless title looks meeting-y — keep when in doubt)
7. Keep events where user response is `accepted` or `needsAction`.
8. For each kept event, build the output item:
   - `ts` = event start time (for all-day single-day events, `<date>T00:00:00`)
   - `title` = event summary
   - `action` derivation:
     - If event has a Google Meet or Zoom link → `"join at HH:MM (meetily armed)"`
     - Else if event has an attached doc (agenda, attachments[]) → `"skim agenda, attend at HH:MM"`
     - Else → `"attend at HH:MM"`
   - `urgency`:
     - `"now"` if start within 15 minutes of `now`
     - `"today"` if start within 24h
     - `"fyi"` otherwise (rare given window)
   - `project_hint`: `null` (GCal events don't reliably map to projects)
9. Sort items by `ts` ascending.
10. Return the JSON contract below. Set `cursor_advance = now` only if no errors occurred.

## Output JSON contract
EXACTLY this shape (parent expects it):
```json
{
  "source": "gcal",
  "fetched_at": "<ISO8601>",
  "cursor_advance": "<ISO8601>",
  "items": [
    {
      "source_id": "<event_id>",
      "ts": "<start_time>",
      "title": "<event title>",
      "action": "<e.g. 'join at 09:30 (meetily armed)' or 'skim agenda, attend at 14:00'>",
      "project_hint": null,
      "urgency": "now | today | fyi"
    }
  ],
  "fyi_count": <number of items with urgency == "fyi">,
  "errors": []
}
```

## Latency budget
Target: under 5 seconds total. Cap parallel `list_events` calls at 5 concurrent. If a calendar call takes >3s, abandon it and record the calendar id in `errors[]` rather than blocking the whole agent.

## Edge cases
- Empty calendars or no events in window: return `items: []` with `fetched_at` and `cursor_advance` set.
- API errors on individual calendars: append `{"calendar": "<id>", "error": "<msg>"}` to `errors[]`, continue with other calendars.
- Total auth/list_calendars failure: return `items: []`, `errors: [{"fatal": "<msg>"}]`, DO NOT advance cursor.
- All-day single-day events (e.g. "Focus block"): include as `ts: <date>T00:00:00`, urgency `today`.
- Multi-day all-day events (vacation, OOO): exclude entirely.
- Recurring events: rely on `singleEvents=true` to expand instances; treat each as independent.
- Conference link detection: check `conferenceData.entryPoints[].uri`, `hangoutLink`, and scan `description` for `zoom.us` / `meet.google.com`.

## Cursor advance rule
Set `cursor_advance` to `now` only on success (no fatal error). Parent persists to `~/.claude/skills/today/state/sources/gcal.json`. On fatal error, leave `cursor_advance` as the input `last_run_ts` so the next run retries the same window.
