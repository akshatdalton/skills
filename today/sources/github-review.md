# github-review source-agent spec

## Purpose
Surface PRs in `EightfoldAI/vscode` and `EightfoldAI/wipdp` where the user is a requested reviewer. These are review-queue items, NOT the user's authored PRs (those are already tracked by /today via `progress.md` frontmatter). Used by /today Step 9 to populate the review block.

## Inputs
- `last_run_ts` — ISO8601 from `~/.claude/skills/today/state/sources/github-review.json`. Informational only; actual filter is "currently assigned for review" since reviews can sit open indefinitely.
- `now` — current timestamp (passed by parent)

## Tools required
- `gh` CLI (NOT GitHub MCP — per user rule). Authenticated against `github.com`.

## Behavior
1. Resolve user handle once: `gh api user --jq .login`.
2. Fetch review queue:
   ```
   GH_HOST=github.com gh search prs \
     --review-requested=@me --state=open \
     --repo EightfoldAI/vscode --repo EightfoldAI/wipdp \
     --limit 40 \
     --json number,title,url,author,createdAt,updatedAt,headRefName,repository
   ```
   Cap at 20 per repo implicitly via `--limit 40` total.
3. For each PR, compute `age_days = (now - createdAt) / 86400`.
4. Sort items by age descending (oldest first).
5. Optionally enrich up to 3 oldest PRs in parallel with:
   `gh pr view <N> --repo <repo> --json reviewDecision,latestReviews`
   to detect if user has already left a review (skip in output if user is in `latestReviews` with state APPROVED or CHANGES_REQUESTED and no newer commit). Hard cap: 3 enrichment calls per run.
6. For each kept PR, build the output item:
   - `source_id` = `"<repo>#<number>"` (e.g. `"vscode#1234"`)
   - `ts` = PR `createdAt`
   - `title` = `"<repo>#<N>  @<author>: <title-truncated-60>  (Nd old)"`
   - `action` derivation:
     - default: `"review and approve"`
     - if enrichment showed prior CHANGES_REQUESTED that author re-pushed against: `"re-review after author updates"`
     - if title contains `WIP` or `[DRAFT]`: `"comment with questions"`
   - `project_hint`: derived from repo — `EightfoldAI/vscode` → `"vscode"`, `EightfoldAI/wipdp` → `"wipdp"`. Never null for this source.
   - `urgency`:
     - `"now"` if `age_days > 5`
     - `"today"` if `age_days <= 1` (opened in last 24h)
     - `"fyi"` otherwise (1 < age_days <= 5)
7. Return the JSON contract below. Set `cursor_advance = now` only if no errors occurred.

## Output JSON contract
EXACTLY this shape (parent expects it):
```json
{
  "source": "github-review",
  "fetched_at": "<ISO8601>",
  "cursor_advance": "<ISO8601>",
  "items": [
    {
      "source_id": "<repo>#<number>",
      "ts": "<createdAt>",
      "title": "<repo>#<N>  @<author>: <title-truncated-60>  (Nd old)",
      "action": "review and approve | review and request changes | comment with questions | re-review after author updates",
      "project_hint": "vscode | wipdp",
      "urgency": "now | today | fyi"
    }
  ],
  "fyi_count": 0,
  "errors": []
}
```

## Latency budget
- Target: under 5 seconds normal case.
- Single `gh search prs` call + up to 3 parallel `gh pr view` enrichments.
- Cap to 20 PRs per repo. If search returns more, take the 20 oldest per repo.

## Edge cases
- `gh` not authenticated → `errors: ["gh auth required; run gh auth login"]`, `items: []`, DO NOT advance cursor.
- Network / API failure → `errors: ["<error msg>"]`, `items: []`, DO NOT advance cursor.
- Empty review queue → `items: []`, `fyi_count: 0`. Parent renderer collapses to "0 PRs queued for your review".
- Enrichment call fails → skip enrichment for that PR, fall back to default `action`, do not record as fatal.
- Author is the user themselves (shouldn't happen via `--review-requested=@me`, but defensive): drop the item.
- Title >60 chars: truncate with single trailing ellipsis char (`…`).

## Cursor advance rule
Set `cursor_advance` to `now` only on success (no fatal error). Parent persists to `~/.claude/skills/today/state/sources/github-review.json`. The cursor is FYI only — never used as a filter on the next run, because review-requests can sit open for weeks.

## Hard constraint — READ-ONLY
This agent NEVER calls `gh pr review`, `gh pr comment`, `gh pr merge`, `gh pr close`, `gh pr edit`, or any write-side `gh` command. Allowed surface: `gh search prs`, `gh pr view`, `gh api repos/*/pulls/*` (GET only), `gh api user`.
