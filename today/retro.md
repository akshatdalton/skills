# Sprint Retro — /today retro

Compute Done vs Planned SP for the closing sprint, draft Akshat's row, write the sprint section to the retro doc.

**Doc path:** `~/Downloads/TM India Sprint Retro Notes.md` — never ask user to re-share this.

## Pre-conditions

Run after user has reviewed Jira and reverted any automation-inflated SPs.
Load schema first: `ToolSearch select:mcp__claude_ai_Atlassian__searchJiraIssuesUsingJql`

## Steps

**1. Get sprint ID** — read `customfield_10020[].id` from any board task in `~/.claude/work_hq/board.json` where `state=active`. Never hardcode.

**2. Query Jira** — result is large, pipe through jq immediately:
```bash
jq '[.issues.nodes[] | {key:.key, status:.fields.status.name, sp:(.fields.customfield_10058 // 0), summary:.fields.summary}]' <result_file>
```
JQL: `assignee = "akshat.v@eightfold.ai" AND sprint = <id>`, fields `[summary, status, customfield_10058]`, maxResults 50.

**3. Flag any sp=5 tickets**
```
⚠️  ENG-XXXXX  "<summary>"  shows 5 SP — confirm not auto-inflated
```
Trust all other values as-is.

**4. Categorize**

| Bucket | Jira statuses |
|--------|---------------|
| Done | Closed, Dev complete |
| Not done (spillover) | Open, In Progress, In Review |
| Planned | all |

**5. Draft Akshat's row** — see Tone Examples below. 3–5 sentences max.

**6. Present and write**

```
SPRINT <N> — <name>
─────────────────────────────────────
Done:    <done_sp> sp  (<n> tickets)
Planned: <planned_sp> sp  (<n> tickets)

DONE
  ENG-XXXXXX  <summary, 55 chars>   <sp>sp
  ...

NOT DONE → S<N+1>
  ENG-XXXXXX  <summary>   <sp>sp
  ...

AKSHAT'S ROW:
| Akshat | <done_sp> | <planned_sp> | <notes> |
```

Ask: "Write Sprint <N> section to retro doc? [y/n]"

On yes — prepend to `~/Downloads/TM India Sprint Retro Notes.md`:

```markdown
## <Month> <day>, <year> | TM India retro

Attendees:

Status:
Throughput:
Predictability:
Quality:

|  | Done | Planned | Suggestions/Learnings/Notes |
| :---- | :---- | :---- | :---- |
| Yavnika |  |  |  |
| Samyak |  |  |  |
| Vasu |  |  |  |
| Amen |  |  |  |
| Rohit |  |  |  |
| Fenil |  |  |  |
| Shailendra |  |  |  |
| Ashutosh |  |  |  |
| Akshat | <done_sp> | <planned_sp> | <notes> |
| Michael |  |  |  |
| Aditya Singh |  |  |  |
| Saai |  |  |  |
| Padma |  |  |  |
| **TOTAL** |  |  |  |

##

##

```

Akshat's row pre-filled. All others blank — team fills live at 10:30 AM retro call.

---

## SP Integrity Rule

Jira automation ("Automation for Jira") bumps SP from original → 5 on status transitions ("Story Point Review = Completed by Agent"). User reverts manually in Jira before running retro. Strategy: query after reverts, trust current values, flag remaining `sp=5` as safeguard.

---

## Tone Examples (Akshat's past rows)

Terse, factual, 2–4 sentences. Pattern: constraints first (oncall/OOO) → open PRs → shipped work → learning → shoutout. Skip sections that don't apply.

**Sprint 88 (Apr 20, 2026)** — Done 13 / Planned 26
> 5 PRs in review, need a final review, should be merged by tomorrow. Learnings: Items to prioritize based on timeline and avoid last minute rush for demo. Will add more time for PR reviews. Shoutout: Samyak Jain for helping and navigating the project for Cultivate demo

**Sprint 87 (Apr 6, 2026)** — Done 12 / Planned 14
> Shadow on-call for 5 days (30:70) — 5 tickets in total. PRs in review

**Sprint 86 (Mar 23, 2026)** — Done 16 / Planned 19
> Was able to pick some momentum on connectors side. But need to start working on other components to bring the app in the demo-ready state. Need to migrate open PRs to the new repo

**Sprint 85 (Mar 9, 2026)** — Done 11 / Planned 11
> Shadow Oncall — 4 days. Need to speed up the journey of discussion to code. Could only work on 1 on-call ticket
