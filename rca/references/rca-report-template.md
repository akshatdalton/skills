# RCA report template

Lazy-loaded at Phase 7. Resolve the path, copy this skeleton, fill every section, keep every claim sourced.

## Path resolution (in order)

1. **Ticket resolves** (CS/IMPL/ENG key; project via `python3 ~/.claude/scripts/progress_fm.py get <TICKET> --field project`) → write into the vault ticket bundle:
   `~/opensource/vault/wiki/projects/<vscode|wipdp>/progress/<TICKET>/rca-<YYYY-MM-DD>.md`
   Drop sibling artifacts (owner lists, repro scripts) in the same dir, e.g. `rca-<date>-owners.md` — mirroring `~/opensource/vault/raw/oncall/2026-06-01-se-career-level-80-owners.md`.
2. **PagerDuty / Slack / no ticket** → `~/opensource/vault/raw/oncall/<YYYY-MM-DD>-<slug>.md` (dir exists); else `~/.claude/rca-reports/<slug>/rca-<YYYY-MM-DD>.md`.
3. **Never** write the RCA body into `progress.md` itself — it's a SIBLING file. `/brain-ingest` distills it into `progress.md` + `learnings.md` at session wrap.

## Skeleton

```markdown
---
rca: <CS/IMPL/ENG key | incident-id | slug>
signal: <jira | slack | pr | pagerduty | session>
created: <YYYY-MM-DD>
status: investigating | root-cause-confirmed | fix-proposed | resolved
region: <us-west-2 | eu-central-1 | westus2 | ...>
---

# RCA — <one-line plain-words title + the punchline>

## Signal
<what fired this: alarm / ticket / thread + reporter + symptom + window. Link the source (absolute path / permalink).>

## Bottom line (observed / inferred / verified)
<2-3 sentences. The single verified root-cause fact. State the health word plainly.>

## Depth-bar ladder (each rung proven)
| Rung | Finding | Label | Artifact |
|---|---|---|---|
| symptom | <e.g. profile_details 500> | observed | <Logs Insights link / SQL> |
| endpoint | <e.g. /api/career_hub/v1/entity/...> | observed | <www_server_log row> |
| field | <e.g. efcustom_text_career_level_field> | verified | <file:line> |
| exact value | <e.g. 80> | observed | <row> |
| value TYPE | <e.g. int, expected str> | verified | <EC2 repro> |
| owners/rows | <e.g. 102 of 133 profiles> | verified | <DW scan> |
| source of bad data | <e.g. HRIS ingest ~07:00 UTC> | inferred | <updated_at spike SQL> |

## Code trace (file:line tree — failing node marked ▶)
\`\`\`
POST /api/... → entity_details_api.py:160 process_request
  └─ position.py:1813 get_ats_data (no field_name)
       └─ str_utils.py:1287 fast_json_loads        ▶ full-materialize → RSS climb
            └─ os_utils.py:431 check_max_rss_size   ▶ raises MemoryError → 500
\`\`\`

## Fix — two tracks
- **Immediate (symptom-stopper):** <gate/flag, no deploy> — owner <…> — <config artifact>
- **Underlying defect:** <data correction / code change> — owner <…> — separate track/ticket

## UI verification (before / after)
- Before: <what the user sees / what re-runnable SQL or product link shows the bug>
- After: <what confirms the fix — re-runnable SQL or product link, NOT a customer-account screenshot>

## To forward (jargon-free, self-validatable) — for CS → customer
<clean customer summary, no internal table/gate names + the link/SQL they can run themselves>

## Artifact links (absolute paths / permalinks)
<every claim above is sourced here>

## Open follow-ups
<carried to ../state/rca_followups.md — the NEXT (waiting) items>
```
