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

## Step 1 — Load browser tools

Use ToolSearch to load each tool before calling it (the browser tools are deferred):

```
ToolSearch: select:mcp__claude-in-chrome__tabs_context_mcp
ToolSearch: select:mcp__claude-in-chrome__navigate
ToolSearch: select:mcp__claude-in-chrome__javascript_tool
```

---

## Step 2 — Open profile

1. Call `tabs_context_mcp` with `createIfEmpty: true` to get a tab ID.
2. Navigate to `https://x.com/{handle}` on that tab.
3. Wait ~1s (run a trivial JS like `document.title`) to confirm the page loaded and the user is logged in. If the page redirects to login, stop and tell the user they need to be logged into X in Chrome.

---

## Step 3 — Scrape loop

Run the extraction script below. Repeat the scroll-then-extract loop until you have `count` qualifying tweets OR you've scrolled 30 times without new results (give up with a warning).

**Extraction script** — run via `javascript_tool` after each scroll:

```javascript
(function() {
  const articles = document.querySelectorAll('article[data-testid="tweet"]');
  const results = [];

  articles.forEach(article => {
    // --- FILTER: skip retweets ---
    const socialCtx = article.querySelector('[data-testid="socialContext"]');
    if (socialCtx) {
      const ctxText = socialCtx.innerText.toLowerCase();
      if (ctxText.includes('repost') || ctxText.includes('retweeted')) return;
    }

    // --- FILTER: skip replies (tweets that start with "Replying to") ---
    const replyCtx = article.querySelector('[data-testid="reply"]');
    // The actual reply-to indicator is a row above the tweet text
    const replyToRow = article.querySelector('div[data-testid="User-Name"] + div > div > span');
    // More reliable: check for the "Replying to @handle" meta row
    const allSpans = article.querySelectorAll('span');
    let isReply = false;
    allSpans.forEach(s => {
      if (s.innerText && s.innerText.trim().toLowerCase() === 'replying to') isReply = true;
    });
    if (isReply) return;

    // --- URL & tweet ID ---
    const links = article.querySelectorAll('a[href*="/status/"]');
    let statusPath = '';
    links.forEach(l => {
      const href = l.getAttribute('href') || '';
      if (href.includes('/status/') && !statusPath) statusPath = href;
    });
    if (!statusPath) return; // can't identify tweet, skip
    const url = 'https://x.com' + statusPath;
    const tweetId = statusPath.split('/status/')[1]?.split('/')[0] || '';
    const authorHandle = statusPath.split('/')[1] || '';

    // --- Text ---
    const textEl = article.querySelector('[data-testid="tweetText"]');
    const text = textEl ? textEl.innerText : '';

    // --- Datetime ---
    const timeEl = article.querySelector('time');
    const datetime = timeEl ? timeEl.getAttribute('datetime') : '';

    // --- Metrics (aria-label contains the count) ---
    const getCount = (testId) => {
      const el = article.querySelector(`[data-testid="${testId}"]`);
      if (!el) return 0;
      const label = el.getAttribute('aria-label') || '';
      const match = label.match(/([\d,]+)/);
      if (match) return parseInt(match[1].replace(/,/g, ''), 10);
      // fallback: read visible text inside the button
      const inner = el.querySelector('span[data-testid]') || el;
      const num = (inner.innerText || '').trim().replace(/[^0-9]/g, '');
      return num ? parseInt(num, 10) : 0;
    };

    // --- Views (analytics link) ---
    let views = 0;
    const analyticsLink = article.querySelector('a[href$="/analytics"]');
    if (analyticsLink) {
      const label = analyticsLink.getAttribute('aria-label') || analyticsLink.innerText || '';
      const match = label.match(/([\d,]+)/);
      if (match) views = parseInt(match[1].replace(/,/g, ''), 10);
    }

    // --- Quote tweet ---
    const quotedCard = article.querySelector('[data-testid="quoteTweet"]') ||
                       article.querySelector('div[role="blockquote"]');
    const isQuoteTweet = !!quotedCard;
    let quotedTweetUrl = '';
    if (quotedCard) {
      const qLinks = quotedCard.querySelectorAll('a[href*="/status/"]');
      qLinks.forEach(l => {
        if (!quotedTweetUrl) quotedTweetUrl = 'https://x.com' + l.getAttribute('href');
      });
    }

    // --- Media ---
    const mediaUrls = [];
    article.querySelectorAll('[data-testid="tweetPhoto"] img').forEach(img => {
      if (img.src && !img.src.includes('profile_images')) mediaUrls.push(img.src);
    });
    article.querySelectorAll('video').forEach(v => {
      if (v.src) mediaUrls.push(v.src);
      // poster image as fallback
      else if (v.poster) mediaUrls.push(v.poster);
    });
    // Card media (link previews with images)
    article.querySelectorAll('[data-testid="card.layoutSmall.media"] img, [data-testid="card.layoutLarge.media"] img').forEach(img => {
      if (img.src) mediaUrls.push(img.src);
    });

    results.push({
      tweet_id: tweetId,
      author_handle: authorHandle,
      url,
      datetime,
      text,
      metrics: {
        replies: getCount('reply'),
        retweets: getCount('retweet'),
        likes: getCount('like'),
        bookmarks: getCount('bookmark'),
        views,
      },
      is_quote_tweet: isQuoteTweet,
      quoted_tweet_url: quotedTweetUrl,
      has_media: mediaUrls.length > 0,
      media_urls: mediaUrls,
    });
  });

  return JSON.stringify(results);
})()
```

**Scroll loop logic:**

```
collected = {} (keyed by tweet_id to deduplicate)
scroll_position = 0
no_new_count = 0

loop:
  run extraction script → parse JSON → merge into collected (skip dupes)
  if len(collected) >= count: break
  if no new tweets added this iteration: no_new_count++
  if no_new_count >= 5: break with warning "only found N tweets"
  scroll_position += 1800
  javascript: window.scrollTo(0, scroll_position)
  wait ~1s (run trivial JS to let page render)
```

Keep only the `count` most recent tweets (sorted by datetime descending) from `collected`.

---

## Step 4 — Build output

Construct the final data structure:

```json
{
  "meta": {
    "handle": "@{handle}",
    "scraped_at": "{ISO datetime now}",
    "tweet_count": {N},
    "filters_applied": ["no_retweets", "no_replies"]
  },
  "tweets": [ ...sorted by datetime descending... ]
}
```

---

## Step 5 — Write file

Save to: `{cwd}/{handle}_tweets_{YYYY-MM-DD}.json`

Use the Write tool. Confirm the path to the user.

---

## Step 6 — Print summary table

Print a compact summary so the user can spot-check:

```
Scraped N tweets from @{handle} → saved to {filename}

  #  Date        Likes   RTs  Views    Preview
  1  2026-04-07  1.2K    342  98K      "not an April Fools joke, we rewrote..."
  2  2026-04-06   847    201  45K      "I want to do a few more of these..."
  ...
```

Format large numbers with K/M suffix for readability. Truncate preview to 60 chars.

---

## Error handling

| Situation | Action |
|-----------|--------|
| Not logged in / login wall | Stop. Tell user to log into X in Chrome first. |
| Profile not found / suspended | Stop. Report it. |
| Fewer tweets than requested | Complete with what's available, note the shortfall. |
| Browser tools unavailable | Remind user to connect the Claude Code Chrome extension. |
