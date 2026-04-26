# Checklist Patterns Reference

## Backend / data-plane (DP)
```markdown
- [x] DP
- [x] Regression testing is not required because new data-plane module, no customer impact
- [x] It is a bug-fix/usability fix that is common for all group_ids and safe to rollout
- [x] This change is easy to read, review, debug and maintain
- [x] None return values are handled gracefully
- [x] Not applicable  ← Product Security
- [x] No additional tests are needed because _____
- [x] No user visible strings are introduced in this PR.
- [x] This PR does not contain any UI changes.
- [x] Not applicable - This change does not impact AI Recruiter functionality.
- [x] Not Applicable - This change is not related to DjSafe Schema.
- [x] Description not required
- [x] If scripts are used in DAGs, list tested regions: NA
- [x] If new dags in dags_config.json need to run in westus2, westus2 has been added as a region in the dag json.
- [x] I have gone through the updated checklist.
```

## Frontend / UI (TM/TA/TD)
```markdown
- [x] TM   ← or TA, TD — whichever applies
- [x] This change could affect the performance of:
  - [x] TM Marketplace   ← or relevant area
- [x] Regression testing is not required because _____
- [x] It is a bug-fix/usability fix that is common for all group_ids and safe to rollout
- [x] This change is easy to read, review, debug and maintain
- [x] Undefined/Null return values are handled in react/JS gracefully
- [x] Not applicable  ← Product Security
- [x] No additional tests are needed because _____
- [x] No user visible strings are introduced in this PR.
- [x] This PR does not contain any UI changes.   ← or keyboard/axe tested
- [x] Not applicable - This change does not impact AI Recruiter functionality.
- [x] Not Applicable - This change is not related to DjSafe Schema.
- [x] Description [customer-facing changelog]: _____
- [x] If scripts are used in DAGs, list tested regions: NA
- [x] If new dags in dags_config.json need to run in westus2, westus2 has been added as a region in the dag json.
- [x] I have gone through the updated checklist.
```
