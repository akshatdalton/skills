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
- `labels`
- `customfield_10011` (Pod)
- `assignee`

### Step 3 — Prepare fields for the new ticket

**Default — copy from reference:**
| Field | Source |
|---|---|
| Priority | Reference ticket's priority ID |
| Sprint | Reference ticket's `customfield_10020[0].id` (number only) |
| Labels | Reference ticket's labels array |
| Pod | Reference ticket's `customfield_10011` (skip if absent) |
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
assignee_account_id: <from step 4 or current user>
additional_fields:
  priority:             {"id": "<id from reference>"}
  customfield_10020:    <sprint id as number, e.g. 13932>
  labels:               ["label1", "label2"]
```

### Step 6 — Add related context (optional)

If useful, append to the description:

```
**Related Context:**
- ENG-12345: <brief description of reference ticket>
```

This is plain text in the description body — not a Jira issue link.

Return the new ticket URL to the user.

---

## Field format cheatsheet

| Field | Parameter | Format | Notes |
|---|---|---|---|
| Priority | `priority` | `{"id": "3"}` | P1=`"2"`, P2=`"3"`, P3=`"4"` |
| Sprint | `customfield_10020` | `13932` (number) | NOT `[13932]` — extract via `[0].id` |
| Labels | `labels` | `["backend"]` | Empty array `[]` is valid |
| Pod | `customfield_10011` | `"team-name"` | Skip if absent on reference |
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
