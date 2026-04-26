---
name: create-jira-ticket-with-reference
description: Create Jira tickets by inheriting metadata (priority, sprint, labels, pod) from a reference ticket. Use whenever the user provides a reference ticket ID or URL and asks to create a similar ticket — phrases like "create a ticket like ENG-12345", "same metadata as ENG-12345", "similar to ENG-12345", "copy metadata from", or "based on ENG-12345". Always use this skill when a Jira ticket ID appears alongside a creation request.
---

# Create Jira Ticket with Reference

Create tickets inheriting metadata from existing reference, with user overrides.

## Workflow

### Step 1 — Identify reference ticket
Extract ticket ID from: plain ID (`ENG-12345`) or URL (`https://eightfoldai.atlassian.net/browse/ENG-12345`).

### Step 2 — Fetch reference metadata
Use Atlassian MCP `getJiraIssue` (cloudId: `eightfoldai.atlassian.net`), request: `priority`, `customfield_10020` (Sprint), `customfield_10058` (Story Points), `customfield_10219` (Pod), `labels`, `assignee`, `parent`.

### Step 3 — Prepare fields

| Field | Source |
|---|---|
| Priority | `priority.id` |
| Sprint | `customfield_10020[0].id` (number only) |
| Story Points | `customfield_10058` |
| Pod | `customfield_10219` option id |
| Labels | labels array |
| Parent | `parent.key` (skip if absent) |
| Assignee | Default to current user's account ID |

User overrides take precedence. "Assign to me" → look up via `lookupJiraAccountId`. If no summary/description yet, ask.

### Step 4 — Lookup account IDs (if needed)
Use `lookupJiraAccountId` (cloudId: `eightfoldai.atlassian.net`, searchString: name).

### Step 5 — Create ticket

```
cloudId:          eightfoldai.atlassian.net
projectKey:       ENG  (or user-specified)
issueTypeName:    Story  (or user-specified)
summary:          <user-provided>
description:      <user-provided> + optional Related Context block (see below)
parent:           <parent.key from reference, e.g. "ENG-177416"> (omit if absent)
assignee_account_id: <from step 4 or current user>
additional_fields:
  priority:             {"id": "<id from reference>"}
  customfield_10020:    <sprint id as bare number, e.g. 13932>
  customfield_10058:    <story points as number, e.g. 2>
  customfield_10219:    {"id": "<pod option id from reference>"}
  labels:               ["label1", "label2"]
```

### Step 6 — Related context (optional)
Append to description if useful:
```
**Related Context:**
- ENG-12345: <brief description of reference ticket>
```
Plain text — not a Jira issue link.

### Step 7 — Confirm and return

Reply with ticket URL + **ALL** fields:
```
ENG-XXXXX created.

Priority:      P2
Sprint:        TM Aries Ind Sprint 88 (started 2026-04-14)
Pod:           ARIES-TM-CORE
Story Points:  2
Parent:        ENG-177416
Labels:        [backend]
```
For missing fields: `not set on reference — skipped`.

---

## After creation
Offer: *"Start `/work-on-jira-task` on ENG-XXXXX?"*

---

## Field format cheatsheet

| Field | Parameter | Format | Notes |
|---|---|---|---|
| Priority | `priority` | `{"id": "3"}` | P1=`"2"`, P2=`"3"`, P3=`"4"` |
| Sprint | `customfield_10020` | `13932` (bare number) | NOT array — extract via `[0].id` |
| Story Points | `customfield_10058` | `2` (number) | `customfield_10016`/`10028` are null in ENG |
| Pod | `customfield_10219` | `{"id": "48832"}` | option id from reference's `customfield_10219.id` |
| Labels | `labels` | `["backend"]` | Empty `[]` valid |
| Parent | `parent` | `"ENG-177416"` (key string) | Top-level param, not in `additional_fields`; skip if absent |
| Assignee | `assignee_account_id` | `"712020:abc..."` | Use `lookupJiraAccountId` to resolve |

## Story Points Scale

| Points | Time |
|---|---|
| 1 | Half day |
| 2 | One day |
| 3 | Two days |
| 5 | Three days |
| 8 | Five days |

**Sprint resolution (never hardcode):**
1. Primary: reference ticket's sprint
2. Fallback: fetch active sprint via JQL: `sprint in openSprints() AND project = ENG`
3. Log sprint start date in confirmation for future calculations

---

## Error handling

| Error | Cause | Fix |
|---|---|---|
| "Specify a valid value for assignee" | Wrong param name | Use `assignee_account_id`, not `assignee` |
| "Number value expected as Sprint id" | Sprint as array | Use `customfield_10020[0].id` as bare number |
| "Invalid priority" | Wrong format | Must be `{"id": "string"}` |
| Reference not found | Doesn't exist / no access | Tell user, offer to create without metadata |
| Field missing on reference | Pod/labels not set | Skip silently, continue |
