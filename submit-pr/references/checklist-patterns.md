# Checklist Patterns Reference

## Product-area assignment (1e flag → area)

**Always pre-check exactly one.** Never multiple.

| Path pattern | Area |
|---|---|
| `www/connectors/`, `www/apps/connectors_app/` | **DP** (true data-plane: connector ingestion, RAG pipeline, customer-impact) |
| `www/apps/tether_app/` | **TM** (Tether is Manager Agent territory, NOT DP) |
| `www/career_hub/agents/` | **TM** (Manager Agent backend) |
| `www/react/src/apps/careerHub/teamPlanning/.../ManagerWorkflows/` | **TM** (Manager Agent UI) |
| Other `www/react/**` UI changes | infer from sibling cues; default **TM** |

**Anti-pattern:** Pre-checking `[x] DP` for any backend connector touch. DP = data-plane *customer impact*, not "you touched a connector file." Evidence: PRs #104387, #104429 had `[x] DP` un-checked at merge.

## Backend / true data-plane (DP)
For PRs in `www/connectors/`, `www/apps/connectors_app/`, RAG pipeline.

```markdown
- [x] DP
- [x] Regression testing is not required because new data-plane module, no customer impact
- [x] It is a bug-fix/usability fix that is common for all group_ids and safe to rollout
- [x] This change is easy to read, review, debug and maintain
- [x] None return values are handled gracefully
- [x] Not applicable  ← Product Security
- [ ] No additional tests are needed because _____   ← LEAVE UNCHECKED, blank intact, when "tests cover the changes" row is [x]
- [x] No user visible strings are introduced in this PR.
- [x] This PR does not contain any UI changes.
- [x] Not applicable - This change does not impact AI Recruiter functionality.
- [x] Not Applicable - This change is not related to DjSafe Schema.
- [x] Description not required
- [x] If scripts are used in DAGs, list tested regions: NA
- [x] If new dags in dags_config.json need to run in westus2, westus2 has been added as a region in the dag json.
- [x] I have gone through the updated checklist.
```

## Frontend / UI (TM/TA/TD) — including Tether & Manager Agent backends

```markdown
- [x] TM   ← or TA, TD — whichever applies
- [x] This change could affect the performance of:
  - [x] TM Marketplace   ← or relevant area
- [x] Regression testing is not required because _____
- [x] It is a bug-fix/usability fix that is common for all group_ids and safe to rollout
- [x] This change is easy to read, review, debug and maintain
- [x] Undefined/Null return values are handled in react/JS gracefully
- [x] Not applicable  ← Product Security
- [ ] No additional tests are needed because _____   ← LEAVE UNCHECKED, blank intact, when "tests cover the changes" row is [x]
- [x] No user visible strings are introduced in this PR.
- [x] This PR does not contain any UI changes.   ← or keyboard/axe tested
- [x] UI changes have been verified for placement and positioning overflows for different screen sizes/zoom levels   ← MUST be checked for any *.tsx/*.jsx PR (most-flipped row at merge: 8 PRs)
- [x] Not applicable - This change does not impact AI Recruiter functionality.
- [x] Not Applicable - This change is not related to DjSafe Schema.
- [x] Description [customer-facing changelog]: _____
- [x] If scripts are used in DAGs, list tested regions: NA
- [x] If new dags in dags_config.json need to run in westus2, westus2 has been added as a region in the dag json.
- [x] I have gone through the updated checklist.
```

## Backend-only Python PR (suppress UI sub-tree)

When `IS_BACKEND_ONLY=true` (no `*.tsx/*.jsx`), the i18n + A11y sub-rows get pruned at merge (evidence: #105216 stripped 4 rows). Emit ONLY these two summary lines under the UI sub-section, suppress everything below them:

```markdown
- [x] No user visible strings are introduced in this PR.
- [x] This PR does not contain any UI changes.
```

## Endpoint-touching add-on (IS_ENDPOINT=true)

When `endpoint_validation/schemes/**/*.json` OR a new Flask route in `www/apps/**/*_api.py` is in the diff, also emit (evidence: PR #105712):

```markdown
- [x] Endpoint has decorators.login_required if it needs authenticated user
- [x] Endpoint checks permissions for object ids being requested via api params
- [x] JSON registry has the right set of roles who can access this endpoint via allowed_roles
- [x] JSON registry has validation for the api parameters for object access
```
