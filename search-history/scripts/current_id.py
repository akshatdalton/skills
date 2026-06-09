#!/usr/bin/env python3
"""
current_id.py — Reliably resolve the CURRENT Claude Code session id.

Works for BOTH Claude Code CLI and Claude Desktop "Code" sessions: both write
their transcripts to ~/.claude/projects/ and both register in ~/.claude/sessions/.

Resolution order (deterministic, no disk-flush latency):
  Tier 1  $CLAUDE_CODE_SESSION_ID            — instant, exact, set in every session shell
  Tier 2  PID-walk -> ~/.claude/sessions/<pid>.json
          Walks THIS process's ancestry, so concurrent sessions in the same cwd
          never collide (unlike "newest mtime", which is a coin-flip across tabs).

It then CONFIRMS by locating the transcript via rglob("<sid>.jsonl") and printing
cwd / surface / last user message. If Tiers 1 and 2 both yield an id they are
cross-checked and any disagreement is surfaced.

Usage:
  python3 current_id.py            # full diagnostic box (default)
  python3 current_id.py --quiet    # print ONLY the session id (for scripting); exit 1 if unknown
  python3 current_id.py --path     # print ONLY the transcript JSONL path; exit 1 if not on disk yet
"""
import os, sys, json, subprocess
from pathlib import Path

HOME = Path.home()
PROJECTS = HOME / ".claude" / "projects"
REG = HOME / ".claude" / "sessions"
QUIET = "--quiet" in sys.argv[1:]
PATH = "--path" in sys.argv[1:]


def transcript_for(sid):
    if not sid:
        return None
    hits = [h for h in PROJECTS.rglob(f"{sid}.jsonl") if "subagents" not in h.parts]
    return hits[0] if hits else None


def ppid_of(pid):
    try:
        out = subprocess.run(["ps", "-o", "ppid=", "-p", str(pid)],
                             capture_output=True, text=True).stdout.strip()
        return int(out) if out else None
    except Exception:
        return None


def alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


def last_user_msg(path):
    """Last human turn (skip tool results / system-reminder <...> blocks)."""
    last = ""
    try:
        for line in open(path):
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("type") != "user" or e.get("isSidechain"):
                continue
            c = e.get("message", {}).get("content", "")
            if isinstance(c, list):
                c = "".join(b.get("text", "") for b in c
                            if isinstance(b, dict) and b.get("type") == "text")
            if isinstance(c, str) and c.strip() and not c.lstrip().startswith("<"):
                last = c.strip()
    except Exception:
        pass
    return last


# ── Tier 1: env var ──────────────────────────────────────────────────────────
env_sid = os.environ.get("CLAUDE_CODE_SESSION_ID") or ""

# ── Tier 2: PID-walk registry (also gives confirming metadata when env is set) ─
reg_sid, reg_meta = None, None
pid, hops = os.getpid(), 0
while pid and pid > 1 and hops < 12:
    f = REG / f"{pid}.json"
    if f.exists():
        try:
            reg_meta = json.load(open(f))
            reg_sid = reg_meta.get("sessionId")
            break
        except Exception:
            pass
    pid, hops = ppid_of(pid), hops + 1

sid = env_sid or reg_sid
source = ("CLAUDE_CODE_SESSION_ID env var" if env_sid
          else "PID->registry walk" if reg_sid else None)

# ── Scripting modes: bare id / bare transcript path ──────────────────────────
if PATH:
    t = transcript_for(sid)
    if t:
        print(t)
        sys.exit(0)
    sys.exit(1)  # id may be valid but transcript not yet flushed
if QUIET:
    if sid:
        print(sid)
        sys.exit(0)
    sys.exit(1)

# ── Full diagnostic ──────────────────────────────────────────────────────────
print("=" * 64)
if not sid:
    print("Could not determine session id.")
    print("  $CLAUDE_CODE_SESSION_ID is unset AND no registry file matched this")
    print("  process's ancestry. Use the random-marker grep last resort (see SKILL.md).")
else:
    print(f"Session ID : {sid}")
    print(f"  source   : {source}")
    if env_sid and reg_sid:
        print(f"  registry : {reg_sid}  [{'AGREE' if env_sid == reg_sid else 'DISAGREE (!) — nested/wrapped session?'}]")
    m = reg_meta or {}
    if m:
        print(f"  cwd      : {m.get('cwd')}")
        print(f"  surface  : {m.get('entrypoint')}  (pid={m.get('pid')}, alive={alive(m.get('pid'))})")
        if m.get("name"):
            print(f"  name     : {m.get('name')}")
    t = transcript_for(sid)
    print(f"  transcript: {t if t else '(not yet flushed to disk — id is still valid)'}")
    if t:
        lu = last_user_msg(t)
        if lu:
            print(f"  last user : {lu[:140]}")
print("=" * 64)
