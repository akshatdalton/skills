# RCA follow-ups (open)

Cross-pass / cross-day investigation state for `/rca`. The recurring `/loop` reads this each tick to resume a signal it's still chasing (waiting on a teammate, pending verification, data settling, fix not yet landed). Mirrors `today/state/oncall_followups.md`.

Append new investigations as `## [open] <title>` with a `NEXT (waiting)` block. Flip to `## [done] <title>` (or delete) when the RCA is resolved.

---

## [open] ENG-197774 — Solr POST RemoteDisconnected on HP CareerHub (2026-06-10)

**Signal:** [Slack C04AB2A4VAT/p1781097553611749](https://eightfoldai.slack.com/archives/C04AB2A4VAT/p1781097553611749) + [ENG-197774](https://eightfoldai.atlassian.net/browse/ENG-197774)
**Status:** root-cause-confirmed; Track A fix ready; Track B needs SRE
**Report:** `~/opensource/vault/wiki/projects/vscode/progress/ENG-197774/rca-2026-06-10.md`

NEXT (waiting):
- Track A PR: `search_utils.py:2691` — `TCPKeepAliveAdapter(max_retries=2)` → explicit `Retry(total=3, ..., allowed_methods={"GET","POST",...})` — waiting for `/ship-task ENG-197774`
- Track B: SRE check Solr Jetty `connector.idleTimeout` + LB `idle_timeout` in us-west-2 — separate infra ticket
- Staging verify: reproduce idle-then-search (3–5 min wait) → confirm no 502, Sentry #286312 stops growing
