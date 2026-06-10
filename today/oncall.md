# On-Call Command Center — /today oncall

Lazy-loaded sub-mode (read only when `/today oncall …` is invoked). Akshat is the **TM / Career Hub India primary on-call**. This file is the operating model + the live driver. US counterpart: Mrugank Upadhyay. Handover source: Vasu Gurram (KT 2026-06-01).

> Tooling rule (same as parent /today): `gh` for GitHub, Atlassian MCP for Jira, PagerDuty MCP for incidents/schedules, AWS CLI for CloudWatch/logs, `read-config`/`query-data` skills + eightfold MCP for platform config & DB. NEVER `slack_send_*` without ALL-CAPS YES (`[[feedback-slack-send-requires-caps-yes]]`).

## Fixed references (verify live, don't trust stale)

| Thing | Value |
|---|---|
| Main on-call dashboard | https://eightfoldai.atlassian.net/jira/dashboards/10016 — add **ARDM / TM** filter → your box (~37 issues at KT) |
| Triage dashboard (FYI only) | https://eightfoldai.atlassian.net/jira/dashboards/18225 |
| Tracking sheet | https://docs.google.com/spreadsheets/d/1K_stAjOZO5IVKf-DcIpj4_fHfqfMj3MOTovywVwOFyU — **add a NEW sheet each on-call sprint**, list your tickets + status + short comment |
| Main channel | `#ext-tm_oncall` C04AB2A4VAT — PagerDuty feed + user reports |
| Secondary channel | `#ext-customerissues-tm` C016AR3F2TH — ext-talent-design merged in here |
| Build alerts | `#build_alerts` C02M1HSHDUH — Playwright/pytest failures |
| PD: Career Hub Primary schedule | `PBWVBGY` (you = `P3PA61T`) |
| PD: Career Hub Secondary | `PK9L3IW` → Amenreet Singh Sodhi `P75P9CK` |
| PD: TM on-call manager | `P5KFRG2` → Shailendra Jaiswal `PDAVCEC` |
| PD: my Career Hub escalation policies | `PX1LB7F`, `P2QO5YP`, `PDR10X9`, `P1B9NAP` |
| PD: Career Hub service | `P0IHZZS` |
| Operational on-call (build/Playwright) | check live; KT said Fenil Mehta primary, **Gautam Kumar lead** (PCS Primary `PFLGTU7`) |
| TD help | Sai / Padma |
| Claude token top-up | Pankaj Rajan (`@bunker`/`@Panka`) |

## The operating model (from Vasu KT)

**Daily order of work** — by **priority level, then due date** (Akshat's rule; Vasu's KT default was due-date-only):
1. Sort P0 → P1 → P2 → P3; within each priority, **overdue → due today → 1d → 3d → no-due**. Pick tickets *assigned to you* first (dashboard → "tickets to triage by engineer", filter = you). Live PagerDuty pages outrank everything.
2. `Dev complete` / `Waiting for Eng` overdue tickets usually just need **verify PR merged + reached stage → close**, not a fresh fix.
2. Each ticket: verify the triage label is correct; if `code-fix-needed` but already dev-complete, fix the label.
3. **Follow up daily** on tickets assigned to *other* people (ping the owner — they often don't know it's assigned). You're primary; chasing is your job.

**Ticket lifecycle:** new issue lands in "to-be-routed" (no triage label) → someone adds a pod label + triage comment (1–2 days) → moves to "triaged" tab → assigned to an engineer → you work/close it. **Close** once the PR is merged and the fix has reached stage.

**Fixing:** pass the ticket + triage comment straight to Claude → it drafts a PR. Mobile bugs are **front-end only** — reproduce by toggling mobile view in the browser, no device needed.
- **Can't reproduce?** Push back on the ticket thread asking for repro detail (often reproducible only when logged in as the reporting user's listing).
- **PR review** = whoever has **code-owner approval** for the touched area (varies: Ashto/Padma/Swign/UI-infra/DP). Label your PRs **`TM on call`** so the sprint count is one filter away.
- **Due dates:** engineers may move them (give a reason). P1 ≈ 1 week / 10 days.

**Escalation:** P0 → act immediately. Build/Playwright failure you're tagged in → tag the **operational on-call**. TD questions → Sai/Padma. User pings without a ticket → tell them to raise one.

## PagerDuty incident playbook ("Too Many Product Exceptions" & friends)

Prereq (one-time): install the **PagerDuty mobile app**, set phone **call + SMS** notifications (easy to miss otherwise).

When paged:
1. Read the alarm's **playbook** + description.
2. Open the **AWS console** link from the alert → find the **alarm window** (red = active/breaching; note start–end, or use "now" if still firing).
3. **DB query** `www_server_log` for 500s in that window, grouped by event + group_id (query template below).
4. **Second query** for the exact log rows of the worst endpoint → pull `user email` from the JSON → log in as that user, reproduce the page.
5. **Diagnose:** *multiple* endpoints failing → **infra** issue; *single* endpoint → likely a **recent code change** — bisect that.

**"Too Many Product Exceptions" threshold:** 10 breaches in a 15-min window; **pages** if breached ≥2× in the last 4 datapoints (~1 hr).

**Preferred path — CloudWatch Logs Insights on the `WWW` log group** (per official playbook [EP/928284673](https://eightfoldai.atlassian.net/wiki/spaces/EP/pages/928284673); needs only `aws` CLI, no db_explorer). For a `[us-west-2]` alarm use log group `WWW`; for `[westus2]` use `azure-WWW`. Start an async query then poll `get-query-results`:
```
fields @timestamp, @message
| filter @message like /Uncaught exception/
| parse @message "Uncaught exception- * in- * for user- * " as ex, endpoint, user
| stats count(*) as counts by ex, endpoint   # add `, user` to see tenant concentration
| sort counts desc | limit 40
```
Then pull raw messages for the top `ex`+`endpoint` (`| filter @message like /<endpoint>/ and @message like /<ExType>/`) to read the trace. **Heuristic refinement (verified 2026-06-01):** if the top offenders are all `eightfolddemo-*` / `*playwright*` / `*selenium*` users → it's **demo/CI test traffic, not a customer incident** (e.g. `view_career_hub` DBClient `RequestTimeoutException` from slow demo-tenant queries). Single real-customer endpoint = code/data bug; many customers = consider revert.

DB-explorer query templates (StarRocks `log.www_server_log`, namespace `career_hub`, exclude stage/dev hosts) — alternative via `query-data` skill / eightfold MCP, or paste into stage db_explorer:
```sql
-- 1) endpoints throwing 500s in the alarm window
SELECT event, group_id, COUNT(*) AS cnt FROM log.www_server_log
WHERE namespace='career_hub' AND response_code=500
  AND hostname NOT LIKE 'stage%' AND hostname NOT LIKE '%dev%'
  AND t_create >= '<START>' AND t_create <= '<END>'
GROUP BY event, group_id ORDER BY cnt DESC LIMIT 100;

-- 2) exact rows for one endpoint (read the JSON: user email, trace, what went wrong)
SELECT * FROM log.www_server_log
WHERE namespace='career_hub' AND response_code=500
  AND hostname NOT LIKE 'stage%' AND hostname NOT LIKE '%dev%'
  AND t_create >= '<START>' AND t_create <= '<END>' LIMIT 100;
```

## ★ Triage depth bar → see `/rca`

The triage depth bar (symptom → endpoint → field → exact value → value's TYPE → owners/rows → source of the bad data) and the observed/inferred/verified discipline now live canonically in **`/rca`** ([SKILL.md](/Users/akshat.v/.claude/skills/rca/SKILL.md) "The contract"). When an on-call page or ticket needs RCA, fire `/rca <signal>`. Do not duplicate the rules here. See `[[feedback-triage-pinpoint-precision]]`, `[[feedback-cite-artifacts-for-audit]]`.

## Known patterns & learnings (from real pages — grow this)

> **RCA discipline + bug-class knowledge is now canonical in `/rca`.** The triage depth bar, the verify-before-assert gate, the authoritative-artifact map, and the recurring bug classes (custom-field str-coercion, RSS-cap `MemoryError`, profile-skills data model, company-logo render, search bulk-download cap, PA-blank-by-design), region sharding, query templates, and data-access governance now live in **`/rca`** ([SKILL.md](/Users/akshat.v/.claude/skills/rca/SKILL.md) + [playbook.md](/Users/akshat.v/.claude/skills/rca/playbook.md)). Fire `/rca <signal>` for any RCA. The patterns below are retained as the on-call **incident-operations** record (and feed `/rca` playbook.md).

1. **"Too Many Product Exceptions" RCA = CloudWatch Logs Insights on `WWW`** (not db_explorer). Parse `Uncaught exception- <ex> in- <endpoint> for user- <user>` → group by `ex,endpoint` then add `,user`. The per-exception-type metrics `www-exceptions.careerhub.<Type>.sum` give a quick composition without logs (no endpoint dim, but type breakdown exists).
2. **Attribution caveat:** the log's `for user-` is the **request viewer**, and `in-` is `request.endpoint` (no path params) — so the **rendered entity/profile_id is NOT in the log**. `apps/index_view.py:373` `all_exception_handler` is the 500 funnel. Don't equate the failing viewer with the data owner without checking the data (for self-service careerhub they usually coincide, but prove it).
3. **These pagers are 500s, not 403s.** Product-exception alarms = uncaught exceptions surfaced as 500. "Gates" like `custom_field_str_data_type_conversion_gate` are **behavior** gates (do/don't coerce), NOT authz/permission gates.
4. **Recurring class — custom-field type mismatch:** `TransformationValidationException: …custom field <f> having value <v>` on profile/entity endpoints → a field declared `string` got a non-`str` value (e.g. int `80`). Fix is the per-customer gate **`custom_field_str_data_type_conversion_gate`** (rollout of **ENG-192050**; owner **lpatel@eightfold.ai / ta-flex@eightfold.ai**). Check `mcp__eightfold__config get_changelog` for which customers are already enabled before proposing.
5. **Confirm code-level fixes by reproduction, not prod data:** drive the two branches directly — `str_utils.convert_to_data_type(dt, val, convert_to_string=False/True)` + `validate_custom_field_value` — to show off=raises / on=passes. Deterministic, no prod access needed.
6. **Customer data is region-sharded** — query in the customer's own region (e.g. `se.com` → `eu-central-1`); scope `mcp__eightfold__db_explorer` / `query-data` to that region. The us-west-2 dev EC2 box has no prod-DB creds.
7. **PagerDuty writes:** add the note (`add_note_to_incident`) **before** resolving (`manage_incidents status=resolved`) so it's on record. **`#ext-tm_oncall` is a Slack Connect channel → `slack_send_message` is blocked; use `slack_send_message_draft`** (user taps send) — also satisfies the caps-YES rule.
8. **Config audit is one tool away:** `mcp__eightfold__config` (`read_config` / `get_changelog` / `run_jq_query`) answers "is feature/gate X on for customer Y, and who changed it when" instantly.
9. **Company logos on Career Hub profiles come from `entities_v2` (Crunchbase-sourced), matched by `norm_name`/`syn_name`, `rank desc`** — render path: `profile.get_experience_entities()` → `entity_objects.get_using_name([...])` → `fetch_from_db` (`www/entity/entity_objects.py`). Two traps proven on IMPL-202919: (a) `entity_update_overrides_config` is **global + only UPDATES existing rows by exact `domain`, never creates** → can't fix a missing/shared-domain company, and any override regresses that company *everywhere*, not just one section; (b) `fetch_from_db` filters `domain NOT LIKE 'eightfolddemo%'` → a company created via `/account#tab-company` under an `eightfolddemo-*` demo account is **excluded** and won't render (verified live: `get_using_name(['Legal Counsel for the Elderly'])` → `None`). Org-correct fix for a missing/shared-domain affiliate logo = **customer creates a Crunchbase entry per company → next Crunchbase DAG imports it** (per Vasu). Don't config-override, don't hand-insert. Verify the live render with `get_using_name([...], skip_cache=True)` in IPython on a box with `global`-DB creds (dev box can't reach `global`).
10. **"Too Many Product Exceptions" where the dominant exception is `MemoryError` = the per-worker RSS guard tripping, NOT a kernel OOM or a logic bug** (verified on #55138, 2026-06-03). Trace shows `os_utils.check_max_rss_size()` (`os_utils.py:431`) raising `MemoryError: Cannot allocate more memory Curr: <X> M Max: <MAX_RSS_SIZE_MB>` (4000 default; it's a **deploy-time env var**, so `config get_changelog` will NOT show it — check deploy/pod-manifest history for onset). It's the app's self-protection valve (abort one request cleanly rather than let the worker grow until the kernel OOM-kills it and drops everything on that worker). **Read it in two layers:** the guard firing = working as designed; the real issue to flag = *why* workers reached the cap. (a) The guard is sprinkled across hot paths, so it trips on whichever request is in-flight once a worker is already over cap → produces a **scatter across many endpoints/products that *looks* like fleet infra but isn't**. Group the Logs Insights output `by user`/tenant: concentration on one tenant+endpoint (here Microsoft `RINAYAK@…` on `entity_details`, 73/95) = **single-tenant heavy-payload / code-data issue**, other products are collateral. (b) **Two trip paths:** `…get_ats_data → fast_json_loads(ats_data) → check_max_rss_size` is **causal** (a big blob deserialized into RAM); `db_connection.execute → request_tracelog.add_event → check_max_rss_size` is **incidental** (the check just sits at that post-query checkpoint — do NOT chase "optimize the DB query"). (c) **Fix layer:** reduce what's loaded per request (lazy/partial load, size cap on the blob), NOT a reflexive `MAX_RSS_SIZE_MB` bump (raising the cap without more host RAM removes the OOM safety margin). (d) The rendered entity id is NOT in CloudWatch (only an `SMID`) — get `position_id`/`profile_id` from `log.www_server_log` (cols incl. `user_email`, `group_id`, `event`, `request_path`, `position_id`, `profile_id`, `viewer_profile_id`). **That table is region-sharded: Azure `[westus2]` tenants (e.g. Microsoft) are NOT in the AWS us-west-2 / eu db_explorer** (verified: 0 `microsoft.com` rows) — pinpointing them needs westus2/Azure DB access.
11. **A repeat page on an already-acked incident — alarm now OK, no new alert, no new incident — is PagerDuty re-notifying a STALE incident on ack-timeout, NOT a re-breach** (verified on #55138). Check: `describe-alarms` State=OK + `list_alerts_from_incident` still shows only the original alert + Logs Insights quiet. The fix for the repeat paging is to **resolve the incident** (note-then-resolve per #7), not to re-investigate. A genuine re-breach fires a *fresh* incident with a *fresh* alert.
12. **Customer "skills / data disappeared from the profile / Profile Assistant" tickets (profile-skills class)** — where to look (verified on CS-17128, Amdocs, 2026-06-03):
    - **Access:** the per-tenant views customers/CSEs paste (`v_<numericid>_profile_skill` / `v_<numericid>_profile_data`) are **NOT queryable from our internal (volkscience) login** → "Unknown table … group_id=volkscience.com". Use the **cross-tenant `analytics.*` tables filtered by `group_id` = DOMAIN** (e.g. `amdocs.com`, NOT the numeric id), in the **customer's region** (EU → `eu-central-1` via `eightfold_eu_internal`). `analytics.profile_v1` = email↔profile_id lookup.
    - **Skill data model (one profile, layered):** `analytics.profile_data` (namespaced rows, carries `updated_at`): `profile_staging:skill_details` (raw upload inbox) · `profile_staging_resume` · `profile_assistant` (accept/dismiss **LOG only**, not skills) · `skill_level` (official live skills). **`analytics.profile_skill_assessment_v2`** = per-skill assessment layer, **raw skill names as uploaded** + self/manager ratings → **this is what PROVES a skill is on the profile** (keeps odd names like "Mobility"/"RTB"/"Rater"). **`analytics.profile_skill`** = a **canonicalized index** built on top: renames to the taxonomy ("RTB"→"Real Time Bidding", raw kept in `original_skill`) and **drops skills that don't map (e.g. "Mobility")** → ⚠ **NOT the source of truth**; querying it is exactly what fools a customer/CSE into "vanished".
    - **Authoritative, self-checkable product views to cite (no raw-table jargon):** the **candidate_profile model** `https://stage.eightfold-eu.ai/models?terms=<profile_id>&model=candidate_profile` (`skill_details` / `ranked_skills`) and **Career Hub → profile → Skills and Performance → My Skills** (search the skill). Both need the data-access grant.
    - **Repair-footprint detection:** group `analytics.profile_data` by `DATE(updated_at)` per namespace → a one-day spike = a bulk script/repair (CS-17128: `skill_level` 16,520 profiles on 05-27 = the CS-17067 manager-assessment repair). Open the rewritten rows: full/normalized = restorative; empty = blanking.
13. **"Profile Assistant is blank/empty" is usually EXPECTED, not data loss.** PA only *suggests* skills that are (a) not yet on the profile AND (b) not already accepted/dismissed. Code (`~/eightfold/vscode`): `www/career_hub/profile/profile_assistant/profile_assistant.py` `get_v2_data():L84` → `_filter_entities_in_profile:L152` (drops skills already on the profile) → `_filter_dismissed_and_accepted_entities:L167` (drops accepted/dismissed, L183-184). Skills are sourced via `ProfileAssistantAtsDataBuilder._get_skills` → `ats_data['skills']` (`profile_assistant_ats_data_builder.py:60`). So once skills are on the profile, PA empties **by design**. The raw uploaded `skill_details` is **not itself** the PA suggestion source — confirm intended design with the PA owners (Yavnika / Fenil / Rohit) before asserting to the customer.
14. **Accessing customer data (per-tenant DB views, candidate_profile model, Career Hub impersonation) requires the "Request Access to Customer Data" form** (`stage.eightfold-eu.ai/internal/data_access`) with a justification ticket URL — it is **recorded against you**. PREP the form but let **Akshat submit** it (personal-accountability action). **Do NOT screenshot inside a customer's Career Hub account** without explicit customer/Yavnika permission. The cross-tenant `analytics.*` queries (#12) need no impersonation, so prefer them for evidence.
15. **Career Hub "an employee can bulk-download the whole staff directory via People Search" tickets (data-exposure class)** — verified on CS-17152 (Wipro, 2026-06-04). Endpoint `GET /api/career_hub/v1/search/profile?search_data_id=search` (`entity_type=profile`). Flow: `entity_search_api.py:535` route → `process_request:551` → `people_search_feed.py:9` `PeopleSearchFeedParams(CareerHubSearchParams)`. **Two stacked ceilings by design:** (a) **per request** ≤ `MAX_LIMIT_FOR_SOLR=1000` (`search_constants.py:86`, `entity_searcher.py:218` "More than 1000 results not supported"); (b) **total reachable** capped only when the per-customer gate **`career_hub_search_cap_start_gate`** is ON — it clamps pagination `start`≤`CAREER_HUB_SEARCH_START_CAP=1000` (`career_hub_search_base.py:291`) → ≤~2000 records total. Gate default `*:0` (OFF); **ON for DTAG = `telekom-growthhub.com`**; OFF for a customer ⇒ they can page `start=0,1000,…` through everything. **Fix = enable the gate for the customer's `group_id`** (config, no deploy). Gate is **locked**; owners **`imalhotra@`/`abhinav.garg@`/`jkearney@`** (DTAG rollout by `prajan@`). ⚠️ The gate caps `start` ONLY, not `page_size`; and `career_hub_search_base.py:279-284` notes processor/scripts/integrations_console callers using `EntitySearchRequest` directly **bypass the cap**. **"Encrypt the API response" customer asks are MOOT for authenticated users** — the browser must decrypt to render, so the user can still save the JSON; HTTPS already covers network interception. Real levers: cap volume (the gate), minimize returned fields (careerhub explore `fields` config via `get_explore_entity_config`), rate-limit. Per-profile fields come from `ProfileDataBuilder.get_entity_card` (config-driven). Validate-don't-trust: a ticket's auto-suggested "Related JIRA" links can be pure red herrings (CS-17152's were matched on `customer=Wipro` only — none related to the actual issue).
16. **"App Platform Processor Error Rate-Net Error Rate - Careerhub" is (almost always) `custom_fields_transform_app_flow` Lambda-not-found NOISE, not a customer outage** (verified on #55561, 2026-06-08). Processor-tier (namespace `processor`, NOT www); a **ratio** `processor-invoke-app-method-errored-careerhub.sum / …-careerhub.sum ×100`, threshold **1%** → pages at **100% on tiny volume** (2 invokes both failing = 100%). **Diagnose:** db_explorer `redshift_log` (region us-west-2) → `app_platform_apps_log` (cols `group_id, app_id, caller_id, trigger_name, lambda_fn, status_code, exception, event_type, t_create`; the runbook's `env` col does NOT exist there): `WHERE event_type='app_invoke_completed' AND status_code<>200 AND exception IS NOT NULL AND t_create>='<win>' GROUP BY caller_id, group_id`. Official runbook = the repo skill `www/services/oncall_auto_triage/v2/skills/app_platform_processor_error_rate.md`, which **excludes `caller_id != 'custom_fields_transform_app_flow'`** as known noise. (a) **Error:** tenant CFT Lambda `appplatform-<tenant>-Custom_Field_Transformation_App…` → `ResourceNotFoundException: Function not found`; `trigger=ats_integrations_transformation_script_save` → `retry_transformation=True` (`app_platform_app_invoker.py:761`) → **retry storm** (230k+ rows/4h; mostly `*-sandbox`, but also prod: appliedmaterials/fisherinvestments/citi/qualcomm/ngc/morganstanley). (b) **Why known-noise still PAGES:** alarm metric gated by `should_emit_alarm_metrics()` (`app_platform_utils.py:1766`) → for SCRIPT_SAVE defers to `AppTransformationEmitErrorHandler.emit_alarm_metrics()` (`app_platform_emit_error_handler.py:51`) = `return not _has_fallback_app()` → **tenants with NO fallback app leak into the metric** → CW shows 1–4/window (gated trickle) while DB shows 230k. (c) **Don't trust "OOM" claims** — #55215 (Mrugank) said "running out of memory" but data = Lambda-not-found. (d) **CW can't attribute to a tenant** — `…errored-careerhub.sum` has `Dimensions:[]` (the `counter_breakdowns=[group_id]` at `app_platform_app_invoker.py:800` isn't a CW dimension). (e) **Lambda existence NOT directly checkable** — `lambda:GetFunction/ListFunctions` IAM-denied for akshat.v; the processor's own `ResourceNotFoundException` is the authoritative evidence. (f) **Resolve = note-then-resolve** the (usually already-OK) alarm per #11; durable fixes = `mute_combinations` (`should_mute_alert` `app_platform_utils.py:1806`) and/or flag prod tenants' missing CFT Lambda to App Platform / DP-Data-Integrations as a SEPARATE track from the page.

## Sub-mode behaviours

### `/today oncall` (default render)
Render an on-call HQ block, freshest first:

1. **Am I on?** — `mcp__pagerduty-api__list_oncalls` filtered to schedule `PBWVBGY` / user `P3PA61T`. Show shift window + secondary (Amenreet) + manager (Shailendra).
2. **Open incidents** — `mcp__pagerduty-api__list_incidents` for service `P0IHZZS`, `statuses=[triggered,acknowledged]`. For each: id, title, urgency, age, ack state. Flag any unacked.
3. **My triaged tickets by priority + due date** — Atlassian JQL (cloudId `eightfoldai.atlassian.net`; load `ToolSearch select:mcp__114f2116-2588-4db6-a487-4f63402d59f0__searchJiraIssuesUsingJql` first):
   `assignee = currentUser() AND statusCategory != Done ORDER BY priority DESC, duedate ASC`, request `fields:[summary,status,priority,duedate,issuetype,labels,project]`. **Separate on-call tickets from your own sprint work**: on-call = Bug/IMPL/CS + `tm-comp-*`/`triaged`/`customer` labels + a due date; exclude ENG Stories tagged `tether-*`/`ccep-*`/`wipdp`/`*-deployment` (those are RAG-for-TM project work). Result is large — save to file and extract with `jq -r '.issues.nodes[] | [.key,.fields.priority.name,.fields.duedate,.fields.status.name,(.fields.summary[0:70])] | @tsv'`.
4. **Follow-ups** — tickets in the TM box assigned to *others* with due date ≤ today → "ping <owner>".
5. **Build alerts** — unresolved tags in `#build_alerts` mentioning you → "tag operational on-call (Gautam/Fenil)".
6. **★ OPEN FOLLOW-UPS** — read `~/.claude/skills/today/state/oncall_followups.md` and render each `[open]` item's title + its `NEXT (waiting)` lines. These are cross-day threads (waiting on someone, pending verification, data pinpoints) that have no Jira ticket. Append new ones there as `## [open] <title>` with a `NEXT` block; mark `[done]` (or delete) when closed. This is what lets a page you diagnosed today still get chased tomorrow.
7. **Sheet nudge** — if a new on-call sprint started and no new tab logged this rotation, remind to add one.

Render ABOVE the normal /today dashboard when invoked as `/today oncall`; otherwise it's a compact one-line "ON-CALL: <n> open incidents, <m> overdue" banner the default render can show.

### `/today oncall page <incident-id|latest>`
Run the PagerDuty playbook above end-to-end:
0. **Resolve the target.** If an incident id is given, use it. If `latest` (or no arg): `list_incidents` for service `P0IHZZS`, `statuses=[triggered,acknowledged]`, sorted newest-first → take the most recent; tie-break by `triggered` over `acknowledged`. If **zero** open incidents, say so and stop (offer the most recently *resolved* one for a post-mortem instead).
1. `get_incident` + `list_incident_notes` + `list_alerts_from_incident` → pull alarm name, region, time.
2. Resolve the alarm window (CloudWatch via AWS CLI if `aws` authed; else surface the AWS console link from the alert and ask user to read the red window).
3. Build + run the two DB queries (substitute window) via `query-data` / eightfold MCP.
4. Output: impacted endpoints, single-vs-multi verdict (code vs infra), the offending user/trace, and a proposed next action. **Never** `manage_incidents` (ack/resolve/reassign) without explicit user confirmation.

### `/today oncall triage <TICKET>`  → ALIAS for `/rca <TICKET>`
RCA discipline now lives canonically in **`/rca`** — prefer typing `/rca <TICKET>` directly. This sub-mode is a thin alias retained for muscle memory:
- Fire `Skill(skill="rca", args="<TICKET>")`. `/rca` drives the depth bar, grounding, tree trace, the persisted RCA report, and offers `/ship-task`.
- On-call-specific add-on only: if `/ship-task` is taken, ensure the PR carries the **`TM on call`** label, and verify/fix the Jira triage label.

### `/today oncall sheet`
Open the tracking sheet; if a new rotation, propose a new sheet tab + draft your ticket rows (ticket · status · short comment) from the live JQL in render step 3. Confirm before writing.

## Driving checklist (how I help each on-call day)

> **★ Verify-before-assert gate → enforced by `/rca`.** Before any load-bearing claim, run /rca's gate: fitness-for-claim · **≥2 independent sources for any *absence*** · quote the recorded artifact for who-did-what · label observed/inferred/verified, never assert flat. See `/rca` [SKILL.md](/Users/akshat.v/.claude/skills/rca/SKILL.md) "The contract" rule 3. (Root cause of every CS-17128 correction; see [[feedback-oncall-data-grounding-and-dual-audience]].)

- [ ] `/today oncall` → confirm shift, surface unacked incidents + overdue tickets in one screen.
- [ ] For each page: `/today oncall page <id>` → diagnosis snippet (no auto-ack).
- [ ] For each code-fix ticket: `/rca <TICKET>` (drives RCA + offers `/ship-task`).
- [ ] Daily follow-up pings drafted (you send — caps-YES rule for Slack).
- [ ] End of day: `/today oncall sheet` → log statuses.
