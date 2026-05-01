---
name: brainstorm-and-save
description: Open-ended exploration / ideation entry point — when there's no ticket or PR in hand and the user wants to think through a problem, research an area, or weigh approaches before deciding to act. Loads relevant project context, runs a constrained brainstorming dialogue, captures every decision passively to project-context, then presents a decision menu (create tickets / work on existing ticket / defer). Use this INSTEAD OF superpowers:brainstorming for the dev workflow — wrapper owns capture and controls deviation. Trigger on phrases like "I want to think about", "let's brainstorm", "let's explore", "should we", "before we build", "no ticket yet but", "I have an idea", "research X", "weigh A vs B", "what's the right approach for".
---

# Brainstorm and Save

Exploration entry point for the dev workflow. Owned capture, no file/TODO sprawl from sub-skills.

## Pre-entry: resolve project (mandatory)

Determine the project slug to anchor the brainstorm. Try in this order — stop at the first hit:

1. **Current branch's existing context** — invoke `Skill(skill="project-context", args="branch:read")`. If it returns a project slug via the `**Project**:` field, use it.
2. **Current branch → ticket → epic** — `git rev-parse --abbrev-ref HEAD`. If branch matches `*ENG-XXXXX*`, fetch the ticket via Atlassian MCP `getJiraIssue`, read its `parent` / epic link, derive slug from epic key or summary.
3. **Open PR on current branch → linked ticket** — `gh pr view --json body,headRefName 2>/dev/null`. Parse PR body for ENG-XXXXX or Jira links. If found, follow step 2 from there.
4. **Keyword match against existing projects** — list `~/.claude/projects/<project-dir>/memory/projects/*.md`. Match user's request keywords against project file names + first-line overviews. Surface top match for confirmation.
5. **Propose new project** — derive slug from user's request topic (lowercase, dashes, max 4 words). Confirm with user before creating.

Surface the resolution in one line:

```
↳ project: <slug> (resolved via <step name>)
```

If step 5 fires, ask once: "Creating new project context `<slug>`? (y/n)" — only this one question is allowed in pre-entry.

Then invoke `Skill(skill="project-context", args="project:read <slug>")` to load existing decisions, charter, ticket-graph as input to the brainstorm.

## Body: constrained brainstorming dialogue

Drive the brainstorm yourself — do NOT invoke `superpowers:brainstorming`. Reason: that skill creates its own files, TODOs, and plan artifacts that fragment our context layering. The wrapper owns all capture; everything goes to project-context and nowhere else.

### Dialogue pattern

Use this loop:

1. **Reflect the question** — restate what the user is exploring in one sentence so they can correct framing early.
2. **Surface what's already known** — pull from loaded project context: prior decisions, in-flight branches, charter, constraints. Cite specifically (`per decisions.md: "..."`).
3. **Open the option space** — propose 2-4 candidate approaches, each with tradeoffs. Don't recommend yet — let the user weigh in.
4. **Narrow** — ask the user 1-2 sharp questions to discriminate between options (constraints, deadline, who's affected, reversibility).
5. **Recommend** — based on user's answers, pick one with the main tradeoff explicitly named.
6. **Capture** — see passive capture below.

Iterate steps 3-5 as the user pulls on threads. Don't railroad to a conclusion in one turn.

### Passive capture (during brainstorm)

The moment a discrete decision, constraint, or insight crystallizes during the dialogue, MUST invoke `Skill(skill="project-context", args="project:update <slug> <one-line>")` immediately and surface:

```
↳ saved to project context: <one-line summary>
```

Examples worth saving:
- "Approach A chosen over B because B requires schema migration we can't ship this quarter."
- "Constraint: must work for tenants without admin role."
- "Deferred: caching layer — revisit after baseline perf measured."
- "Out of scope for this initiative: cross-region replication."

NEVER ask "should I save this?". Save and notify.

### Forbidden behavior

- Do not write to `thoughts/`, `plans/`, `brainstorms/`, or any new file outside `memory/projects/<slug>/`.
- Do not create TODO lists or task trackers.
- Do not create plan files. If user asks for a plan, that's a separate skill (`superpowers:writing-plans` or our own — explicit user request only).
- Do not invoke `superpowers:brainstorming` — its file-creation behavior pollutes our layering.

## Post-exit: decision menu

When the user signals the brainstorm is converging ("ok let's do this", "I think we've got it", "let's move forward"), present:

```
Brainstorm complete. Project context updated. Pick next action:

1. Create tickets   → /create-jira-ticket-with-reference (one or more for the chosen approach)
2. Work on existing → /work-on-jira-task <ticket-id>     (if there's already a ticket that fits)
3. Defer            → already saved to project context; come back any time
```

Do not auto-pick. Let the user choose.

## When NOT to use

- User shares a ticket URL → use `/work-on-jira-task` directly, brainstorming happens inside that skill's plan step.
- User shares a PR URL → use `/explain-anything` or `/get-pr-ready-to-merge`.
- User asks for a tech doc → use `/create-tech-doc`.
- User has a concrete bug to fix → use `superpowers:systematic-debugging`.

## Notes

- This skill is the entry point for the "no anchor yet" case. Once an anchor (ticket / PR / branch) exists, normal chain takes over.
- Project context update happens throughout, not just at the end — compaction-safe.
- The wrapper exists specifically to prevent superpowers:brainstorming from creating side artifacts. If you ever feel tempted to invoke that skill from inside this one, don't.
