---
name: project-context
description: Two-layer context storage — per-branch (ticket details, files, decisions) and per-project (umbrella across branches/repos for an epic). Use /project-context:branch:read|update for branch context, /project-context:project:read|update for project context. Auto-loaded on entry by /work-on-jira-task, /get-pr-ready-to-merge, /create-jira-ticket-with-reference, /run-on-ec2, /debug-api. Backward-compat: bare /project-context:read|update defaults to branch.
---

# Project Context

Two layers:

1. **Branch layer** — per-branch context (one PR's worth). Existing behavior.
2. **Project layer** — umbrella across many branches/PRs/repos for one epic or initiative.

Branch files link up to a project via a `**Project**: <slug>` field. `:branch:read` auto-loads the parent project file.

## Sub-commands

| Invocation | Action |
|---|---|
| `/project-context:branch:read` | Surface branch context for current branch + auto-load parent project. |
| `/project-context:branch:update <info>` | Create/update branch context for current branch. |
| `/project-context:project:read [<slug>]` | Surface project context. Slug optional (auto-derived from branch). |
| `/project-context:project:update <slug> <info>` | Create/update project context. |
| `/project-context:read` | Backward-compat → `:branch:read`. |
| `/project-context:update <info>` | Backward-compat → `:branch:update`. |

## File layout

```
~/.claude/projects/<project-dir-slug>/memory/
├── branches/
│   └── <branch-slug>.md                # one per branch
└── projects/
    ├── <project-slug>.md               # INDEX file (overview + lookups)
    └── <project-slug>/
        ├── charter.md                  # detail
        ├── ticket-graph.md             # detail
        └── decisions.md                # detail
```

Per the overview-with-lookups rule (always loaded via MEMORY.md): the project INDEX file stays small with one-line entries pointing to detail children. Detail children only loaded when their lookup pointer signals relevance.

## Branch detection

```bash
git rev-parse --abbrev-ref HEAD
```

Branch slug: strip `<user>/` prefix, replace `/` with `-`, append `.md`.

Project dir slug: derive from current `pwd` — replace `/` with `-`, prefix `-`. Example: `/Users/akshat.v/eightfold/wipdp` → `-Users-akshat-v-eightfold-wipdp`.

## Project slug derivation

When user invokes `:project:*` without an explicit slug, OR when `:branch:read` needs the parent project to auto-load, derive in this order:

1. **Read branch file** — if it has `**Project**: <slug>`, use it.
2. **Jira parent epic** — extract ENG-XXXXX from branch name. Atlassian MCP `getJiraIssue` → check `parent` / `customfield_10014` (epic link). Slug = lowercase epic key (e.g. `eng-185000`) OR slugified epic summary (lowercase, dashes, no special chars), pick whichever the user prefers; default to slugified summary if available.
3. **Ask user** — propose top 1-2 candidates, accept user override.

Once derived, write back to the branch file's `**Project**: <slug>` field so step 1 hits next time.

---

## /project-context:branch:read

Execute these steps in order. Every step is mandatory; do not skip.

1. Detect branch + resolve `branches/<branch-slug>.md`.
2. If file missing → notify "↳ no branch context yet for `<branch>` (will seed on first material finding)" and SKIP to step 7.
3. Read the index file.
4. **MUST: parse the `**Project**: <slug>` field on line 3 of the branch file.**
   - **If field present + non-empty** → MUST immediately invoke `Skill(skill="project-context", args="project:read <slug>")` to load the parent project. Do not stop after step 3.
   - **If field absent or empty** → derive slug (see [Project slug derivation](#project-slug-derivation)). Write the field back into the branch file (no user prompt — passive). Then invoke `Skill(skill="project-context", args="project:read <slug>")`.
5. **Load latest checkpoint** (if any):
   - Find the `## Checkpoints` section in the index. Take the TOP entry (newest-first ordering).
   - If section missing or malformed → fallback: list `branches/<branch-slug>/checkpoints/*.md`, sort lexicographically descending (filenames are ISO timestamps — lex sort = chronological), take first.
   - If a latest checkpoint exists → READ that file fully into context. Surface a one-line resume header: `↳ resuming from checkpoint <ts>: Phase=<...>, Next=<...> (waiting: <...>)`.
   - Do NOT load older checkpoints. They're for explicit lookup only.
6. Surface a one-line load notification: `↳ loaded branch context: <branch-slug> + project: <slug>` (the resume header from step 5 already covers the checkpoint piece).
7. Done. Do NOT ask the user anything; do NOT echo full file contents in the chat unless the user explicitly asks.

## /project-context:branch:update

1. Detect branch + resolve path.
2. If file missing → seed from [Branch template](#branch-template).
3. Parse `<info>` argument; merge into existing sections (preserve all old content).
4. Write file.
5. **Bubble-up check**: if `<info>` contains scope-change keywords (`now also need`, `pivot`, `instead of`, new ENG-XXXXX, new repo path) → propose: "This looks like a project-level change. Update project `<slug>`'s decisions or ticket-graph?"
6. Confirm: "Updated branch context for `<branch>`."

## /project-context:project:read

1. Resolve slug (explicit arg → derive → ask).
2. Read `projects/<slug>.md` (INDEX). If missing → "No project context for `<slug>`. Use `/project-context:project:update` to seed."
3. Surface index.
4. If user message references a topic in the index (e.g., "what was the ticket graph?") → load the matching detail child file.

## /project-context:project:update

1. Resolve slug.
2. If INDEX missing → seed from [Project template](#project-template).
3. Parse `<info>` argument; route to appropriate detail file (`charter.md` for charter/why, `ticket-graph.md` for tickets/branches/dependencies, `decisions.md` for design/pivots). Update INDEX with one-line lookup if a new detail file is created.
4. Write atomically — never lose existing content.
5. If invoked passively by another skill (background mode) → also notify user: "Recorded at project layer: <one-line summary>".

---

## Branch template

```markdown
# Branch: <branch-name>

**Project**: <project-slug>  ← linked to projects/<slug>.md

## Ticket
- **ENG**: https://eightfoldai.atlassian.net/browse/ENG-XXXXX
- **IMPL**: https://eightfoldai.atlassian.net/browse/IMPL-XXXXXX  ← omit if N/A
- **Summary**: <one-line>

## Relevant Files / Components
<!-- file:line format where known -->

## Key Findings
<!-- root causes, patterns, constraints -->

## Decisions
<!-- approach decisions and why -->

## Test Environment
<!-- sandbox URL, login, navigation steps -->

## Open Questions / Notes
```

Omit empty sections.

## Project template

INDEX file (`projects/<slug>.md`):

```markdown
# Project: <slug>

<one-paragraph overview>

## Charter → [charter.md](<slug>/charter.md)
- one-line: why this project exists, success criteria

## Ticket Graph → [ticket-graph.md](<slug>/ticket-graph.md)
- one-line: count and current state (X open, Y in progress, Z done)

## Decisions → [decisions.md](<slug>/decisions.md)
- one-line: latest decision summary

## Branches in flight
- <repo>: <branch> → PR #<n> (<state>)
```

Detail children:

- `charter.md` — full why, success criteria, stakeholders, deadline.
- `ticket-graph.md` — every ENG ticket, parent/child relations, current state, blockers.
- `decisions.md` — chronological log of design decisions and pivots, with reason.

---

## Passive operation contract (MANDATORY — baked into this skill, not memory)

Reads and updates are passive. No "shall I save this?" framing. No asking before saving. No echoing full file contents. Acknowledgement = one-line `↳` notification only.

### Auto-read trigger

Other skills MUST invoke `Skill(skill="project-context", args="branch:read")` as their first action on entry. The /project-context:branch:read flow above will transitively load the parent project. Skills with this contract baked in: `/work-on-jira-task`, `/get-pr-ready-to-merge`, `/create-jira-ticket-with-reference`, `/run-on-ec2`, `/debug-api`, `/submit-pr`. Each skill's own SKILL.md repeats this contract — don't rely on memory or shared docs.

### Auto-update trigger

During any work, the MOMENT you learn something material, you MUST call `Skill(skill="project-context", args="branch:update <one-line description>")` BEFORE moving to your next action. Then surface:

```
↳ saved to branch context: <one-line summary>
```

A finding is "material" if you'd want it recalled when compaction hits in the next minute. Examples that always count:
- Root cause located at file:line
- Design decision made (chose A over B because C)
- Key file discovered ("user fixtures live at tests/fixtures/users.py")
- Test env detail (sandbox URL, login, navigation steps)
- Constraint understood (rate limit, auth requirement, schema invariant)
- Unblocking insight (workaround for a bug, missing dep installed)

Bubble up to project layer when the finding crosses branches: scope changed, new ticket spawned, cross-branch dependency, decision affecting the whole initiative. Call `Skill(skill="project-context", args="project:update <slug> <info>")` and surface:

```
↳ saved to project context: <one-line summary>
```

### Anti-patterns (forbidden)

- "Should I save this to context?" — NO. Save it. Surface the one-liner.
- "Want me to record this?" — NO. Record it.
- "I'll update context at the end of the task." — NO. Update it now, every time, throughout.
- Echoing full branch file contents in chat after a read — NO. The agent has it loaded; the user doesn't need to re-read it.

The user's safety mechanism is correcting in the next message if a save was wrong. That's a far cheaper interaction than asking permission for every save.

## Notes

- This skill only reads/writes local files. It calls Atlassian MCP only when deriving a project slug from a Jira epic.
- All knowledge files follow the overview-with-lookups rule (memory feedback file).
