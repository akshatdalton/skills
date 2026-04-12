#!/usr/bin/env python3
"""
magnetx-engage skill implementation.
Handles Mode 1 (daily session) and Mode 2 (reply coach) for @aksenHQ X engagement.
"""

import json
import sys
from datetime import datetime
from collections import defaultdict, Counter
from typing import Optional

# Load accounts.json
ACCOUNTS_PATH = "/Users/akshat.v/.claude/skills/magnetx-engage/accounts.json"


def load_accounts() -> dict:
    """Load target accounts from accounts.json."""
    try:
        with open(ACCOUNTS_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {ACCOUNTS_PATH} not found")
        sys.exit(1)


def calculate_engagement_rate(tweets: list) -> float:
    """Calculate avg engagement rate: (likes + replies + retweets) / views."""
    if not tweets:
        return 0.0

    total_engagement_rate = 0.0
    valid_tweets = 0

    for tweet in tweets:
        views = tweet.get("views", 0) or 1  # Avoid division by zero
        engagement = (
            tweet.get("likes", 0) +
            tweet.get("replies", 0) +
            tweet.get("retweets", 0)
        )
        if views > 0:
            total_engagement_rate += engagement / views
            valid_tweets += 1

    return total_engagement_rate / valid_tweets if valid_tweets > 0 else 0.0


def calculate_reply_back_signal(tweets: list) -> float:
    """Calculate % of recent posts where replies > 0."""
    if not tweets:
        return 0.0
    posts_with_replies = sum(1 for t in tweets if t.get("replies", 0) > 0)
    return (posts_with_replies / len(tweets)) * 100


def extract_peak_posting_hour(tweets: list) -> Optional[int]:
    """Extract most frequent posting hour from tweet datetimes (UTC)."""
    if not tweets:
        return None

    hours = []
    for tweet in tweets:
        datetime_str = tweet.get("datetime")
        if datetime_str:
            try:
                # Parse ISO 8601 datetime
                dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
                hours.append(dt.hour)
            except ValueError:
                pass

    if hours:
        hour_counter = Counter(hours)
        return hour_counter.most_common(1)[0][0]
    return None


def rank_accounts(accounts: list, tweet_data: dict) -> list:
    """Rank accounts by engagement rate and reply-back signal."""
    ranked = []

    for account in accounts:
        handle = account["handle"]
        if handle not in tweet_data:
            continue

        tweets = tweet_data[handle]
        engagement_rate = calculate_engagement_rate(tweets)
        reply_back_signal = calculate_reply_back_signal(tweets)
        peak_hour = extract_peak_posting_hour(tweets)

        # Rank by: engagement_rate (0.6 weight) + reply_back_signal (0.4 weight)
        score = (engagement_rate * 100) * 0.6 + reply_back_signal * 0.4

        ranked.append({
            "account": account,
            "tweets": tweets,
            "engagement_rate": engagement_rate,
            "reply_back_signal": reply_back_signal,
            "peak_hour": peak_hour,
            "score": score
        })

    # Sort by score descending
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked


def surface_top_posts(ranked_accounts: list, num_posts: int = 5) -> list:
    """Surface top N posts across ranked accounts."""
    top_posts = []
    posts_collected = 0
    account_idx = 0

    while posts_collected < num_posts and account_idx < len(ranked_accounts):
        account_data = ranked_accounts[account_idx]
        tweets = account_data["tweets"]

        # Get most recent tweet with good engagement
        for tweet in tweets:
            if posts_collected >= num_posts:
                break

            replies = tweet.get("replies", 0)
            if replies > 0:  # Filter for posts with engagement
                top_posts.append({
                    "account": account_data["account"],
                    "tweet": tweet,
                    "engagement_rate": account_data["engagement_rate"],
                    "reply_back_signal": account_data["reply_back_signal"],
                    "account_score": account_data["score"]
                })
                posts_collected += 1

        account_idx += 1

    return top_posts


def mode1_daily_session(tweet_data: dict) -> None:
    """Mode 1: Daily engagement session."""
    accounts = load_accounts()["accounts"]

    print("\n🧲 YOUR DAILY ENGAGEMENT TARGETS (5 posts)\n")

    # Rank accounts
    ranked = rank_accounts(accounts, tweet_data)

    # Surface top 5 posts
    top_posts = surface_top_posts(ranked, num_posts=5)

    for idx, post_data in enumerate(top_posts, 1):
        account = post_data["account"]
        tweet = post_data["tweet"]
        engagement_rate = post_data["engagement_rate"]
        reply_back = post_data["reply_back_signal"]

        handle = account["handle"]
        name = account["name"]
        followers = tweet.get("followers", "N/A")

        # Suggested angle (thinking starter)
        reason = account.get("reason", "Active builder in your niche")

        print(f"{idx}. [@{handle}] — {followers} followers, {engagement_rate:.1%} engagement")
        print(f"   📄 Post: \"{tweet.get('text', '')[:100]}...\"")
        print(f"   🔗 {tweet.get('url', 'N/A')}")
        print(f"   Why: {reason} | {reply_back:.0f}% reply-back rate")
        print(f"   Angle to explore: [Your thinking direction here]")
        print()

    # Account scores summary
    print("⏱️ Account scores (engagement rate + reply-back signal):")
    for idx, account_data in enumerate(ranked[:5], 1):
        handle = account_data["account"]["handle"]
        rate = account_data["engagement_rate"]
        reply_back = account_data["reply_back_signal"]
        print(f"   {handle}: {rate:.1%} engagement, {reply_back:.0f}% reply-back")


def mode2_reply_coach(tweet_url: str, optional_handle: Optional[str] = None) -> None:
    """Mode 2: Reply coach for a specific tweet."""
    print(f"\n🎯 REPLY ANGLES FOR {tweet_url}\n")
    print("Mode 2 (Reply Coach) requires manual tweet input or browser scraping.")
    print("Implement tweet decode + angle generation here.")
    print(f"Tweet URL: {tweet_url}")
    if optional_handle:
        print(f"Account context: @{optional_handle}")


def main():
    """Entry point for magnetx-engage skill."""
    if len(sys.argv) == 1:
        # Mode 1: Daily session
        print("Mode 1: Daily Session (requires tweet_data from scrape-x-profile)")
        print("Implementation: Pass tweet_data dict from scrape-x-profile skill")
        # In actual use, tweet_data would be passed from scrape-x-profile
        mode1_daily_session({})
    elif len(sys.argv) >= 2:
        # Mode 2: Reply coach
        tweet_url = sys.argv[1]
        optional_handle = sys.argv[2] if len(sys.argv) > 2 else None
        mode2_reply_coach(tweet_url, optional_handle)


if __name__ == "__main__":
    main()
