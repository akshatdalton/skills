# /today source cursors

Per-source operational state for the ★ BRIEFING block. Each file tracks "since last run" so the second `/today` of the day only surfaces deltas.

## File shape

Every `<source>.json` carries the same minimum:

```json
{
  "last_run_ts": "2026-05-31T22:51:00Z",
  "cursor": "<source-specific marker>",
  "fetched_count": 12
}
```

Individual source agents may add fields they need (e.g. `slack.json` adds `engaged_channels` cache, `jira-new.json` adds `known_ticket_keys` and `account_id`). The base three are always present.

## When cursors advance

Only after the BRIEFING render completes successfully. If /today crashes mid-render, the cursor is NOT advanced — the next run re-shows the items.

## Resetting a single source

```bash
echo '{"last_run_ts": null, "cursor": null, "fetched_count": 0}' > ~/.claude/skills/today/state/sources/slack.json
```

Next /today refetches Slack from scratch (last 24h) without touching the other sources.

## Files

- `gcal.json` — Google Calendar
- `meetily.json` — Meetily transcripts
- `gmail.json` — Gmail
- `slack.json` — Slack engaged channels
- `github-review.json` — GitHub PRs assigned for review
- `jira-new.json` — Jira newly-assigned tickets
