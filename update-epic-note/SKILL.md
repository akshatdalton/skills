---
name: update-epic-note
description: Use when user invokes /update-epic-note, says "add this to the epic note", "update the epic note with X", "log this on ENG-177416", or wants a dated executive entry added to the Notes field on the WIP RAG-for-TM epic (ENG-177416). Default target ENG-177416; supports `--epic <KEY>` for other epics. For Akshat's manager-facing epic status log.
---

# update-epic-note

Add a date-prefixed executive entry to the **Notes** field (`customfield_10403`, under Basic Info) of a Jira Epic. Default target: **ENG-177416** (Workforce Intelligence Platform — RAG for Talent Management).

## The contract

The user gives a polished 1–2 line executive entry. **This skill does not rewrite their wording.** It owns:

1. Today's date prefix (`YYYY-MM-DD —`)
2. ADF formatting (the field rejects markdown/wiki/plain text)
3. Preserving history (prepend, don't replace, unless told)
4. Calling `editJiraIssue` correctly
5. Verifying the write

The user owns the wording. If their text looks like a tech changelog, the skill nudges once and asks before posting — see "Style validation" below.

## Argument parsing

```
/update-epic-note <text>                  # default target ENG-177416, prepend mode
/update-epic-note --epic ENG-XXXXX <text> # different epic
/update-epic-note --replace <text>        # wipe existing, write only today's entry
/update-epic-note --remove <date>         # delete the entry for that date
```

If no `<text>` is provided and the user's message has no obvious content, ask once for the entry text. Don't invent content.

## Steps

1. **Resolve date:** `date +%Y-%m-%d` (user's local timezone).
2. **Resolve epic key:** parse `--epic <KEY>` if present, else `ENG-177416`.
3. **Style validation** on the input text (see section below). If a flag fires, surface a one-line warning and ask the user to confirm or revise BEFORE step 4.
4. **Read current Notes:**
   ```
   mcp__...__getJiraIssue
     cloudId=eightfoldai.atlassian.net
     issueIdOrKey=<EPIC>
     fields=["customfield_10403"]
   ```
   If `customfield_10403` is `null` or missing, treat the existing content array as `[]`.
5. **Build the new ADF paragraph:**
   ```json
   {
     "type": "paragraph",
     "content": [{"type": "text", "text": "<YYYY-MM-DD> — <user text>"}]
   }
   ```
   For multi-line entries (user passed text containing `\n`), use `hardBreak` between lines — date prefix appears only on the FIRST line:
   ```json
   {
     "type": "paragraph",
     "content": [
       {"type": "text", "text": "<YYYY-MM-DD> — <line 1>"},
       {"type": "hardBreak"},
       {"type": "text", "text": "<line 2>"}
     ]
   }
   ```
6. **Compose the updated doc:**
   - `prepend` (default): `content = [<new paragraph>, ...existing.content]`
   - `--replace`: `content = [<new paragraph>]`
   - `--remove <date>`: `content = existing.content.filter(p => !p.content[0].text.startsWith(<date>))`
7. **Write back:**
   ```
   mcp__...__editJiraIssue
     cloudId=eightfoldai.atlassian.net
     issueIdOrKey=<EPIC>
     fields={"customfield_10403": {"type":"doc","version":1,"content":[...]}}
   ```
   Do NOT pass `contentFormat: "markdown"` for this field — it's strict ADF, not a markdown-convertible body.
8. **Verify** by re-fetching `customfield_10403` and printing the first paragraph's text. If it doesn't match what was sent, surface the discrepancy.

## Style validation

The Notes field is read by the user's manager. The entries must be **executive summary**, not tech changelog. See memory `feedback_executive_summary_pattern` for the rationale.

Before posting, scan the user's text. If ANY of these fire, surface a one-line warning and ask:

| Signal | What to say |
|---|---|
| Mentions tool names (Pulumi, S3, boto3, structlog, CloudWatch, ADF, MCP, K8s, etc.) | "Looks like a tech changelog — mentions `<tool>`. Manager-facing entries usually skip tool names. Post as-is or revise?" |
| Mentions file paths / extensions (`.yml`, `.py`, `Makefile`, etc.) | Same nudge. |
| Lists 3+ ENG-XXXXX ticket IDs | "Multiple ticket IDs make this read like an internal log. One or two is fine as context. Trim or proceed?" |
| Lacks a forward-looking clause (no "need to…", "should…", "next…", future-tense reference) | "No implication / next-step clause — the example pattern is `<outcome>, <what's next>`. Add one or post as-is?" |
| Longer than 2 lines of prose | "This is >2 lines. Manager-facing entries are 1–2 lines. Trim or proceed?" |

If the user says "proceed" / "as-is" — post verbatim. Do not silently rewrite their words.

## Output format

```
✓ ENG-177416 Notes updated.
  Mode:    prepend  (or: replace / remove)
  Added:   2026-MM-DD — <text>
  Entries: N total
  Verified: yes
```

## Field reference

| Surface | Value |
|---|---|
| Custom field ID | `customfield_10403` |
| Field name in Jira UI | "Notes" (under Basic Info / Details section) |
| Format required | ADF (Atlassian Document Format) — NOT markdown, NOT wiki markup |
| Default epic | ENG-177416 — Workforce Intelligence Platform — RAG for Talent Management |
| Cloud ID | `eightfoldai.atlassian.net` |
| Required auth | Atlassian MCP (already configured) |

## Common mistakes

| Mistake | Fix |
|---|---|
| Sending markdown/plain string → `"Operation value must be an Atlassian Document"` | Wrap in `{"type":"doc","version":1,"content":[...]}` ADF structure. |
| Replacing the whole field accidentally | Always read existing content first; prepend new paragraph to its `content` array. |
| Date prefix on continuation lines | Date only on FIRST line of an entry; use `hardBreak` for line 2. |
| Multiple separate paragraphs for one entry | An "entry" = ONE paragraph. Multi-line entries use `hardBreak` inside one paragraph. |
| Writing a tech changelog | Run the style validation. See `feedback_executive_summary_pattern`. |
| Calling `editJiraIssue` with `contentFormat: "markdown"` on this field | The Notes field is strict ADF — don't pass `contentFormat`. |

## Don't

- Don't auto-rewrite the user's wording. Nudge once if it reads like a changelog, then respect their choice.
- Don't append at the bottom (oldest-first ordering). Prepend so the latest entry is at top.
- Don't fabricate an entry from session context. Ask the user for the text.
- Don't update other fields on the epic (description, labels, status) — this skill ONLY touches `customfield_10403`.

## Related

- Memory: `feedback_executive_summary_pattern` — the style guide enforced by this skill.
- Memory: `feedback_convert_jira_issuetype_in_place` — different operation, but same `editJiraIssue` API.
- Skill: `create-jira-ticket-with-reference` — for creating new tickets, not updating epic notes.
