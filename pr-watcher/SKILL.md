---
name: pr-watcher
description: Watch open PRs for CI completion, auto-fix safe failures, post shipit when clean, merge wipdp PRs against main. Designed to run inside `/loop 30m /pr-watcher` in a dedicated Claude Code "watcher tab" — replaces broken cron-based watchers (claude -p auth + crontab edit fail in macOS cron context). Reads/writes a single shared state file so any other Claude session can add/remove watches. Use when user wants to leave a tab running to monitor PRs, or when invoked by /loop.
---

# pr-watcher

PR-watching agent with four sub-modes. Designed to be driven by `/loop` once a watch exists.

## Sub-modes

The user's invocation determines the mode:

| Phrase | Mode |
|---|---|
| `add <PR url or owner/repo#N>` to /pr-watcher | [ADD](#add-mode) |
| `remove <PR url or owner/repo#N>` from /pr-watcher | [REMOVE](#remove-mode) |
| `list` /pr-watcher / "what's being watched" | [LIST](#list-mode) |
| `pause shipit on <PR>` / `enable shipit on <PR>` | [CONFIG](#config-mode) |
| Invocation by /loop with no extra args, OR "tick now" | [TICK](#tick-mode) |

If no mode is unambiguous from the user's phrasing, ask before doing anything.

## ADD mode

1. Parse PR identifier (`owner/repo#N` or full URL).
2. Fetch initial state: `gh pr view <id> --json headRefOid,baseRefName,headRefName`.
3. Append to `~/.claude/scheduled/state/watch-state.json` under `watches[<owner/repo#N>]`:
   ```json
   {
     "added_at": <unix_ts>,
     "added_by_dir": "<pwd>",
     "branch": "<headRefName>",
     "last_sha": "<headRefOid>",
     "last_state": "pending",
     "last_notified_state": null,
     "last_review_comment_id": null,
     "auto_action_attempted": false,
     "auto_shipit_enabled": true
   }
   ```
4. **Auto-start the loop** by invoking the `loop` skill via the `Skill` tool with `args: "1h /pr-watcher"`. (User can change interval; default 1h matches CI cadence.)

   **Default to local in-session loop, NEVER cloud.** If `/loop` asks via AskUserQuestion whether to set up a cloud schedule (CronCreate) instead — always answer **"keep local"**. The user has explicitly chosen local-only as the default for PR watchers, and does not want to be re-prompted. Only escalate to cloud if the user types "schedule on cloud" / "use CronCreate" explicitly. Same rule applies to `/get-pr-ready-to-merge` Step 7.

5. Print confirmation: "Added <id>. /loop 1h /pr-watcher started in this tab — leave it open."

## REMOVE mode

1. Parse PR id.
2. Delete `watches[<id>]` from state file.
3. If `watches` is now empty, print "No watches remain. Loop will end on next tick."

## LIST mode

Read state file. Print compact table. Mark `auto_shipit_enabled=false` entries that have been waiting `>24h` with a `⚠ stale pause` flag — surfaces forgotten "no shipit yet" decisions so user can re-confirm or unpause:

```
PR                              State            Auto-shipit  Added       Flag
EightfoldAI/vscode#105039       passing          off          14:54       ⚠ stale pause (>24h, confirm?)
EightfoldAI/vscode#105792       pending          on           16:46
```

Compute stale-pause: `auto_shipit_enabled=false` AND `now - added_at > 86400`.

## CONFIG mode

- "pause shipit on <id>" / "don't post shipit yet on <id>" → set `watches[<id>].auto_shipit_enabled = false`
- "enable shipit on <id>" / "ok ship <id>" → set `auto_shipit_enabled = true` (next tick will post if state still passing+clean)

## TICK mode

This is what /loop invokes. See [Per-tick algorithm](#per-tick-algorithm).

## Stopping

- Delete all watches → loop ends naturally on next tick (skill exits without ScheduleWakeup).
- `/loop stop` in the watcher tab → immediate halt.

## State file

Location: `~/.claude/scheduled/state/watch-state.json`

```json
{
  "watches": {
    "<owner>/<repo>#<number>": {
      "added_at": <unix_ts>,
      "added_by_dir": "<absolute path of session that added it>",
      "branch": "<branch name>",
      "last_sha": "<head sha at last check>",
      "last_state": "pending|failing_autofix|failing_user|passing|merged|timed_out",
      "last_notified_state": "<the state we last sent ntfy for, or null>",
      "last_review_comment_id": "<id of newest review comment we've seen>",
      "auto_action_attempted": false,
      "auto_shipit_enabled": true
    }
  },
  "config": {
    "timeout_hours": 4,
    "auto_fix_scope": ["lint_ruff", "lint_eslint", "format", "sort_imports"],
    "merge_strategy": {
      "EightfoldAI/wipdp": { "to_main_branch": "squash_merge_direct", "to_feature_branch": "shipit_comment" },
      "EightfoldAI/vscode": { "to_main_branch": "shipit_comment", "to_feature_branch": "shipit_comment" }
    }
  }
}
```

## Per-tick algorithm

(This section applies to TICK mode only.)


1. Read state file. If `watches` is empty:
   - Print: "No watches active. Loop will end."
   - Exit. (Do NOT call ScheduleWakeup.)

2. For each watch entry:

   a. **Fetch current state** for the PR:
      ```
      gh pr view <owner>/<repo>#<number> --json headRefOid,state,isDraft,baseRefName,reviewDecision,reviews,comments
      gh api repos/<owner>/<repo>/commits/<sha>/check-runs
      gh api repos/<owner>/<repo>/commits/<sha>/status
      gh api repos/<owner>/<repo>/pulls/<number>/comments
      ```

   b. **Classify** the state — see [Classification](#classification) below.

   c. **Pick action** from [Action matrix](#action-matrix). Take exactly one action.

   d. **Update** the watch entry's `last_state`, `last_sha`, `last_notified_state`, `last_review_comment_id`. Write state file.

3. After walking all watches, write state file. Print summary.

## Classification

For a single PR, determine state in this order:

| Order | Test | State |
|---|---|---|
| 1 | `now - added_at > timeout_hours * 3600` | `timed_out` |
| 2 | PR is merged (gh: state=MERGED) | `merged` |
| 3 | Any check-run with status `in_progress` or `queued`, OR any status with state `pending` | `pending` |
| 4 | Any check-run conclusion `failure`/`cancelled`/`timed_out`, OR any status state `failure`/`error` | classify failures: if all failures are in `auto_fix_scope` → `failing_autofix`; else → `failing_user` |
| 5 | All checks complete, no failures, AND `reviewDecision` is null/REVIEW_REQUIRED, AND no review comments AND no reviews yet | `passing_no_review` |
| 6 | All checks complete, no failures | `passing` |

## Action matrix

| State | New comments since `last_review_comment_id`? | Action |
|---|---|---|
| `pending` | no | Silent. Update `last_state=pending`. |
| `pending` | yes | Notify "N new review comments on #X". Update `last_review_comment_id`. |
| `timed_out` | — | Notify ONCE. Remove watch entry. |
| `failing_autofix` (and `auto_action_attempted=false`) | — | Run [auto-fix](#auto-fix), commit, push. Set `auto_action_attempted=true`, `last_sha=<new>`. Stay in watches. |
| `failing_autofix` (and `auto_action_attempted=true`) | — | Notify ONCE "auto-fix didn't resolve #N". Remove watch. |
| `failing_user` | — | Notify ONCE "CI failed on #N — needs your input. Run: /get-pr-ready-to-merge <PR_URL>". Remove watch. |
| `passing_no_review` | — | If `last_notified_state != "passing_no_review"`: notify ONCE "✓ #N is green and untouched by reviewers — time to ping reviewers to unblock the task". Then silent. Stay in watches. |
| `passing` | yes | Notify "passing but N new comments on #X". Stay in watches one more tick to let user respond. |
| `passing` + `auto_shipit_enabled=false` | no | If `last_notified_state != "passing"`: notify ONCE "ready for shipit on #N — say 'enable shipit on <id>' to auto-post". Then silent. Stay in watches. |
| `passing` + `auto_shipit_enabled=true` | no | [Resolve to merge action](#merge-resolution). |
| `merged` | — | Notify "merged #N". Remove watch. |

### Merge resolution

Look up `config.merge_strategy[<owner>/<repo>]`. Determine `is_to_main` = `baseRefName in ["main", "master"]`.

| Strategy lookup | Action |
|---|---|
| `shipit_comment` | `gh pr comment <PR> --body "shipit"`. Notify "shipit posted on #N". Remove watch. |
| `squash_merge_direct` | `gh pr merge <PR> --squash --delete-branch`. Notify "merged #N". Remove watch. |

Pre-flight checks before EITHER action: PR not draft, no unresolved review threads (use `gh api .../pulls/<N>/reviews` and `.../comments` — fail open if any review state is `CHANGES_REQUESTED` or any comment thread has `isResolved=false`). If pre-flight fails → notify "passing but blocked: <reason>", stay in watches.

## Auto-fix

In Phase 1, scope is intentionally narrow:

- `lint_ruff`: `cd <repo> && ruff check --fix . && ruff format .`
- `lint_eslint`: `cd <repo> && npx eslint --fix .`
- `format`: same as above (umbrella)
- `sort_imports`: `ruff` handles for python; eslint plugin handles for JS

After fix:
```
git add -u
git commit -m "Auto-fix: <scope> via /pr-watcher"
git push
```

Branch must already be checked out in the dir referenced by `added_by_dir`. If `pwd != added_by_dir`, `cd` there first. If branch doesn't match → notify "auto-fix skipped: branch mismatch", set `auto_action_attempted=true` so we don't loop on it.

## Notifications

Use ntfy.sh topic `claude-code-reminders`:

```bash
curl -s \
  -H "Title: <emoji> <short title>" \
  -H "Priority: <default|urgent>" \
  -H "Tags: <tag>" \
  -d "<message body with PR URL and any next-step command>" \
  ntfy.sh/claude-code-reminders
```

Title prefixes: ✓ for success/passing, ✗ for failure/blocked, ◑ for new-comments, ⏱ for timeout.

## Adding a watch from another skill

Other skills (e.g., `/get-pr-ready-to-merge` after a successful push) trigger ADD mode by invoking pr-watcher with the add phrasing. They MUST also chain `Skill(skill="loop", args="1h /pr-watcher")` after — that's what makes the watcher self-starting from the chain.

## End-of-tick output

After walking all watches, print a compact table:

```
PR                                    State            Action this tick
EightfoldAI/vscode#105343             pending          silent
EightfoldAI/wipdp#62                  passing          posted shipit, removed
EightfoldAI/vscode#105165             failing_user     notified, removed
```

Then either let `/loop` schedule the next tick (if any watches remain), or print "No watches remain — loop ending" and exit without scheduling.

---

## Data Contract

### Reads (DB)
- (none — auto-fix is mechanical scope; deeper triage delegates to `/get-pr-ready-to-merge`)

### Reads (Memory)
- (none from the canonical Memory stores — `pr-watcher` does NOT consume work_hq board or vault hot.md; merge events flow into Memory via other skills)

### Writes (Memory)
- `~/opensource/vault/wiki/log.md` — append on watch state transitions ("vscode#NNN: pending→passing", "wipdp#NN: merged via auto-shipit", "vscode#MMM: failing_user notify")

### Local (skill-only — not canonical data)
- `~/.claude/scheduled/state/watch-state.json` — runtime state of the watch loop (which PRs, last seen state, debounce flags). Skill-private operational state; not consumed by other skills; explicitly NOT a duplicate of vault.

### Live external (not stored)
- `gh pr view` / `gh api repos/.../{check-runs,status,comments}`
- ntfy.sh notifications
