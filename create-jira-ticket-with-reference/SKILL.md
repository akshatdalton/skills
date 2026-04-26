---
name: create-jira-ticket-with-reference
description: Create Jira tickets by inheriting metadata (priority, sprint, labels, pod) from a reference ticket. Use whenever the user provides a reference ticket ID or URL and asks to create a similar ticket — phrases like "create a ticket like ENG-12345", "same metadata as ENG-12345", "similar to ENG-12345", "copy metadata from", or "based on ENG-12345". Always use this skill when a Jira ticket ID appears alongside a creation request.
---

# Create Jira Ticket with Reference

Inherit metadata from reference ticket, apply user overrides.

## Workflow

### Step 1 — Identify reference
Extract from: plain ID (`ENG-12345`) or URL.

### Step 2 — Fetch reference metadata
Atlassian MCP `getJiraIssue` (cloudId: `eightfoldai.atlassian.net`), request: `priority`, `customfield_10020` (Sprint), `customfield_10058` (Story Points), `customfield_10219` (Pod), `labels`, `assignee`, `parent`.

### Step 3 — Prepare fields

| Field | Source |
|---|---|
| Priority | `priority.id` |
| Sprint | `customfield_10020[0].id` (number) |
| Story Points | `customfield_10058` |
| Pod | `customfield_10219` option id |
| Labels | labels array |
| Parent | `parent.key` (skip if absent) |
| Assignee | Default current user |

User overrides take precedence. "Assign to me" → `lookupJiraAccountId`. No summary yet → ask.

### Step 4 — Create ticket

```
cloudId:          eightfoldai.atlassian.net
projectKey:       ENG  (or user-specified)
issueTypeName:    Story  (or user-specified)
summary:          <user-provided>
description:      <user-provided> + optional Related Context
parent:           <parent.key> (omit if absent)
assignee_account_id: <resolved>
additional_fields:
  priority:             {"id": "<id>"}
  customfield_10020:    <sprint id bare number>
  customfield_10058:    <story points number>
  customfield_10219:    {"id": "<pod option id>"}
  labels:               ["label1", "label2"]
```

### Step 5 — Related context (optional)
Append if useful: `**Related Context:** - ENG-12345: <brief>`. Plain text, not Jira link.

### Step 6 — Confirm and return

Reply with URL + all fields:
```
ENG-XXXXX created.
Priority:      P2
Sprint:        TM Aries Ind Sprint 88 (started 2026-04-14)
Pod:           ARIES-TM-CORE
Story Points:  2
Parent:        ENG-177416
Labels:        [backend]
```
Missing fields: `not set on reference — skipped`.

---

## After creation
Offer: *"Start `/work-on-jira-task` on ENG-XXXXX?"*

---

## Field format cheatsheet

| Field | Parameter | Format | Notes |
|---|---|---|---|
| Priority | `priority` | `{"id": "3"}` | P1=`"2"`, P2=`"3"`, P3=`"4"` |
| Sprint | `customfield_10020` | `13932` (bare number) | NOT array — `[0].id` |
| Story Points | `customfield_10058` | `2` (number) | `10016`/`10028` null in ENG |
| Pod | `customfield_10219` | `{"id": "48832"}` | option id from reference |
| Labels | `labels` | `["backend"]` | Empty `[]` valid |
| Parent | `parent` | `"ENG-177416"` (key) | Top-level param; skip if absent |
| Assignee | `assignee_account_id` | `"712020:abc..."` | `lookupJiraAccountId` to resolve |

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
2. Fallback: active sprint via JQL: `sprint in openSprints() AND project = ENG`
3. Log sprint start date in confirmation

---

## Error handling

| Error | Cause | Fix |
|---|---|---|
| "Specify a valid value for assignee" | Wrong param | Use `assignee_account_id` |
| "Number value expected as Sprint id" | Sprint as array | Bare number from `[0].id` |
| "Invalid priority" | Wrong format | Must be `{"id": "string"}` |
| Reference not found | Missing/no access | Offer create without metadata |
| Field missing on reference | Not set | Skip silently |

---

## Workflow ending

Before completing, run `/project-context:update` with ticket ID, summary, and any context gathered.

```
───── workflow ─────
✓ Ticket: ENG-XXXXX created
→ Next: /work-on-jira-task ENG-XXXXX
────────────────────
```
