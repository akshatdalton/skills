#!/usr/bin/env python3
"""
kanban.py — projects the vault task board into an Obsidian Kanban file and
syncs edits back.

The vault progress.md frontmatter is the single source of truth. This tool:
  render    walk vault frontmatters -> write Tasks.md (an Obsidian Kanban board)
  readback  parse Tasks.md -> write state/bucket back into vault frontmatter
  sync      readback then render (what /today calls each run)
  migrate   one-time: seed `bucket: today` from today.json today_ids

Board lanes (left -> right): Backlog | To Do | In Progress | In Review | Done.
A card's lane is a function of (state, bucket):
  - todo-ish state + bucket=backlog -> Backlog ; bucket=today -> To Do
  - in-progress states -> In Progress ; review states -> In Review ; done -> Done

Conflict rule (split by field) when both you (drag) and automation (a skill
writing vault state) moved a ticket since the last render:
  - bucket (today/backlog) : the board always wins — only you ever set it.
  - state                  : automation wins — a PR/CI move beats a stale drag.
We detect "who moved it" by comparing each side against the lane we last
rendered, stored per-ticket in a small ledger.
"""
from __future__ import annotations
import argparse, datetime as dt, json, re
from pathlib import Path

VAULT = Path.home() / "opensource/vault"
PROJECTS = VAULT / "wiki/projects"
BOARD_FILE = VAULT / "Tasks.md"
LEDGER = Path.home() / ".claude/work_hq/.kanban_state.json"
TODAY_JSON = Path.home() / ".claude/work_hq/today.json"
REPOS = ("vscode", "wipdp")

LANES = ["Backlog", "To Do", "In Progress", "In Review", "Done"]

TODO_STATES = {"new", "planning", "todo"}
PROGRESS_STATES = {"in-progress", "implementing"}
REVIEW_STATES = {"in-review", "pr_in_review", "ci", "testing", "ready-to-merge"}
DONE_STATES = {"merged", "closed"}
HIDDEN_STATES = {"abandoned", "archived"}  # never rendered on the board

TICKET_RE = re.compile(r"ENG-\d+")
SETTINGS_DEFAULT = '{"kanban-plugin":"board"}'


def today_str() -> str:
    return dt.date.today().isoformat()


# ---------------------------------------------------------------- lane mapping
def lane_for(state: str, bucket: str) -> str | None:
    """Forward map: which lane a ticket renders into. None = hidden."""
    if state in HIDDEN_STATES:
        return None
    if state in DONE_STATES:
        return "Done"
    if state in REVIEW_STATES:
        return "In Review"
    if state in PROGRESS_STATES:
        return "In Progress"
    # todo-ish or unknown -> Backlog/To Do split on bucket
    return "To Do" if bucket == "today" else "Backlog"


def state_for_lane(lane: str, cur_state: str) -> str | None:
    """Reverse map applied when YOU drag a card. Preserves todo-ish nuance."""
    if lane in ("Backlog", "To Do"):
        return cur_state if cur_state in TODO_STATES else "todo"
    if lane == "In Progress":
        return "in-progress"
    if lane == "In Review":
        return "in-review"
    if lane == "Done":
        return "merged"
    return None


def bucket_for_lane(lane: str) -> str:
    return "backlog" if lane == "Backlog" else "today"


# ----------------------------------------------------------------- vault model
def _frontmatter_region(text: str) -> tuple[int, int] | None:
    """Return (start, end) line indices of the frontmatter body (exclusive of
    the --- fences), or None if there is no frontmatter."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return (1, i)
    return None


def read_frontmatter(path: Path) -> dict:
    """Extract the scalar fields we care about. Lightweight, no PyYAML."""
    text = path.read_text()
    region = _frontmatter_region(text)
    if not region:
        return {}
    lines = text.splitlines()
    out: dict = {}
    for line in lines[region[0]:region[1]]:
        m = re.match(r"^([\w-]+):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip().strip('"').strip("'")
        if key not in out:  # top-level only; ignore nested (needs_input, etc.)
            out[key] = val
    return out


def write_frontmatter_fields(path: Path, updates: dict) -> None:
    """Surgically set/insert scalar frontmatter keys, leaving everything else
    (body, nested blocks, quoted titles, lists) byte-for-byte intact."""
    text = path.read_text()
    region = _frontmatter_region(text)
    if not region:
        raise ValueError(f"{path} has no frontmatter")
    lines = text.splitlines(keepends=True)
    nl = "\n"
    start, end = region  # body line range [start, end)
    remaining = dict(updates)
    for i in range(start, end):
        m = re.match(r"^([\w-]+):", lines[i])
        if m and m.group(1) in remaining:
            key = m.group(1)
            lines[i] = f"{key}: {remaining.pop(key)}{nl}"
    # insert any keys that weren't already present, just before the closing ---
    if remaining:
        ins = [f"{k}: {v}{nl}" for k, v in remaining.items()]
        lines[end:end] = ins
    path.write_text("".join(lines))


def walk_vault() -> list[dict]:
    """All active (non-archived) tickets with their frontmatter + paths."""
    tasks = []
    for repo in REPOS:
        d = PROJECTS / repo / "progress"
        if not d.exists():
            continue
        for child in sorted(d.iterdir()):
            if not child.is_dir() or not child.name.startswith("ENG-"):
                continue
            fm_file = child / "progress.md"
            if not fm_file.exists():
                continue
            fm = read_frontmatter(fm_file)
            tid = fm.get("ticket") or child.name
            tasks.append({
                "id": tid,
                "title": fm.get("title", ""),
                "state": fm.get("state", "new"),
                "bucket": fm.get("bucket", "backlog"),
                "priority": fm.get("priority", "P2"),
                "repo": repo,
                "path": fm_file,
                "relpath": fm_file.relative_to(VAULT).with_suffix("").as_posix(),
            })
    return tasks


def vault_index() -> dict:
    """ticket id -> path, for read-back lookups."""
    return {t["id"]: t["path"] for t in walk_vault()}


# ----------------------------------------------------------------- board parse
def parse_board(text: str) -> dict:
    """Parse an existing Tasks.md into {order, settings, description}.
    order: {lane: [ticket ids in file order]}.  Used to preserve manual sort."""
    order: dict[str, list[str]] = {ln: [] for ln in LANES}
    lane = None
    settings = None
    desc_lines: list[str] = []
    seen_lane = False
    lines = text.splitlines()
    i = 0
    # skip frontmatter
    region = _frontmatter_region(text)
    if region:
        i = region[1] + 1  # past closing ---
    while i < len(lines):
        line = lines[i]
        if line.startswith("%% kanban:settings"):
            block = [line]
            i += 1
            while i < len(lines):
                block.append(lines[i])
                if lines[i].strip() == "%%":
                    break
                i += 1
            settings = "\n".join(block)
            i += 1
            continue
        h = re.match(r"^##\s+(.*)$", line)
        if h:
            seen_lane = True
            lane = h.group(1).strip()
            order.setdefault(lane, [])
            i += 1
            continue
        if lane is not None and line.lstrip().startswith("- "):
            m = TICKET_RE.search(line)
            if m:
                order[lane].append(m.group(0))
        elif not seen_lane and line.strip() and not line.startswith("**"):
            desc_lines.append(line)
        i += 1
    return {
        "order": order,
        "settings": settings,
        "description": "\n".join(desc_lines).strip(),
    }


def board_lanes_by_ticket(text: str) -> dict:
    """ticket id -> current lane in the board file."""
    parsed = parse_board(text)
    out = {}
    for lane, tids in parsed["order"].items():
        for tid in tids:
            out[tid] = lane
    return out


# ----------------------------------------------------------------------- ledger
def load_ledger() -> dict:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text())
    return {}


def save_ledger(led: dict) -> None:
    LEDGER.write_text(json.dumps(led, indent=2))


# ----------------------------------------------------------------------- render
def _card(t: dict) -> str:
    title = re.sub(r"[\[\]|]", "", t["title"]).strip()
    tag = "#" + (t["priority"] or "P2")
    return f"- [ ] [[{t['relpath']}|{t['id']}]] — {title} {tag} #{t['repo']}"


def render() -> str:
    tasks = walk_vault()
    by_lane: dict[str, list[dict]] = {ln: [] for ln in LANES}
    for t in tasks:
        lane = lane_for(t["state"], t["bucket"])
        if lane:
            by_lane[lane].append(t)

    prev = parse_board(BOARD_FILE.read_text()) if BOARD_FILE.exists() else {
        "order": {}, "settings": None, "description": ""
    }

    def ordered(lane: str) -> list[dict]:
        prior = prev["order"].get(lane, [])
        rank = {tid: i for i, tid in enumerate(prior)}
        # keep prior order for known cards; new cards sort after, by priority
        return sorted(
            by_lane[lane],
            key=lambda t: (rank.get(t["id"], len(prior)), t.get("priority", "P2"), t["id"]),
        )

    settings = prev["settings"] or f"%% kanban:settings\n```\n{SETTINGS_DEFAULT}\n```\n%%"
    description = prev["description"]
    if not description and TODAY_JSON.exists():
        try:
            description = json.loads(TODAY_JSON.read_text()).get("notes", "").strip()
        except Exception:
            description = ""

    parts = ["---", "", "kanban-plugin: board", "", "---", ""]
    if description:
        parts += [description, ""]
    led: dict = {}
    for lane in LANES:
        parts.append(f"## {lane}")
        parts.append("")
        for t in ordered(lane):
            parts.append(_card(t))
            led[t["id"]] = {"lane": lane, "state": t["state"], "bucket": t["bucket"]}
        parts.append("")
    parts.append(settings)
    out = "\n".join(parts).rstrip() + "\n"

    BOARD_FILE.write_text(out)
    save_ledger(led)
    return out


# --------------------------------------------------------------------- readback
def readback(dry_run: bool = False) -> list[str]:
    """Fold board edits back into vault frontmatter. Returns human log lines."""
    if not BOARD_FILE.exists():
        return ["(no board file yet — nothing to read back)"]
    board_lane = board_lanes_by_ticket(BOARD_FILE.read_text())
    index = vault_index()
    led = load_ledger()
    log: list[str] = []

    for tid, cur_lane in board_lane.items():
        path = index.get(tid)
        if not path:
            continue  # draft / orphan card — leave it on the board
        fm = read_frontmatter(path)
        cur_state = fm.get("state", "new")
        cur_bucket = fm.get("bucket", "backlog")
        prev_lane = led.get(tid, {}).get("lane")
        vault_lane = lane_for(cur_state, cur_bucket)

        user_moved = prev_lane is not None and cur_lane != prev_lane
        auto_moved = prev_lane is not None and vault_lane != prev_lane

        updates: dict = {}
        # bucket: the board always wins — but it only *means* anything for the
        # Backlog vs To Do split, so never churn it on active/done lanes.
        if cur_lane in ("Backlog", "To Do"):
            new_bucket = bucket_for_lane(cur_lane)
            if new_bucket != cur_bucket:
                updates["bucket"] = new_bucket
        # state: follow the board only when you moved it and automation didn't.
        if user_moved and not auto_moved:
            new_state = state_for_lane(cur_lane, cur_state)
            if new_state and new_state != cur_state:
                updates["state"] = new_state
        elif user_moved and auto_moved:
            log.append(f"  {tid}: conflict — keeping vault state '{cur_state}' "
                       f"(automation wins); board placement deferred")

        if updates:
            if "state" in updates:   # a planning-only bucket move isn't a "touch"
                updates["last-touched"] = today_str()
            changed = ", ".join(f"{k}={v}" for k, v in updates.items() if k != "last-touched")
            log.append(f"  {tid}: {changed}  [{prev_lane} -> {cur_lane}]")
            if not dry_run:
                write_frontmatter_fields(path, updates)

    # NB: the ledger ("last rendered lanes") is the baseline for detecting your
    # drags — only render() writes it. sync() always renders after readback, so
    # the ledger is fresh for the next run.
    if not log:
        log.append("  (no board edits to fold back)")
    return log


# ---------------------------------------------------------------------- migrate
def migrate(dry_run: bool = False) -> list[str]:
    """One-time: seed bucket:today from today.json today_ids."""
    log: list[str] = []
    if not TODAY_JSON.exists():
        return ["today.json not found — nothing to migrate"]
    today_ids = json.loads(TODAY_JSON.read_text()).get("today_ids", [])
    index = vault_index()
    for tid in today_ids:
        path = index.get(tid)
        if not path:
            log.append(f"  {tid}: skipped (no progress.md — ghost id)")
            continue
        fm = read_frontmatter(path)
        if fm.get("bucket") == "today":
            log.append(f"  {tid}: already today")
            continue
        log.append(f"  {tid}: bucket -> today")
        if not dry_run:
            write_frontmatter_fields(path, {"bucket": "today"})
    if not log:
        log.append("  (no today_ids to migrate)")
    return log


# ------------------------------------------------------------------------- main
def main():
    p = argparse.ArgumentParser(description="Obsidian Kanban <-> vault sync")
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("render", help="vault -> Tasks.md")
    rb = sp.add_parser("readback", help="Tasks.md -> vault frontmatter")
    rb.add_argument("--dry-run", action="store_true")
    sp.add_parser("sync", help="readback then render")
    mg = sp.add_parser("migrate", help="seed bucket:today from today.json")
    mg.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if args.cmd == "render":
        render()
        print(f"rendered {BOARD_FILE}")
    elif args.cmd == "readback":
        for line in readback(dry_run=args.dry_run):
            print(line)
        if args.dry_run:
            print("(dry-run — no files written)")
    elif args.cmd == "sync":
        print("readback:")
        for line in readback():
            print(line)
        render()
        print(f"rendered {BOARD_FILE}")
    elif args.cmd == "migrate":
        for line in migrate(dry_run=args.dry_run):
            print(line)
        if args.dry_run:
            print("(dry-run — no files written)")


if __name__ == "__main__":
    main()
