# Claude Code Skills

**7 optimized skills for Claude Code** - refactored from operator_platform/skills/ with improvements for clarity, conciseness, and effectiveness.

## Skills Overview

### 1. **explain-anything.md** (2.3 KB)
Explain any reference as a zero-context story with citations.
- ✅ Fetches source (files, GitHub, Jira, URLs)
- ✅ Narrative arc (problem → cause → solution)
- ✅ Code citations and quotes
- ✅ Call-path tracing

**Use when**: "Explain this error", "What does this PR do?", "Explain the code here"

---

### 2. **submit-pr.md** (4.5 KB)
Create or update GitHub PRs following team standards.
- ✅ Prerequisites check (tests, linting)
- ✅ Commit workflow
- ✅ PR body construction
- ✅ Checklist validation
- ✅ CI failure troubleshooting

**Use when**: "Create a PR", "Submit my changes", "Update the PR"

---

### 3. **work-on-jira-task.md** (2.8 KB)
Complete workflow for picking up and executing a Jira task.
- ✅ Read and understand task
- ✅ Plan implementation
- ✅ Implement and test
- ✅ Create branch and commit
- ✅ PR creation and review cycle

**Use when**: "Pick up task ENG-123", "How do I work on this task?", "Let's build this feature"

---

### 4. **review-pr-architecture.md** (5.4 KB)
Systematic PR review for architecture, patterns, and design quality.
- ✅ Architecture concerns (patterns, boundaries, errors)
- ✅ Performance & security checks
- ✅ Testing strategy review
- ✅ How to comment effectively
- ✅ Red flags and approval criteria

**Use when**: "Review this PR", "Check the design", "Does this follow patterns?"

---

### 5. **create-jira-ticket.md** (2.6 KB)
Create well-structured Jira tickets linked to code.
- ✅ Ticket structure (problem → solution → criteria)
- ✅ Code references (file:line format)
- ✅ Related links (PRs, docs, dependencies)
- ✅ Field setup (epic, priority, points)
- ✅ Quality checklist

**Use when**: "Create a ticket for...", "What's needed to track this?", "Document this task"

---

### 6. **create-tech-doc.md** (4.2 KB)
Write clear technical documentation that gets read.
- ✅ Problem → solution → details narrative
- ✅ Code references
- ✅ Architecture diagrams (ASCII)
- ✅ Configuration, testing, limitations
- ✅ Quality checklist

**Use when**: "Document this feature", "Create design doc", "Write explanation of how this works"

---

### 7. **get-pr-ready-to-merge.md** (4.1 KB)
Checklist and workflow to get PR approved and merged.
- ✅ Status checks
- ✅ Pre-review checklist
- ✅ Address review feedback
- ✅ CI/CD troubleshooting
- ✅ Merge process

**Use when**: "Make sure this PR is ready", "Fix the CI failure", "Can we merge this?"

---

## Improvements Over Original Skills

| Aspect | Original | Improved |
|--------|----------|----------|
| **Length** | 6-8 KB each | 2.3-5.4 KB |
| **Focus** | Comprehensive | Actionable |
| **Examples** | Abstract | Concrete |
| **Navigation** | Long sections | Short, scannable |
| **Code refs** | Mentioned | Specific file:line |
| **Checklists** | Scattered | Consolidated |
| **Tools** | MCP-focused | Claude Code tools |
| **Tone** | Formal | Direct, practical |

## How to Use These Skills

Each skill is **independent** but they work together:

```
Design Phase:
  explain-anything → understand problem
  create-tech-doc → document approach
  create-jira-ticket → track work

Implementation Phase:
  work-on-jira-task → execute task
  submit-pr → propose changes

Review Phase:
  review-pr-architecture → give feedback
  get-pr-ready-to-merge → finalize
```

## Quick Start

### To explain something:
Reference a file, URL, PR number, or Jira ticket, then ask:
```
"Explain what's happening in [reference]"
"What does PR #102400 do?"
"Explain the error in this log"
```

### To work on a task:
Ask Claude to help:
```
"Help me work on task ENG-185314"
"Let's implement [feature] - can you help plan?"
"Create a PR for these changes"
```

### To review code:
Ask Claude for architecture review:
```
"Review PR #102400 for architecture"
"Does this follow our patterns?"
"Check for performance issues in this PR"
```

## Key Principles

All skills follow these principles:

1. **Narrative first, details second** - Explain the "why" before the "how"
2. **Code references matter** - Always point to specific files/lines
3. **Concrete over abstract** - Real examples, real values, real URLs
4. **Scannable format** - Use headers, bullets, checklists
5. **Link everything** - To code, docs, tickets, PRs
6. **Be honest** - Acknowledge limitations and unknowns

## Contributing

To improve these skills:

1. **Try them** - Use each skill in real work
2. **Note what works** - What was helpful?
3. **Note what's missing** - What would improve it?
4. **Update the skill** - Add improvements back here

## Organization

All skills live in `./claude_skills/`:
- One markdown file per skill
- Standalone but interconnected
- No external dependencies
- Easy to search and reference

---

**Created**: March 20, 2026
**Based on**: operator_platform/skills/ (7 original skills)
**Optimized for**: Claude Code + EightfoldAI codebase
