---
name: create-jira-ticket-with-reference
description: Create Jira tickets by inheriting metadata (priority, sprint, labels, pod) from a reference ticket. Use whenever the user provides a reference ticket ID or URL and asks to create a similar ticket — phrases like "create a ticket like ENG-12345", "same metadata as ENG-12345", "similar to ENG-12345", "copy metadata from", or "based on ENG-12345". Always use this skill when a Jira ticket ID appears alongside a creation request.
---

> For all per-ticket state mutations, see [shared progress policy](/Users/akshat.v/.claude/skills/_shared/progress-policy.md).

# Create Jira Ticket with Reference

Inherit metadata from reference ticket, apply user overrides.

## Pre-entry: vault context check (v0.2)

On entry, check whether the reference ticket has a vault progress directory and surface its initiative context:

```bash
# Probe vault first (single source of truth)
for repo in vscode wipdp; do
  for d in progress progress/archive; do
    p=~/opensource/vault/wiki/projects/$repo/$d/<REF_TICKET_ID>
    [ -d "$p" ] && awk '/^---$/{c++; if(c==2)exit; next} c==1{print}' "$p/progress.md" && break 2
  done
done
```

Surface one-line: `↳ loaded vault context: project=<repo> initiative=<slug>` or `↳ no vault context yet`.

> **Note:** The new ticket's relationship to its initiative is captured in the vault progress.md frontmatter `initiative:` field set in Step 7. Initiative-level decisions/learnings live in `vault/wiki/projects/<repo>/learnings.md` under `## Initiative: <slug>` sections.

Never ask "shall I save?" — save and notify. User corrects next message if wrong.

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

**Description formatting (mandatory):** Always pass `contentFormat: "markdown"`. Build the description with actual newline characters — NOT escaped `\n` sequences. Write the description to a temp file first, then read it back to guarantee proper encoding:

```bash
cat > /tmp/jira_desc.md << 'EOF'
<description body with real newlines>

**Related Context:** <parent/reference ticket context>
EOF
```

Then paste the content (read from the file) as the `description` parameter. This is the same discipline as `/submit-pr`'s `--body "$(cat file)"` — it prevents `\n` from rendering as literal backslash-n in the Jira UI.

```
cloudId:          eightfoldai.atlassian.net
projectKey:       ENG  (or user-specified)
issueTypeName:    Story  (or user-specified)
summary:          <user-provided>
description:      <content of /tmp/jira_desc.md — actual newlines>
contentFormat:    markdown
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

### Step 7 — Vault progress seed (PRIMARY — single source of truth for ticket state)

After ticket creation, immediately seed the vault progress directory. **The vault progress.md is the single source of truth for per-ticket state.**

```bash
mkdir -p ~/opensource/vault/wiki/projects/<repo>/progress/<NEW_TICKET_ID>/
```

Determine `<repo>` (`vscode` or `wipdp`):
- From the reference ticket's `repo` field if known
- From the user's cwd (`git remote get-url origin`)
- From the description / parent epic context

Create `~/opensource/vault/wiki/projects/<repo>/progress/<NEW_TICKET_ID>/progress.md`:

```markdown
---
ticket: <NEW_TICKET_ID>
title: "<summary>"
project: <repo>
branch: null
pr: null
pr_state: null
state: new
priority: <P0|P1|P2 inherited from reference>
created: <today YYYY-MM-DD>
last-touched: <today YYYY-MM-DD>
session_ids: []
---

# <NEW_TICKET_ID> — <summary>

## Jira summary

<description from create response, OR what the user gave you when asked for summary>

## Status

Created from reference ENG-XXXXX. Not yet started. No branch, no PR.

## What's next (when work begins)

Fire `/brain-recall <NEW_TICKET_ID>` then `/work-on-jira-task <NEW_TICKET_ID>` to scope and implement.

## Key references

- Jira: https://eightfoldai.atlassian.net/browse/<NEW_TICKET_ID>
- Reference ticket: https://eightfoldai.atlassian.net/browse/<REF_TICKET_ID>
- Plan: (none yet — will be written here when /work-on-jira-task or /think generates one)
```

Surface inline (not as a question):
```
↳ vault progress seeded: projects/<repo>/progress/<NEW_TICKET_ID>/
```

## After creation

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
| Literal `\n\n` visible in Jira description UI | Escaped newlines in payload | Use temp file + `contentFormat: "markdown"` (Step 4) |

---

## Workflow ending

The vault progress.md (Step 7) IS the source of truth for the new ticket. No board.json refresh is required — `/today` and all state-machine skills read progress.md directly via `progress_fm.py`.

Surface the final summary:

```
───── workflow ─────
✓ Ticket   : <NEW_TICKET_ID> created
✓ Reference: <REF_TICKET_ID> (priority, sprint, labels inherited)
✓ Vault    : projects/<repo>/progress/<NEW_TICKET_ID>/progress.md (source of truth)
→ Next     : /brain-recall <NEW_TICKET_ID> then /work-on-jira-task  OR  /ship-task <NEW_TICKET_ID>
────────────────────

───── artifacts ─────
Jira       : https://eightfoldai.atlassian.net/browse/<NEW_TICKET_ID>
Reference  : https://eightfoldai.atlassian.net/browse/<REF_TICKET_ID>
Progress   : ~/opensource/vault/wiki/projects/<repo>/progress/<NEW_TICKET_ID>/progress.md
─────────────────────
```

> Vault progress.md frontmatter carries `needs_input`, `bucket`, and all per-ticket state directly. No derived board.json to regenerate.
