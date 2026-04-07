---
name: scrape-x-profile
description: >
  Scrapes structured tweet data from any public X (Twitter) profile using Chrome
  browser automation. Extracts only original tweets and quote-tweets (no retweets,
  no replies). Captures text, datetime, URL, likes, retweets, replies, views,
  bookmarks, media, and quote-tweet metadata. Saves output as JSON in the current
  working directory. Use when the user says "scrape tweets from @handle",
  "get tweets from X profile", "extract tweet data", "analyze tweets from",
  or provides a handle and a count. Args format: `@handle [count]` (count defaults to 20).
---

# scrape-x-profile

Scrape structured tweet data from a public X profile for analysis.

**Args:** `@handle [count]`  — e.g. `/scrape-x-profile @trq212 30`

---

## Step 0 — Parse args

Extract from the user's invocation:
- `handle`: the @handle (strip the `@` for URL use)
- `count`: number of original tweets to collect (default: 20, max: 100)

Confirm with one line: `Scraping {count} tweets from @{handle}…`

---

## Step 1 — Load browser tools (parallel)

Use ToolSearch to load all four tools **in a single parallel message**:

```
ToolSearch: select:mcp__claude-in-chrome__tabs_context_mcp
ToolSearch: select:mcp__claude-in-chrome__navigate
ToolSearch: select:mcp__claude-in-chrome__javascript_tool
ToolSearch: select:mcp__claude-in-chrome__read_console_messages
```

---

## Step 2 — Open profile

1. Call `tabs_context_mcp` with `createIfEmpty: true` to get a tab ID. Call this **tab A** (profile tab).
2. Navigate to `https://x.com/{handle}` on tab A.
3. Confirm page loaded by running `document.title`. If it redirects to login, stop and tell the user to log in first.

---

## Step 3 — Scrape profile metadata + first tweet batch (combined)

Run profile metadata and first tweet extraction **as a single JS call** to avoid a round-trip:

```javascript
(function() {
  // ── PROFILE ──────────────────────────────────────────────
  const nameEl = document.querySelector('[data-testid="UserName"]');
  const displayName = nameEl ? nameEl.querySelector('span')?.innerText : '';
  const handleEl = nameEl ? nameEl.querySelectorAll('span')[3] : null;
  const handle = handleEl ? handleEl.innerText : '';

  const bioEl = document.querySelector('[data-testid="UserDescription"]');
  const bio = bioEl ? bioEl.innerText : '';

  // Website — use data-testid="UserUrl" first, fall back to header items
  const websiteEl = document.querySelector('[data-testid="UserUrl"] a');
  const website = websiteEl ? websiteEl.innerText.trim() : '';

  // Joined date
  const joinedEl = document.querySelector('[data-testid="UserJoinDate"]');
  let joined = joinedEl ? joinedEl.innerText.replace(/^joined\s*/i, '').trim() : '';
  if (!joined) {
    document.querySelectorAll('[data-testid="UserProfileHeader_Items"] > span').forEach(span => {
      const t = span.innerText.trim();
      if (t.toLowerCase().includes('joined')) joined = t.replace(/^joined\s*/i, '').trim();
    });
  }

  // Location
  const locationEl = document.querySelector('[data-testid="UserLocation"]');
  const location = locationEl ? locationEl.innerText.trim() : '';

  // Followers / following — target the stat block links, not the follow/unfollow buttons.
  // The stat links live inside [data-testid="UserProfileHeader_Items"] or the profile header nav.
  // Each link's innerText is "1,234\nFollowing" or "56.7K\nFollowers" — split on whitespace to get the count.
  let following = '', followers = '';
  document.querySelectorAll('a[href$="/following"], a[href$="/followers"]').forEach(a => {
    const text = a.innerText.trim();
    const parts = text.split(/\s+/);
    const count = parts[0];
    const label = (parts[1] || '').toLowerCase();
    if (label === 'following') following = count;
    if (label === 'followers') followers = count;
  });

  // Pinned tweet URL
  const pinnedCtx = document.querySelector('[data-testid="socialContext"]');
  let pinnedTweetUrl = '';
  if (pinnedCtx && pinnedCtx.innerText.toLowerCase().includes('pinned')) {
    const pinnedArticle = pinnedCtx.closest('article');
    if (pinnedArticle) {
      const link = pinnedArticle.querySelector('a[href*="/status/"]');
      if (link) pinnedTweetUrl = 'https://x.com' + link.getAttribute('href');
    }
  }

  // Avatar URL
  const avatarImg = document.querySelector('a[href$="/photo"] img, [data-testid="UserAvatar-Container"] img');
  const avatarUrl = avatarImg ? avatarImg.src : '';

  const profile = { display_name: displayName, handle, bio, location, website, joined,
    followers, following, pinned_tweet_url: pinnedTweetUrl, avatar_url: avatarUrl };

  // ── FIRST TWEET BATCH ────────────────────────────────────
  window._collected = window._collected || {};
  const articles = document.querySelectorAll('article[data-testid="tweet"]');

  articles.forEach(article => {
    const socialCtx = article.querySelector('[data-testid="socialContext"]');
    const isPinned = !!(socialCtx && socialCtx.innerText.toLowerCase().includes('pinned'));
    if (socialCtx) {
      const ctxText = socialCtx.innerText.toLowerCase();
      if (ctxText.includes('repost') || ctxText.includes('retweeted')) return;
    }
    const allSpans = article.querySelectorAll('span');
    let isReply = false;
    allSpans.forEach(s => { if (s.innerText && s.innerText.trim().toLowerCase() === 'replying to') isReply = true; });
    if (isReply) return;

    const links = article.querySelectorAll('a[href*="/status/"]');
    let statusPath = '';
    links.forEach(l => { const h = l.getAttribute('href') || ''; if (h.includes('/status/') && !statusPath) statusPath = h; });
    if (!statusPath) return;
    const tweetId = statusPath.split('/status/')[1]?.split('/')[0] || '';
    if (!tweetId || window._collected[tweetId]) return;

    const url = 'https://x.com' + statusPath;
    const authorHandle = statusPath.split('/')[1] || '';
    const textEl = article.querySelector('[data-testid="tweetText"]');
    const text = textEl ? textEl.innerText : '';
    const timeEl = article.querySelector('time');
    const datetime = timeEl ? timeEl.getAttribute('datetime') : '';

    const getCount = (testId) => {
      const el = article.querySelector(`[data-testid="${testId}"]`); if (!el) return 0;
      const label = el.getAttribute('aria-label') || ''; const m = label.match(/([\d,]+)/);
      if (m) return parseInt(m[1].replace(/,/g, ''), 10);
      const inner = el.querySelector('span[data-testid]') || el;
      const num = (inner.innerText || '').trim().replace(/[^0-9]/g, '');
      return num ? parseInt(num, 10) : 0;
    };
    let views = 0;
    const al = article.querySelector('a[href$="/analytics"]');
    if (al) { const m = (al.getAttribute('aria-label') || al.innerText || '').match(/([\d,]+)/); if (m) views = parseInt(m[1].replace(/,/g,''),10); }

    const quotedCard = article.querySelector('[data-testid="quoteTweet"]') || article.querySelector('div[role="blockquote"]');
    let quotedTweetUrl = '';
    if (quotedCard) quotedCard.querySelectorAll('a[href*="/status/"]').forEach(l => { if (!quotedTweetUrl) quotedTweetUrl = 'https://x.com' + l.getAttribute('href'); });

    const mediaUrls = [];
    article.querySelectorAll('[data-testid="tweetPhoto"] img').forEach(img => { if (img.src && !img.src.includes('profile_images')) mediaUrls.push(img.src); });
    article.querySelectorAll('video').forEach(v => { if (v.src) mediaUrls.push(v.src); else if (v.poster) mediaUrls.push(v.poster); });
    article.querySelectorAll('[data-testid="card.layoutSmall.media"] img, [data-testid="card.layoutLarge.media"] img').forEach(img => { if (img.src) mediaUrls.push(img.src); });

    window._collected[tweetId] = { tweet_id: tweetId, author_handle: authorHandle, url, datetime, text, is_pinned: isPinned,
      metrics: { replies: getCount('reply'), retweets: getCount('retweet'), likes: getCount('like'), bookmarks: getCount('bookmark'), views },
      is_quote_tweet: !!quotedCard, quoted_tweet_url: quotedTweetUrl, has_media: mediaUrls.length > 0, media_urls: mediaUrls };
  });

  return JSON.stringify({ profile, collected: Object.keys(window._collected).length });
})()
```

Store the `profile` object. Continue scroll loop with `window._collected` already seeded.

---

## Step 4 — Scroll + extract loop

**Extraction script** (reuse after each scroll — same as the inner loop above but profile section removed):

```javascript
(function() {
  const articles = document.querySelectorAll('article[data-testid="tweet"]');
  articles.forEach(article => {
    const socialCtx = article.querySelector('[data-testid="socialContext"]');
    const isPinned = !!(socialCtx && socialCtx.innerText.toLowerCase().includes('pinned'));
    if (socialCtx) {
      const ctxText = socialCtx.innerText.toLowerCase();
      if (ctxText.includes('repost') || ctxText.includes('retweeted')) return;
    }
    const allSpans = article.querySelectorAll('span');
    let isReply = false;
    allSpans.forEach(s => { if (s.innerText && s.innerText.trim().toLowerCase() === 'replying to') isReply = true; });
    if (isReply) return;

    const links = article.querySelectorAll('a[href*="/status/"]');
    let statusPath = '';
    links.forEach(l => { const h = l.getAttribute('href') || ''; if (h.includes('/status/') && !statusPath) statusPath = h; });
    if (!statusPath) return;
    const tweetId = statusPath.split('/status/')[1]?.split('/')[0] || '';
    if (!tweetId || window._collected[tweetId]) return;

    const url = 'https://x.com' + statusPath;
    const authorHandle = statusPath.split('/')[1] || '';
    const textEl = article.querySelector('[data-testid="tweetText"]');
    const text = textEl ? textEl.innerText : '';
    const timeEl = article.querySelector('time');
    const datetime = timeEl ? timeEl.getAttribute('datetime') : '';

    const getCount = (testId) => {
      const el = article.querySelector(`[data-testid="${testId}"]`); if (!el) return 0;
      const label = el.getAttribute('aria-label') || ''; const m = label.match(/([\d,]+)/);
      if (m) return parseInt(m[1].replace(/,/g, ''), 10);
      const inner = el.querySelector('span[data-testid]') || el;
      const num = (inner.innerText || '').trim().replace(/[^0-9]/g, '');
      return num ? parseInt(num, 10) : 0;
    };
    let views = 0;
    const al = article.querySelector('a[href$="/analytics"]');
    if (al) { const m = (al.getAttribute('aria-label') || al.innerText || '').match(/([\d,]+)/); if (m) views = parseInt(m[1].replace(/,/g,''),10); }

    const quotedCard = article.querySelector('[data-testid="quoteTweet"]') || article.querySelector('div[role="blockquote"]');
    let quotedTweetUrl = '';
    if (quotedCard) quotedCard.querySelectorAll('a[href*="/status/"]').forEach(l => { if (!quotedTweetUrl) quotedTweetUrl = 'https://x.com' + l.getAttribute('href'); });

    const mediaUrls = [];
    article.querySelectorAll('[data-testid="tweetPhoto"] img').forEach(img => { if (img.src && !img.src.includes('profile_images')) mediaUrls.push(img.src); });
    article.querySelectorAll('video').forEach(v => { if (v.src) mediaUrls.push(v.src); else if (v.poster) mediaUrls.push(v.poster); });
    article.querySelectorAll('[data-testid="card.layoutSmall.media"] img, [data-testid="card.layoutLarge.media"] img').forEach(img => { if (img.src) mediaUrls.push(img.src); });

    window._collected[tweetId] = { tweet_id: tweetId, author_handle: authorHandle, url, datetime, text, is_pinned: isPinned,
      metrics: { replies: getCount('reply'), retweets: getCount('retweet'), likes: getCount('like'), bookmarks: getCount('bookmark'), views },
      is_quote_tweet: !!quotedCard, quoted_tweet_url: quotedTweetUrl, has_media: mediaUrls.length > 0, media_urls: mediaUrls };
  });
  return JSON.stringify({ new: 0, total: Object.keys(window._collected).length }); // new count tracked externally
})()
```

**Scroll loop logic:**

```
scroll_position = 0
no_new_count = 0

loop:
  run extraction script → count new additions to window._collected
  if total >= count: break
  if no new tweets this iteration: no_new_count++
  if no_new_count >= 5: break with warning "only found N tweets"
  scroll_position += 1800
  window.scrollTo(0, scroll_position)   ← scroll + extract can be one JS call
  wait ~1s (trivial JS)
```

Keep only the `count` most recent tweets (sorted by datetime descending).

---

## Step 5 — Enrich truncated tweets on a second tab (parallel)

X truncates long tweets in the feed with `…`. Individual tweet pages show full text + accurate bookmarks + better view counts.

**Only run this step if any tweet has `text.endsWith('…')`. Cap at 20 enrichments.**

**Setup (parallel):** While tab A stays on the profile, create **tab B** for enrichment:
- Call `tabs_create_mcp` to open a new tab → this is **tab B**
- Identify all tweet IDs where `text.endsWith('…')` from `window._collected`

**For each truncated tweet** (sequential on tab B):
1. Navigate tab B to `https://x.com/{handle}/status/{tweetId}`
2. Wait ~1s, then run enrichment JS:

```javascript
(function() {
  const path = window.location.pathname;
  let article = null;
  document.querySelectorAll('article[data-testid="tweet"]').forEach(a => {
    if (!article && a.querySelector(`a[href*="${path}"]`)) article = a;
  });
  if (!article) article = document.querySelector('article[data-testid="tweet"]');
  if (!article) return JSON.stringify({ error: 'no article' });

  const textEl = article.querySelector('[data-testid="tweetText"]');
  const text = textEl ? textEl.innerText : '';

  const getCount = (testId) => {
    const el = article.querySelector(`[data-testid="${testId}"]`); if (!el) return 0;
    const label = el.getAttribute('aria-label') || ''; const m = label.match(/([\d,]+)/);
    if (m) return parseInt(m[1].replace(/,/g,''), 10);
    const inner = el.querySelector('span[data-testid]') || el;
    const num = (inner.innerText || '').trim().replace(/[^0-9]/g,'');
    return num ? parseInt(num, 10) : 0;
  };

  let views = 0;
  const al = article.querySelector('a[href$="/analytics"]');
  if (al) { const m = (al.getAttribute('aria-label')||al.innerText||'').match(/([\d,]+)/); if(m) views = parseInt(m[1].replace(/,/g,''),10); }

  return JSON.stringify({
    text,
    metrics: {
      replies: getCount('reply'),
      retweets: getCount('retweet'),
      likes: getCount('like'),
      bookmarks: getCount('bookmark'),
      views
    }
  });
})()
```

3. Update `window._collected[tweetId]` on tab A with the enriched text + metrics.

After all enrichments, close tab B (navigate it away or leave it — tab A is the source of truth).

---

## Step 6 — Export data via console.log

**Do NOT use `JSON.stringify` + textarea for export.** The content filter blocks JSON containing
tweet URLs, image URLs with query strings, and base64-encoded data — all of which appear in a
typical tweet payload. The reliable workaround is `console.log` per tweet, read back via
`read_console_messages`.

**Write to console on tab A:**

```javascript
(function() {
  const all = Object.values(window._collected)
    .sort((a, b) => new Date(b.datetime) - new Date(a.datetime))
    .slice(0, COUNT); // replace COUNT with actual count
  window._all = all; // keep reference for Step 7
  // Profile — re-read from DOM so it's fresh
  const nameEl = document.querySelector('[data-testid="UserName"]');
  const displayName = nameEl ? nameEl.querySelector('span')?.innerText : '';
  const bioEl = document.querySelector('[data-testid="UserDescription"]');
  const bio = bioEl ? bioEl.innerText.replace(/\n/g,' ') : '';
  const websiteEl = document.querySelector('[data-testid="UserUrl"] a');
  const website = websiteEl ? websiteEl.innerText.trim() : '';
  const joinedEl = document.querySelector('[data-testid="UserJoinDate"]');
  const joined = joinedEl ? joinedEl.innerText.replace(/^joined\s*/i,'').trim() : '';
  const locationEl = document.querySelector('[data-testid="UserLocation"]');
  const location = locationEl ? locationEl.innerText.trim() : '';
  let following = '', followers = '';
  document.querySelectorAll('a[href$="/following"], a[href$="/followers"]').forEach(a => {
    const parts = a.innerText.trim().split(/\s+/);
    const label = (parts[1] || '').toLowerCase();
    if (label === 'following') following = parts[0];
    if (label === 'followers') followers = parts[0];
  });
  const profile = { display_name: displayName, bio, location, website, joined, followers, following };
  console.log('[PROFILE]', JSON.stringify(profile));
  all.forEach((t, i) => {
    console.log('[TWEET' + i + ']', JSON.stringify({
      tweet_id: t.tweet_id, author_handle: t.author_handle, datetime: t.datetime,
      text: t.text, is_pinned: t.is_pinned, metrics: t.metrics,
      is_quote_tweet: t.is_quote_tweet, has_media: t.has_media
    }));
  });
  return 'logged profile + ' + all.length + ' tweets';
})()
```

**Read back in one call** using `read_console_messages` with pattern `\[PROFILE\]|\[TWEET`:

```
mcp__claude-in-chrome__read_console_messages(tabId, pattern="\[PROFILE\]|\[TWEET", limit=COUNT+5)
```

Parse each log line: the JSON value starts after the first space following the tag.
Reconstruct `tweet.url` as `https://x.com/{author_handle}/status/{tweet_id}` — no need to log it.

---

## Step 7 — Build output

```json
{
  "meta": {
    "handle": "@{handle}",
    "scraped_at": "{ISO datetime now}",
    "tweet_count": {N},
    "filters_applied": ["no_retweets", "no_replies"]
  },
  "profile": {
    "display_name": "...",
    "handle": "@...",
    "bio": "...",
    "location": "...",
    "website": "...",
    "joined": "...",
    "followers": "...",
    "following": "...",
    "pinned_tweet_url": "...",
    "avatar_url": "..."
  },
  "tweets": [
    {
      "tweet_id": "...",
      "author_handle": "...",
      "url": "...",
      "datetime": "...",
      "text": "...",
      "is_pinned": false,
      "metrics": { "replies": 0, "retweets": 0, "likes": 0, "bookmarks": 0, "views": 0 },
      "is_quote_tweet": false,
      "quoted_tweet_url": "",
      "has_media": false,
      "media_urls": []
    }
  ]
}
```

---

## Step 8 — Write file

Save to: `{cwd}/{handle}_tweets_{YYYY-MM-DD}.json`

Use the Write tool. Confirm path to user.

---

## Step 9 — Print summary table

```
Scraped N tweets from @{handle} → saved to {filename}

  #  Date        Likes   RTs  Views    Preview
  1  2026-04-07  1.2K    342  98K      "not an April Fools joke, we rewrote..."
  2  2026-04-06   847    201  45K      "I want to do a few more of these..."
  ...
```

Format large numbers with K/M suffix. Truncate preview to 60 chars. Mark pinned tweet with `📌`.

---

## Error handling

| Situation | Action |
|-----------|--------|
| Not logged in / login wall | Stop. Tell user to log into X in Chrome first. |
| Profile not found / suspended | Stop. Report it. |
| Fewer tweets than requested | Complete with what's available, note the shortfall. |
| Browser tools unavailable | Remind user to connect the Claude Code Chrome extension. |
| Enrichment tab fails to load | Skip that tweet's enrichment, keep feed-view data. |
