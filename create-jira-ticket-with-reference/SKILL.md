---
name: create-jira-ticket-with-reference
description: Create Jira tickets by inheriting metadata (priority, sprint, labels, pod) from a reference ticket. Use whenever the user provides a reference ticket ID or URL and asks to create a similar ticket — phrases like "create a ticket like ENG-12345", "same metadata as ENG-12345", "similar to ENG-12345", "copy metadata from", or "based on ENG-12345". Always use this skill when a Jira ticket ID appears alongside a creation request.
---

# Create Jira Ticket with Reference

Create new Jira tickets by inheriting metadata from an existing reference ticket, with user overrides where specified.

## Workflow

### Step 1 — Identify the reference ticket

Extract the ticket ID from user input:
- Plain ID: `ENG-12345`
- Full URL: `https://eightfoldai.atlassian.net/browse/ENG-12345`

### Step 2 — Fetch reference metadata

Use the Atlassian MCP `getJiraIssue` tool (cloudId: `eightfoldai.atlassian.net`) and request these fields:
- `priority`
- `customfield_10020` (Sprint)
- `customfield_10058` (Story Points — ENG project)
- `customfield_10219` (Pod — ENG project)
- `labels`
- `assignee`
- `parent`

### Step 3 — Prepare fields for the new ticket

**Default — copy from reference:**
| Field | Source |
|---|---|
| Priority | Reference ticket's `priority.id` |
| Sprint | Reference ticket's `customfield_10020[0].id` (number only) |
| Story Points | Reference ticket's `customfield_10058` |
| Pod | Reference ticket's `customfield_10219` option id (ENG project) |
| Labels | Reference ticket's labels array |
| Parent | Reference ticket's `parent.key` (skip if absent) |
| Assignee | Default to the current user's account ID |

**If the user specifies overrides**, apply them instead. If they say "assign to me", look up their account ID via `lookupJiraAccountId`.

If the user hasn't provided a summary/description yet, ask before proceeding.

### Step 4 — Lookup account IDs (if needed)

If the user specifies an assignee by name, use `lookupJiraAccountId` (cloudId: `eightfoldai.atlassian.net`, searchString: name) to get their account ID.

### Step 5 — Create the ticket

Use the Atlassian MCP `createJiraIssue` tool:

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

### Step 6 — Add related context (optional)

If useful, append to the description:

```
**Related Context:**
- ENG-12345: <brief description of reference ticket>
```

This is plain text in the description body — not a Jira issue link.

### Step 7 — Confirm and return

After the ticket is created, always reply with:

1. **Ticket URL** — `https://eightfoldai.atlassian.net/browse/ENG-XXXXX`
2. **Metadata confirmation** — show the five key fields that were set:

```
ENG-XXXXX created.

Priority:      P2
Sprint:        TM Aries Ind Sprint 88
Pod:           ARIES-TM-CORE
Story Points:  2
Parent:        ENG-177416
```

If any field was missing on the reference ticket and therefore skipped, call it out explicitly (e.g. "Parent: not set — skipped").

---

## Field format cheatsheet

| Field | Parameter | Format | Notes |
|---|---|---|---|
| Priority | `priority` | `{"id": "3"}` | P1=`"2"`, P2=`"3"`, P3=`"4"` |
| Sprint | `customfield_10020` | `13932` (bare number) | NOT an array — extract via `[0].id` |
| Story Points | `customfield_10058` | `2` (number) | ENG project — `customfield_10016`/`10028` are null here |
| Pod | `customfield_10219` | `{"id": "48832"}` | ENG project — option id from reference ticket's `customfield_10219.id` |
| Labels | `labels` | `["backend"]` | Empty array `[]` is valid |
| Parent | `parent` | `"ENG-177416"` (key string) | Top-level param, not in `additional_fields`; skip if absent on reference |
| Assignee | `assignee_account_id` | `"712020:abc..."` | Use `lookupJiraAccountId` to resolve names |

---

## Error handling

| Error | Cause | Fix |
|---|---|---|
| "Specify a valid value for assignee" | Wrong parameter name | Use `assignee_account_id`, not `assignee` |
| "Number value expected as Sprint id" | Sprint passed as array | Use `customfield_10020[0].id` as a bare number |
| "Invalid priority" | Wrong format | Must be `{"id": "string"}` |
| Reference ticket not found | Ticket doesn't exist / no access | Tell user, offer to create without metadata |
| Field missing on reference | Pod/labels not set | Skip that field silently, continue |
