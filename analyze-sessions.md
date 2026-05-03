---
name: analyze-sessions
description: Analyze recent Claude Code session .md files from the Obsidian vault and produce/update wiki knowledge pages
---

# Session Analysis Skill

Analyze Claude Code conversation sessions and extract durable knowledge into the wiki.

## Source

Sessions are pre-exported as `.md` files at:
`~/opensource/vault/claude-code/sessions/`

Filter by project (eightfold by default) and recency. Default: last 50 sessions from eightfold repos.

## Steps

<steps>

<step name="1-gather">
List files in `~/opensource/vault/claude-code/sessions/` sorted by date descending.
Filter to sessions matching the target project (default: `vscode` or `wipdp` in filename).
Read the most recent N (default 50, override with arg).
</step>

<step name="2-extract">
For each session, identify:

<extract>
  <failure-modes>
    Moments where the user corrected Claude: "no", "that's wrong", "you forgot", "you were supposed to", "don't do X", "I told you to". 
    Extract: what Claude did wrong, what the correction was.
  </failure-modes>

  <project-knowledge>
    Technical facts learned: commands, file paths, API patterns, env setup, gotchas, test approaches.
    Only keep facts specific to the codebase — not general programming knowledge.
  </project-knowledge>

  <workflow-patterns>
    How the user orchestrates skills, agents, PRs. What sequence they follow. What they delegate vs. supervise.
  </workflow-patterns>

  <claude-code-meta>
    Skills invoked, improvements requested, new skills created, friction with tooling.
  </claude-code-meta>
</extract>
</step>

<step name="3-synthesize">
Group extracted signals by category. Deduplicate. Weight by recurrence (same correction across 3+ sessions = high priority).
</step>

<step name="4-write">
Write or update these wiki pages in `~/opensource/vault/wiki/`:

- `failure-modes/claude-code-recurring-corrections.md` — corrections by category, each flagged as CLAUDE.md candidate if seen 2+ times
- `projects/vscode.md` — vscode dev environment, CI/sandbox patterns, skills used
- `projects/wipdp.md` — agent builder feature, S3 patterns, PR chain rules, env
- `claude-code-meta/workflow-patterns.md` — skills inventory, orchestration patterns, context management

Each page must have `related:` frontmatter linking to other wiki pages with `[[wikilinks]]`.
</step>

<step name="5-report">
Print a brief summary:
- N sessions analyzed
- Top 3 new failure modes found
- Top new CLAUDE.md candidates
- Any wiki pages updated vs. created new
</step>

</steps>

## Arguments

- No args → last 50 eightfold sessions
- `--project vscode` or `--project wipdp` → filter to one repo
- `--n 100` → change session count
- `--since YYYY-MM-DD` → sessions after date only
