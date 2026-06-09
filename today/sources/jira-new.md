# /today source agent — jira-new

Find newly-assigned Jira tickets + sprint/status changes for the user since last run. NOT every assigned ticket (those flow via existing progress.md frontmatter on the dashboard).

## Account
- `eightfoldai.atlassian.net` — user's Atlassian account

## Cursor
- File: `~/.claude/skills/today/state/sources/jira-new.json`
- Fields:
  - `last_run_ts` (ISO8601) — for "updated since" filter
  - `account_id` (str) — cached from `atlassianUserInfo`; refresh monthly
  - `known_ticket_keys` (list[str]) — tickets already surfaced in a prior BRIEFING
- First run (no cursor): window = last 24h; fetch `account_id`

## Tools (deferred — load via ToolSearch `select:<name>` before calling)
- `mcp__claude_ai_Atlassian__searchJiraIssuesUsingJql` — primary
- `mcp__claude_ai_Atlassian__getJiraIssue` — enrichment (sprint, components)
- `mcp__claude_ai_Atlassian__atlassianUserInfo` — accountId cache (first run / monthly)

Load via: `ToolSearch select:mcp__claude_ai_Atlassian__searchJiraIssuesUsingJql,mcp__claude_ai_Atlassian__getJiraIssue,mcp__claude_ai_Atlassian__atlassianUserInfo` before invoking.

## READ-ONLY hard constraint
MUST NOT call: `editJiraIssue`, `transitionJiraIssue`, `createJiraIssue`, `addCommentToJiraIssue`, `addWorklogToJiraIssue`, `createIssueLink`, `updateConfluencePage`, or any write tool. Allowed: `searchJiraIssuesUsingJql`, `getJiraIssue`, `atlassianUserInfo`, `getJiraProjectIssueTypesMetadata`.

## Steps
1. Load cursor. If `account_id` missing or older than 30d → `atlassianUserInfo`, cache.
2. Compute window: `last_run_ts` if present, else `now - 24h`.
3. JQL via `searchJiraIssuesUsingJql`:
   ```
   assignee = currentUser() AND updated >= "<last_run_ts>" AND status != "Done" ORDER BY updated DESC
   ```
   Cap results at 25.
4. For each ticket, classify:
   - **Newly assigned** — key NOT in `known_ticket_keys` → `urgency: today`, `action: "plan placement: today or backlog"`
   - **Sprint changed** — known key + sprint field shifted vs prior state → `urgency: today`, `action: "re-evaluate sprint priority"`
   - **Status changed by someone else** — known + status moved → `urgency: fyi`, `action: "review status change"`
5. Append new keys to `known_ticket_keys`. /today persists cursor on success.

## project_hint
- Inspect `components` and `labels` for `vscode` or `wipdp`
- Else inspect repo prefix on linked PRs (if cheap)
- Else `null`

## Output JSON contract
```json
{
  "source": "jira-new",
  "fetched_at": "<ISO8601>",
  "cursor_advance": "<ISO8601>",
  "items": [
    {
      "source_id": "<ticket_key>",
      "ts": "<updated_at>",
      "title": "<TICKET_KEY>  P<n>  <repo>  <status>  <one-line-title>",
      "action": "plan placement: today | re-evaluate sprint priority | review status change",
      "project_hint": "vscode | wipdp | null",
      "urgency": "today | fyi"
    }
  ],
  "fyi_count": <int>,
  "errors": []
}
```

## Latency budget
- Typical: < 5s (small result count)
- Worst case: < 15s

## Failure modes
- `account_id` missing → fetch via `atlassianUserInfo`, retry once
- API/auth error → return `items: []`, `errors: ["jira: <msg>"]`, do NOT advance cursor
- Sprint field missing on a ticket → skip sprint-change classification (treat as newly-assigned if unknown, else fyi)
- Individual `getJiraIssue` fails → skip ticket, append `errors[]` note with key, continue
- First run with no `last_run_ts` → use `now - 24h`
