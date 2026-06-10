# /rca playbook — eightfold data-source domain knowledge

Lazy-loaded. Read this once an investigation touches eightfold data. It holds the **grounding knowledge** the depth bar runs on: which store is authoritative, the recurring bug classes + their fixes, region sharding, query templates, data-access governance, and the demo-account replication recipe. (Migrated from `today/oncall.md`; the on-call *incident-ops* patterns stay there.)

> Tooling: `gh` for GitHub, Atlassian MCP for Jira, AWS CLI for CloudWatch, `read-config`/`check-gate` + eightfold MCP (`db_explorer`/`config`) for platform DB & config, `/efx` for EC2 repro. NEVER `slack_send_*` without ALL-CAPS YES.

## Authoritative-artifact map (rule 4 — prove "present" with the source of truth)

**Profile-skills class** ("skills/data disappeared from the profile / Profile Assistant") — verified on CS-17128 (Amdocs):
- **Access:** the per-tenant views customers/CSEs paste (`v_<numericid>_profile_skill` / `v_<numericid>_profile_data`) are **NOT queryable from our internal (volkscience) login**. Use the cross-tenant **`analytics.*`** tables filtered by `group_id` = **DOMAIN** (e.g. `amdocs.com`, not the numeric id), in the customer's region (EU → `eu-central-1` via `eightfold_eu_internal`). `analytics.profile_v1` = email↔profile_id lookup.
- **Skill data model (one profile, layered)** — `analytics.profile_data` (namespaced rows, carries `updated_at`): `profile_staging:skill_details` (raw upload inbox) · `profile_staging_resume` · `profile_assistant` (accept/dismiss **LOG only**, not skills) · `skill_level` (official live skills).
- **`analytics.profile_skill_assessment_v2`** = per-skill assessment layer, **raw skill names as uploaded** + self/manager ratings → **this PROVES a skill is on the profile** (keeps odd names like "Mobility"/"RTB").
- **`analytics.profile_skill`** = a **canonicalized index** built on top: renames to taxonomy ("RTB"→"Real Time Bidding", raw kept in `original_skill`) and **drops skills that don't map (e.g. "Mobility")** → ⚠ **NOT the source of truth**. Querying it is exactly what fools a customer/CSE into "vanished".
- **Self-checkable product views to cite (no raw-table jargon):** the **candidate_profile model** `https://stage.eightfold-eu.ai/models?terms=<profile_id>&model=candidate_profile` (`skill_details` / `ranked_skills`), and **Career Hub → profile → Skills and Performance → My Skills** (search the skill). Both need the data-access grant.
- **Repair-footprint detection:** group `analytics.profile_data` by `DATE(updated_at)` per namespace → a one-day spike = a bulk script/repair. Open the rewritten rows: full/normalized = restorative; empty = blanking.

## Attribution — viewer ≠ owner (rule 5)

The log's `for user-` is the **request viewer**, and `in-` is `request.endpoint` (no path params) — so the **rendered entity/profile_id is NOT in the log**. `apps/index_view.py:373` `all_exception_handler` is the 500 funnel. Don't equate the failing viewer with the data owner without querying the data store (for self-service careerhub they often coincide — prove it; on CS-17128 it was 102 owner profiles, not the 133 viewers).

## Region sharding (rule 3 grounding — query in the customer's own region)

- Customer data is region-sharded — query in the customer's region (`se.com` → `eu-central-1`); scope `db_explorer` / `query-data` to that region. The us-west-2 dev EC2 box has **no prod-DB creds**.
- **Azure `[westus2]` tenants (e.g. Microsoft) are NOT in the AWS us-west-2 / eu `db_explorer`** (verified: 0 `microsoft.com` rows in StarRocks). Microsoft's `www_server_log` is only in **databricks**, reachable via the **stage db_explorer console** `stage.eightfold-wu.ai/internal/db_explorer?database=databricks…&region=westus2` (SSO, Eightfold Work Chrome profile). The MCP `db_explorer` `region` param works but its whitelist has no `databricks`.

## Recurring bug classes (match the symptom, then prove the rung)

1. **Custom-field type mismatch** — `TransformationValidationException: …custom field <f> having value <v>` on profile/entity endpoints → a field declared `string` got a non-`str` value (e.g. int `80`). Immediate fix = per-customer gate **`custom_field_str_data_type_conversion_gate`** (rollout ENG-192050; owner `lpatel@eightfold.ai` / `ta-flex@eightfold.ai`); check `mcp__eightfold__config get_changelog` for who's already enabled. **Two tracks:** the gate coerces int→string (stops the 500); the value is still bad data — flag source correction. Confirm by reproduction, not prod: drive `str_utils.convert_to_data_type(dt, val, convert_to_string=False/True)` + `validate_custom_field_value` (off=raises / on=passes). These are **behavior** gates, not authz — product-exception alarms are 500s (uncaught exceptions), not 403s.
2. **RSS-cap `MemoryError`** — dominant exception `MemoryError` = the per-worker RSS guard `os_utils.check_max_rss_size()` (`os_utils.py:431`) tripping at `MAX_RSS_SIZE_MB` (4000 default; a **deploy-time env var**, so `config get_changelog` won't show it — check deploy/pod-manifest history). NOT kernel OOM, NOT a logic bug; it's the self-protection valve. Trips on whichever request is in-flight once a worker is over cap → **scatter across endpoints that *looks* like fleet infra but isn't** — group Logs Insights `by user`/tenant; concentration on one tenant+endpoint = single-tenant heavy-payload issue, the rest is collateral. **Causal path:** `position.py get_ats_data → str_utils.fast_json_loads(ats_data) → check_max_rss_size`. **Incidental path:** `db_connection.execute → request_tracelog.add_event → check_max_rss_size` (don't chase "optimize the query"). **Fix layer:** reduce what's loaded per request (lazy/partial/size-cap), NOT a reflexive `MAX_RSS_SIZE_MB` bump.
3. **Company-logo / entity render** — logos come from `entities_v2` (Crunchbase-sourced), matched by `norm_name`/`syn_name`, `rank desc`: `profile.get_experience_entities()` → `entity_objects.get_using_name([...])` → `fetch_from_db` (`www/entity/entity_objects.py`). Traps (IMPL-202919): (a) `entity_update_overrides_config` is **global + only UPDATES existing rows by exact `domain`, never creates** → regresses that company everywhere; (b) `fetch_from_db` filters `domain NOT LIKE 'eightfolddemo%'` → a company created under an `eightfolddemo-*` demo account is **excluded**. Org-correct fix = customer creates a Crunchbase entry → next DAG imports it. Verify the render with `get_using_name([...], skip_cache=True)` in IPython on a box with `global`-DB creds.
4. **Search bulk-download / data-exposure** — `GET /api/career_hub/v1/search/profile`: per-request ≤ `MAX_LIMIT_FOR_SOLR=1000`; total reachable capped only when the per-customer gate **`career_hub_search_cap_start_gate`** is ON (clamps pagination `start`≤1000 → ≤~2000). Default OFF → customer can page through everything. Fix = enable the gate for the `group_id` (config, no deploy; gate is locked, owners `imalhotra@`/`abhinav.garg@`/`jkearney@`). ⚠ caps `start` only, not `page_size`; processor/scripts callers using `EntitySearchRequest` bypass it. "Encrypt the response" asks are moot for authenticated users.
5. **Profile Assistant blank** is usually EXPECTED, not data loss — PA only suggests skills (a) not yet on the profile AND (b) not already accepted/dismissed: `profile_assistant.py get_v2_data():L84` → `_filter_entities_in_profile:L152` → `_filter_dismissed_and_accepted_entities:L167`. Once skills are on the profile, PA empties by design. Confirm with PA owners (Yavnika / Fenil / Rohit) before asserting to the customer.

## Grounding query templates

**CloudWatch Logs Insights on the `WWW` log group** (`[us-west-2]` → `WWW`; `[westus2]` → `azure-WWW`) — needs only `aws` CLI:
```
fields @timestamp, @message
| filter @message like /Uncaught exception/
| parse @message "Uncaught exception- * in- * for user- * " as ex, endpoint, user
| stats count(*) as counts by ex, endpoint   # add `, user` to see tenant concentration
| sort counts desc | limit 40
```
Then pull raw messages for the top `ex`+`endpoint` to read the trace. **Heuristic:** if top offenders are all `eightfolddemo-*` / `*playwright*` / `*selenium*` → it's demo/CI test traffic, not a customer incident.

**db_explorer (StarRocks `log.www_server_log`, namespace `career_hub`):**
```sql
-- endpoints throwing 500s in the alarm window
SELECT event, group_id, COUNT(*) AS cnt FROM log.www_server_log
WHERE namespace='career_hub' AND response_code=500
  AND hostname NOT LIKE 'stage%' AND hostname NOT LIKE '%dev%'
  AND t_create >= '<START>' AND t_create <= '<END>'
GROUP BY event, group_id ORDER BY cnt DESC LIMIT 100;
-- then: SELECT * FROM … same WHERE … LIMIT 100;  -- read the JSON: user email, trace
```
Cols incl. `user_email`, `group_id`, `event`, `request_path`, `position_id`, `profile_id`, `viewer_profile_id`.

## Data-access governance (rule 9 — keep evidence forwardable + PII-safe)

Accessing customer data (per-tenant DB views, candidate_profile model, Career Hub impersonation) requires the **"Request Access to Customer Data" form** (`stage.eightfold-eu.ai/internal/data_access`) with a justification ticket URL — it is **recorded against you**. PREP the form but let **Akshat submit** it. **Do NOT screenshot inside a customer's Career Hub account** without explicit customer/Yavnika permission. The cross-tenant `analytics.*` queries need no impersonation — prefer them for evidence. Evidence rank: re-runnable SQL / a link the recipient can execute > screenshot > assertion.

## Demo-account replication recipe (optional — when a controllable env helps)

Not every investigation needs this. When reproduction or fix-verification benefits from a controllable environment (rather than reading prod data you may lack access to), replicate the case in the **demo account `eightfolddemo-ashutosh.tanwar.com`** via `/efx`:
- **Set up the case:** use `/efx` (IPython on the dev box, or the demo tenant's API) to construct the minimal data/config that reproduces the reported bug in the demo account.
- **Reproduce:** trigger the failing endpoint/flow for the demo account and confirm the same symptom (the 500, the missing skill, the wrong logo) — this turns an inferred hypothesis into a verified repro without touching the customer's data.
- **Verify the proposed check/fix:** apply the proposed gate/config/code change against the demo account and confirm the symptom clears — gives a before/after you can show without a customer-account screenshot.
- Caveats: demo tenants are `eightfolddemo-*`, so anything filtered by `domain NOT LIKE 'eightfolddemo%'` (e.g. entity logos, bug class #3) will behave differently — note when the demo env can't model the real path. Demo/CI traffic also shows up as `eightfolddemo-*`/`*playwright*` in Logs Insights (don't confuse it with a customer incident).
