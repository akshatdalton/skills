---
name: sync-skills
description: Push local skill changes to GitHub. Use when user says /sync-skills, "sync my skills", "push skills to GitHub", "update skills repo", or "sync skills".
---

# Sync Skills to GitHub

Commit any changes in `~/.claude/skills/` and push to `git@github-personal:akshatdalton/skills.git`.

## Steps

**1. Pull rebase from main**
```bash
git -C ~/.claude/skills pull --rebase
```
- If this fails (conflicts or error): report the error and stop. Do not proceed with commit.

**2. Stage all changes**
```bash
git -C ~/.claude/skills add -A
```

**3. Check if anything to commit**
```bash
git -C ~/.claude/skills diff --cached --quiet
```
- If exit 0 (nothing staged): report "Nothing to sync — skills are already up to date." and stop.
- If exit 1 (changes staged): continue.

**4. Build commit message**
List the changed files:
```bash
git -C ~/.claude/skills diff --cached --name-only
```
Use the file names to write a short message, e.g. `skills: update submit-pr, add sync-skills 2026-04-07`.

**5. Commit and push**
```bash
git -C ~/.claude/skills commit -m "<message from step 4>"
git -C ~/.claude/skills push
```

**6. Report result**
Show the commit hash + message and confirm push succeeded.

---

## If new skills were added

After pushing, remind the user to pull on any other machine:
```bash
git -C ~/.claude/skills pull
```
Skills load directly from `~/.claude/skills/` — no plugin install needed. Pull is enough.
