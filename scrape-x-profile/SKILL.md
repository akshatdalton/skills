---
name: scrape-x-profile
description: >
  Scrapes original tweets from any public X (Twitter) profile via the authenticated
  GraphQL UserTweets endpoint, using the user's logged-in Chrome session.
  Filters out retweets and replies. Captures text, datetime, URL, likes, retweets,
  replies, views, bookmarks, quote-tweet metadata, and media URLs.
  Output: append-only `tweets.jsonl` + `profile.json` per handle.
  Incremental by default — re-runs only fetch tweets newer than the last run.
  Use when the user says "scrape @handle", "get tweets from X profile",
  "refresh scrape for @handle", or pastes an X profile URL with scrape intent.
  Args: `@handle [--all | --since=YYYY-MM-DD | --count=N]` (default: --since=auto).
---

# scrape-x-profile

Scrape original tweets from a public X profile via the GraphQL `UserTweets` endpoint, using the logged-in Chrome session. Incremental by default.

**Args:** `@handle [mode]`

| Mode | Behavior |
|---|---|
| (none) | `--since=auto` — anchor on `newest_tweet_id` from existing `profile.json`. Hard cap: 2 pages (~80 tweets). |
| `--all` | Paginate until cursor=null or X's ~3200-tweet history cap. Cap: 5 pages. |
| `--since=YYYY-MM-DD` | Paginate until tweet datetime < that date. |
| `--count=N` | One-shot mode: fetch latest N, no anchor logic. |

Output goes to `~/opensource/vault/raw/x-profiles/{handle}/` unless `--output=<path>` is given.

---

## Step 0 — Parse args

Extract:
- `handle`: strip leading `@`
- `mode`: one of `auto` (default), `all`, `since:YYYY-MM-DD`, `count:N`
- `output_dir`: default `~/opensource/vault/raw/x-profiles/{handle}/`

Print one line: `Scraping @{handle} ({mode}) → {output_dir}`

---

## Step 1 — Load Chrome tools (parallel)

```
ToolSearch: select:mcp__Claude_in_Chrome__tabs_context_mcp,mcp__Claude_in_Chrome__navigate,mcp__Claude_in_Chrome__javascript_tool,mcp__Claude_in_Chrome__read_console_messages
```

---

## Step 2 — Read existing state

Check `{output_dir}/profile.json`:
- If exists: extract `user_id`, `newest_tweet_id`, `newest_tweet_datetime`. These are your incremental anchors. Skip user_id extraction in Step 4 if present.
- If not exists: this is a first scrape. `mode=auto` implicitly degrades to `--all` (no anchor available).

Also check `{output_dir}/tweets.jsonl`:
- If exists, read all `tweet_id`s into a `seen_ids` set for dedup at write time.
- If not exists: empty set.

---

## Step 3 — Open tab + arm pipeline

1. `tabs_context_mcp` → get a tab ID (create if none).
2. Navigate to `https://x.com/{handle}`. Confirm with `document.title` — if it contains "Log in to X" or page is `/i/flow/login`, stop and tell the user to log in.
3. Check pipeline:
   ```js
   typeof window.fetchUserTweetsGQL === 'function' && !!window._GQL_QUERY_ID
   ```
4. If false, arm it by running the **pipeline arming script** (see Appendix A). This sets `window._GQL_QUERY_ID`, `window._FEATURES`, `window._FIELD_TOGGLES`, `window.fetchUserTweetsGQL`, `window.parseTweetsGQL`.

> **Note on query ID rotation:** `_GQL_QUERY_ID` = `3AS73VJOTCg8ePuvJndFew` as of 2026-05. If this fails with HTTP 404, X rotated the operation hash — open DevTools Network tab on x.com, look for a `UserTweets` request, copy the hash from the URL path, update Appendix A.

---

## Step 4 — Extract profile metadata + user_id

If `user_id` was loaded from existing `profile.json` in Step 2, skip the React-fiber extraction and only run the DOM metadata script.

Otherwise, run combined extraction on the current tab:

```javascript
(function() {
  // ── user_id via React fiber walk on UserName element ──
  let userId = null;
  const nameEl = document.querySelector('[data-testid="UserName"]');
  if (nameEl) {
    const fiberKey = Object.keys(nameEl).find(k => k.startsWith('__reactFiber$'));
    if (fiberKey) {
      let fiber = nameEl[fiberKey];
      for (let i = 0; i < 50 && fiber && !userId; i++) {
        const props = fiber.memoizedProps;
        if (props) {
          const id = props.userId || props.user_id || props.rest_id || props.id_str;
          if (id) userId = String(id);
        }
        fiber = fiber.return;
      }
    }
  }

  // ── DOM metadata ──
  const displayName = nameEl ? (nameEl.querySelector('span')?.innerText || '') : '';
  const bioEl = document.querySelector('[data-testid="UserDescription"]');
  const bio = bioEl ? bioEl.innerText : '';
  const websiteEl = document.querySelector('[data-testid="UserUrl"] a');
  const website = websiteEl ? websiteEl.innerText.trim() : '';
  const joinedEl = document.querySelector('[data-testid="UserJoinDate"]');
  const joined = joinedEl ? joinedEl.innerText.replace(/^joined\s*/i, '').trim() : '';
  const locationEl = document.querySelector('[data-testid="UserLocation"]');
  const location = locationEl ? locationEl.innerText.trim() : '';

  // followers / following — parse from stat links.
  // Note: X uses /verified_followers (not /followers) as the link href on many profiles; match both.
  let following = '', followers = '';
  document.querySelectorAll('a[href$="/following"], a[href$="/followers"], a[href$="/verified_followers"]').forEach(a => {
    const parts = a.innerText.trim().split(/\s+/);
    const label = (parts[1] || '').toLowerCase();
    if (label === 'following') following = parts[0];
    if (label === 'followers') followers = parts[0];
  });

  // verified
  const verified = !!document.querySelector('[data-testid="UserName"] svg[aria-label*="Verified"]');

  // pinned tweet URL — scan top articles for socialContext="Pinned"
  let pinnedTweetUrl = '';
  document.querySelectorAll('article[data-testid="tweet"]').forEach(a => {
    if (pinnedTweetUrl) return;
    const sc = a.querySelector('[data-testid="socialContext"]');
    if (sc && sc.innerText.toLowerCase().includes('pinned')) {
      const l = a.querySelector('a[href*="/status/"]');
      if (l) pinnedTweetUrl = 'https://x.com' + l.getAttribute('href');
    }
  });

  const avatarImg = document.querySelector('a[href$="/photo"] img, [data-testid="UserAvatar-Container"] img');
  const avatarUrl = avatarImg ? avatarImg.src : '';

  return JSON.stringify({ user_id: userId, display_name: displayName, bio, location, website,
    joined, followers, following, verified, pinned_tweet_url: pinnedTweetUrl, avatar_url: avatarUrl });
})()
```

Parse the returned JSON. If `user_id` is null, abort with error: "couldn't extract user_id — check the page loaded and you're logged in."

Normalize `followers`/`following`: convert "1.2K", "56.7K", "1.5M" → integer. Strip commas first.

---

## Step 5 — Fetch loop (GraphQL + cursor + rate limit)

For each page (up to the cap for the current mode):

```javascript
(async () => {
  const data = await window.fetchUserTweetsGQL('{user_id}', {cursor_or_null});
  if (data.error) { console.log('[FETCH_ERR] ' + data.error); return; }
  const { tweets, cursor } = window.parseTweetsGQL(data);
  // Filter belt-and-suspenders: skip if text starts with 'RT @' (some self-RTs escape the legacy.retweeted_status_id_str filter)
  const clean = tweets.filter(t => !t.text.startsWith('RT @'));
  // Stamp URL with handle
  clean.forEach(t => { t.url = `https://x.com/{handle}/status/${t.tweet_id}`; });
  console.log('[PAGE_META] ' + JSON.stringify({ count: clean.length, cursor: !!cursor }));
  // Chunk tweets to console to stay under read-message size limits
  const CHUNK = 25;
  for (let i = 0; i < clean.length; i += CHUNK) {
    console.log('[T_' + Math.floor(i/CHUNK) + '] ' + JSON.stringify(clean.slice(i, i+CHUNK)));
  }
  window._lastCursor = cursor;
  window._lastBatchSize = clean.length;
})();
```

**Between pages:** sleep 2000ms.
**Between accounts** (if used in a bulk loop): sleep 3000ms.

**Read console after each page:**
```
read_console_messages(tabId, pattern="\[(T_|PAGE_META|FETCH_ERR)", limit=10, clear=true)
```

Parse each `[T_N] ...` line. Build `page_tweets` array.

**Stop conditions per mode:**
- `auto`: stop when any tweet in `page_tweets` matches `newest_tweet_id` from profile.json (anchor hit), OR cursor=null, OR page count >= 2.
- `all`: stop when cursor=null OR page count >= 5.
- `since:DATE`: stop when any tweet's datetime < DATE, OR cursor=null OR page count >= 5.
- `count:N`: stop when collected.length >= N OR cursor=null OR page count >= 5.

When stop condition is met, slice `page_tweets` at the anchor (drop the anchor tweet and anything older).

**Rate limit handling — see Appendix B.** Implement before going to production. Defaults: hard cap 2 pages in auto mode, 5 in --all. Stop on first 429 in this skill (we're scraping one handle — let the bulk wrapper handle retries).

---

## Step 6 — Dedup, sort, write

Across all pages, you now have `new_tweets`. Dedup vs existing `seen_ids` from Step 2. Sort by `datetime` ascending (oldest first).

**Append to `{output_dir}/tweets.jsonl`** — one JSON object per line, no surrounding array. Use `>>` append, never overwrite. Create the file (with empty content) if it doesn't exist before appending.

```python
import os, json
os.makedirs(output_dir, exist_ok=True)
jsonl_path = os.path.join(output_dir, 'tweets.jsonl')
with open(jsonl_path, 'a') as f:
    for t in new_tweets:  # already sorted oldest-first
        f.write(json.dumps(t, ensure_ascii=False) + '\n')
```

**Update `{output_dir}/profile.json`** — full overwrite with merged state:

```json
{
  "handle": "{handle}",
  "user_id": "{user_id}",
  "display_name": "...",
  "bio": "...",
  "location": "...",
  "website": "...",
  "joined": "...",
  "followers": 123456,
  "following": 789,
  "verified": true,
  "pinned_tweet_url": "...",
  "avatar_url": "...",
  "newest_tweet_id": "{max tweet_id across stored + new}",
  "newest_tweet_datetime": "{ISO 8601}",
  "tweet_count_total": {count after this run},
  "last_scraped_at": "{ISO 8601 of this run}",
  "last_scrape_added": {count added this run}
}
```

If the new run added zero tweets, still update `last_scraped_at` and `last_scrape_added=0` — that's useful signal (the handle was checked recently).

---

## Step 7 — Print summary

```
@{handle} → {N} new tweets ({total} total)

  Date        Likes   RTs  Views    Preview
  2026-05-26  4.5K    419  367K     "I just got back from SF and I FEEL INSP..."
  2026-05-25  1.2K    113  103K     "How to build a vertical AI agent..."
  ...
```

Show up to 5 most-recent new tweets. K/M suffix for large numbers. Pinned: prefix with `📌`.
If no new tweets: print `@{handle} → up to date (last_scraped={ts})`.

---

## Error handling

| Situation | Action |
|---|---|
| Not logged in / login wall | Stop. Tell user to log into X in Chrome. |
| 404 on profile | Stop. Likely suspended or doesn't exist. |
| `user_id` extraction fails | Stop. Suggests page didn't load or fiber structure changed. |
| HTTP 429 on fetch | Stop, write what was collected, report `rate_limited=true` so caller can retry later. |
| HTTP 401/403 on fetch | Stop. Session expired — tell user to refresh the page and re-run. |
| Cursor returned but pages cap hit | Print warning `truncated_at_page_cap=true` in summary. |
| Pipeline arming fails | Stop. Check `_GQL_QUERY_ID` rotation per Step 3 note. |

---

## Appendix A — Pipeline arming script

Run once per session (or after a hard reload of the tab) before any fetch:

```javascript
window._GQL_QUERY_ID = '3AS73VJOTCg8ePuvJndFew';

const FEATURES_OBJ = {"rweb_video_screen_enabled":false,"rweb_cashtags_enabled":true,"profile_label_improvements_pcf_label_in_post_enabled":true,"responsive_web_profile_redirect_enabled":false,"rweb_tipjar_consumption_enabled":false,"verified_phone_label_enabled":true,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"premium_content_api_read_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"responsive_web_grok_analyze_button_fetch_trends_enabled":false,"responsive_web_grok_analyze_post_followups_enabled":true,"articles_preview_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"responsive_web_enhance_cards_enabled":false};
window._FEATURES = encodeURIComponent(JSON.stringify(FEATURES_OBJ));
window._FIELD_TOGGLES = encodeURIComponent(JSON.stringify({"withArticlePlainText":false}));

window.fetchUserTweetsGQL = async function(userId, cursor) {
  const ct0 = document.cookie.match(/ct0=([^;]+)/)?.[1] || '';
  const BEARER = 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA';
  const vars = { userId, count: 40, includePromotedContent: false, withVoice: true };
  if (cursor) vars.cursor = cursor;
  const url = '/i/api/graphql/' + window._GQL_QUERY_ID + '/UserTweets?variables=' + encodeURIComponent(JSON.stringify(vars)) + '&features=' + window._FEATURES + '&fieldToggles=' + window._FIELD_TOGGLES;
  const resp = await fetch(url, { headers: { 'authorization': BEARER, 'x-csrf-token': ct0, 'x-twitter-active-user': 'yes' }, credentials: 'include' });
  if (!resp.ok) {
    const reset = resp.headers.get('x-rate-limit-reset');
    return { error: 'HTTP ' + resp.status, rate_limit_reset: reset ? parseInt(reset,10) : null };
  }
  return await resp.json();
};

window.parseTweetsGQL = function(data) {
  const instructions = data?.data?.user?.result?.timeline?.timeline?.instructions || [];
  const tweets = [];
  let cursor = null;

  const extractTweet = (raw, isPinned) => {
    if (!raw) return null;
    const tw = raw.__typename === 'TweetWithVisibilityResults' ? raw.tweet : raw;
    const leg = tw?.legacy;
    if (!leg) return null;
    if (leg.retweeted_status_id_str) return null; // skip RTs
    if (leg.in_reply_to_status_id_str) return null; // skip replies (incl. self-replies/threads — change here if you want threads)
    const mediaUrls = (leg.extended_entities?.media || leg.entities?.media || [])
      .map(m => (m.media_url_https || '').split('?')[0])
      .filter(Boolean);
    return {
      tweet_id: leg.id_str,
      url: '',  // stamped later by caller
      datetime: new Date(leg.created_at).toISOString(),
      text: leg.full_text || leg.text || '',
      is_pinned: !!isPinned,
      is_quote_tweet: !!leg.quoted_status_id_str,
      quoted_tweet_url: leg.quoted_status_id_str ? 'https://x.com/i/status/' + leg.quoted_status_id_str : '',
      has_media: mediaUrls.length > 0,
      media_urls: mediaUrls,
      metrics: {
        replies: leg.reply_count || 0,
        retweets: leg.retweet_count || 0,
        likes: leg.favorite_count || 0,
        bookmarks: leg.bookmark_count || 0,
        views: parseInt(String(tw.views?.count || '0').replace(/,/g, ''), 10)
      }
    };
  };

  for (const instruction of instructions) {
    // Pinned tweet — singular `entry` (not in TimelineAddEntries for some profiles)
    if (instruction.type === 'TimelinePinEntry' && instruction.entry) {
      const ic = instruction.entry.content?.itemContent;
      if (ic?.itemType === 'TimelineTweet') {
        const t = extractTweet(ic.tweet_results?.result, true);
        if (t) tweets.push(t);
      }
      continue;
    }
    if (instruction.type !== 'TimelineAddEntries') continue;
    for (const entry of (instruction.entries || [])) {
      const et = entry.content?.entryType;
      if (et === 'TimelineTimelineCursor' && entry.content?.cursorType === 'Bottom') {
        cursor = entry.content.value;
      } else if (et === 'TimelineTimelineItem' && entry.content?.itemContent?.itemType === 'TimelineTweet') {
        const t = extractTweet(entry.content.itemContent.tweet_results?.result, entry.entryId?.startsWith('tweet-pinned'));
        if (t) tweets.push(t);
      } else if (et === 'TimelineTimelineModule') {
        for (const item of (entry.content?.items || [])) {
          if (item.item?.itemContent?.itemType !== 'TimelineTweet') continue;
          const t = extractTweet(item.item.itemContent.tweet_results?.result, false);
          if (t) tweets.push(t);
        }
      }
    }
  }
  return { tweets, cursor };
};

'pipeline armed';
```

---

## Appendix B — Rate limit policy (bake in)

| Setting | Value |
|---|---|
| Inter-page sleep | 2000ms |
| Inter-account sleep | 3000ms (when used in bulk wrapper) |
| Max pages — `auto` | 2 |
| Max pages — `since`, `count`, `all` | 5 |
| HTTP 429 → action | Stop; persist what was collected; return `rate_limited=true` |
| HTTP 401/403 → action | Stop; report session expired |
| Concurrency | 1 (sequential — parallel hits the same per-account rate-limit budget) |
| Burner account note | This skill should be run against a session logged into a *non-primary* X account. The data is public; the auth is just for endpoint access. |

If the caller is a bulk wrapper, it should:
- Track total requests across handles in a 15-min window
- Sleep until `x-rate-limit-reset + 30s buffer` on first 429
- Abort if a second 429 happens within the same window

---

## Appendix C — Tweet schema (one line per record in `tweets.jsonl`)

```json
{
  "tweet_id": "string",
  "url": "https://x.com/{handle}/status/{tweet_id}",
  "datetime": "ISO 8601 (Z)",
  "text": "raw tweet text (full_text from GraphQL — not truncated)",
  "is_pinned": false,
  "is_quote_tweet": false,
  "quoted_tweet_url": "" ,
  "has_media": false,
  "media_urls": ["https://pbs.twimg.com/..."],
  "metrics": { "replies": 0, "retweets": 0, "likes": 0, "bookmarks": 0, "views": 0 }
}
```

`replies_data` (reply payloads) lives in a separate `replies.jsonl` file in a future pass — not written by this skill.
