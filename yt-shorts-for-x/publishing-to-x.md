# Publishing clips to X (upload + schedule) — Chrome MCP

The interactive tail of the pipeline: put a finished local clip onto X.com as a native
video upload and **schedule** (or post) it, driven by the **Claude-in-Chrome MCP**. Runs
after clips exist; uploads a local mp4 directly (does not depend on gdrive).

**Use when** the user wants a clip actually posted/scheduled on X (e.g. working through a
run's `POST_KIT.md`), not just produced.

## Which tools (read this first)

Every `find` / `left_click` / `key` / `type` / `screenshot` / `form_input` / `navigate`
below is a **Claude-in-Chrome MCP** tool (`mcp__Claude_in_Chrome__*`) — it acts on the page
DOM. In particular, a bare `computer …` call in the steps (`left_click` / `key` / `type` /
`wait` / `screenshot`) always means **`mcp__Claude_in_Chrome__computer`**. Do **NOT** use the
similarly-named desktop **`computer-use`** server for any of these: browsers are tier `read`
there, so its clicks/keys/typing are blocked and the Cmd-V paste will silently fail.

## The one rule that makes attach reliable

**Never click X's Media/image button** (opens a native macOS file dialog automation can't
drive) and **never use `file_upload`** (its allowlist rejects local disk paths in this
harness — you get `only files the user has shared with this session can be uploaded`).
Instead:

> **Copy the clip to the clipboard as a file reference, then Cmd-V into the composer.**

The copy is done by the script shipped with this skill. Invoke it by **absolute path**
(bash cwd resets between calls in this harness):

```bash
bash ~/.claude/skills/yt-shorts-for-x/scripts/copy_file_to_clipboard.sh /abs/NN_slug.mp4
```

It writes the file reference via macOS `NSPasteboard` (osascript JS-ObjC bridge — no
pyobjc, no Finder automation, so nothing hangs), prints `OK: clipboard now holds a file
reference`, and exits non-zero if the file is missing or the copy didn't take.

## Inputs you need first

The target **mp4 path**, the exact **caption**, the **send time**, and the
**post-now-vs-schedule** flag. For a kit these come from the run's `POST_KIT.md`. If any is
missing, ask the user — don't guess.

## Sequence (per clip)

**0. Account gate — BEFORE composing.** `list_connected_browsers` → `select_browser` (the
   user's named browser; if several profiles are connected and the right one isn't obvious,
   ask). `navigate` to `https://x.com` and read the logged-in handle (left nav / profile).
   If it isn't the intended account, or you can't read it, **HALT and confirm with the
   user** — posting to the wrong account is irreversible.

1. **Open compose:** `tabs_context_mcp(createIfEmpty)` → `navigate` to
   `https://x.com/compose/post`.

2. **Focus the editor:** `find` the compose text editor (the one inside the compose
   *dialog*/modal, NOT the background home-timeline composer) → `left_click` it.

3. **Copy the file to the clipboard NOW** — immediately before pasting, so no intervening
   clipboard write can clobber it:
   `bash ~/.claude/skills/yt-shorts-for-x/scripts/copy_file_to_clipboard.sh /abs/NN_slug.mp4`
   Confirm it printed `OK ... file reference`. Run NO other clipboard-touching tool between
   this and the paste.

4. **Paste:** `key` `cmd+v`. Screenshot — the video thumbnail appears with Edit / remove
   controls.

5. **Wait for upload (poll, don't blind-wait):** loop [`computer` `wait` 2–5s → screenshot]
   until the composer shows `NN_slug.mp4: Uploaded (100%)` (scroll the composer if needed).
   The small blue ring by the Post/Schedule button is the **caption-length counter, NOT** an
   upload spinner — ignore it. Never use a bash `sleep` (blocked). Cap at ~8 attempts
   (~30–60s); if it never completes or X shows a format/length error, remove the media and
   retry once, else **halt and report**.

6. **Type the caption verbatim:** `left_click` the editor → `type` the caption EXACTLY from
   POST_KIT (lowercase, no em dashes; preserve intentional caps like "SaaS" and hyphens;
   newlines are fine — Enter is a line break, not submit). Then screenshot and compare
   char-for-char. X may auto-link URLs, autocomplete `@`mentions / `#`hashtags, or apply
   smart punctuation — if the on-screen text diverges, select-all (`key` `cmd+a` in the
   editor) + delete and retype (or paste the text), then re-verify. Never schedule a caption
   that doesn't match.

   **Post-now clip (#1 in a kit):** skip steps 7–8; go straight to the human gate, then click
   **Post** instead of Schedule.

7. **Open the scheduler:** `find` "Schedule post" (calendar icon) → click. URL becomes
   `/compose/post/schedule`.

8. **Set date + time** — all fields are `<select>` comboboxes (get refs with `find`, set with
   `form_input`; 24-hour, no AM/PM):
   - **Today:** the picker defaults to today — set **Hour** (00–23) and **Minute** only
     (e.g. `21` / `00` = 9:00 PM).
   - **Future date:** also set **Month** (e.g. `May`), **Day** (e.g. `31`), **Year**.
   - **Time zone:** the picker shows the **account's** zone (e.g. "India Standard Time") and
     it is read-only. If the user's intended zone differs, **convert the target time into the
     displayed zone** before setting Hour/Minute, or halt and confirm. An off-by-timezone
     public post is a silent, costly error.
   - Verify the "**Will send on …**" line reads exactly what you intend, then click
     **Confirm** (this only applies the time — it does NOT post).

9. **HUMAN GATE:** screenshot the ready-to-schedule composer (caption + video + "Will send
   on …" banner + a **Schedule** button) and **WAIT for an explicit user "go"** —
   scheduling/posting is an irreversible public action. This gate applies equally to the
   post-now **Post** button.

10. **Schedule / Post:** on "go", `find` the **Schedule** (or **Post**) button → click.
    Confirm the toast: `Your post will be sent on <date> at <time>` (or that it posted).

## Failure modes — handle, don't fight

- **`file_upload` → "only files the user has shared with this session"** — expected here. Do
  not retry it; use the clipboard path.
- **Clipboard copy printed no `furl` / "no file reference"** — paste won't attach. Re-run the
  script (absolute path, file exists); re-verify with
  `osascript -e 'clipboard info' | grep furl` right before pasting.
- **`ModuleNotFoundError: AppKit` / Finder "AppleEvent timed out"** — the pyobjc and Finder
  routes the script deliberately avoids. Don't reintroduce them.
- **Two file inputs / editors found** — use the one in the compose *dialog* (modal).
- **Caption diverged after typing** — see step 6 remediation; a wrong public caption is not
  silently fixable.
