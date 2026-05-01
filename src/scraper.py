from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from apify_client import ApifyClient

HASHTAG_ACTOR = "apify/instagram-hashtag-scraper"


@dataclass(frozen=True)
class Post:
    post_id: str
    shortcode: str
    url: str
    caption: str
    timestamp: datetime
    owner_username: str
    owner_full_name: str
    matched_hashtag: str


def _parse_timestamp(raw: str) -> datetime:
    # Apify returns "2026-04-30T22:14:00.000Z"
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def parse_hashtag_items(
    items: Iterable[dict],
    matched_hashtag: str,
    *,
    cutoff: datetime,
) -> list[Post]:
    posts: list[Post] = []
    for item in items:
        timestamp_raw = item.get("timestamp")
        username = item.get("ownerUsername")
        if not timestamp_raw or not username:
            continue
        timestamp = _parse_timestamp(timestamp_raw)
        if timestamp < cutoff:
            continue
        posts.append(
            Post(
                post_id=str(item.get("id", "")),
                shortcode=item.get("shortCode", ""),
                url=item.get("url", ""),
                caption=item.get("caption") or "",
                timestamp=timestamp,
                owner_username=username,
                owner_full_name=item.get("ownerFullName") or "",
                matched_hashtag=matched_hashtag,
            )
        )
    return posts


def fetch_recent_posts(
    *,
    apify_token: str,
    hashtags: Iterable[str],
    posts_per_hashtag: int,
    lookback_hours: int,
    now: datetime | None = None,
) -> list[Post]:
    client = ApifyClient(apify_token)
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(hours=lookback_hours)

    all_posts: list[Post] = []
    for tag in hashtags:
        run_input = {
            "hashtags": [tag],
            "resultsLimit": posts_per_hashtag,
            "resultsType": "posts",
        }
        run = client.actor(HASHTAG_ACTOR).call(run_input=run_input)
        if not run or "defaultDatasetId" not in run:
            continue
        items = client.dataset(run["defaultDatasetId"]).iterate_items()
        all_posts.extend(parse_hashtag_items(items, matched_hashtag=tag, cutoff=cutoff))
    return all_posts
