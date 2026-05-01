from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from src.config import FilterConfig
from src.lang import is_japanese
from src.profile import Profile
from src.scraper import Post


@dataclass(frozen=True)
class Lead:
    fetched_at: datetime
    username: str
    full_name: str
    follower_count: int
    following_count: int
    bio: str
    bio_lang: str
    latest_post_url: str
    latest_post_caption: str
    caption_lang: str
    post_timestamp: datetime
    matched_hashtag: str
    profile_url: str


def _classify_lang(text: str) -> str:
    return "ja" if is_japanese(text) else "non-ja"


def _passes_followers(profile: Profile, cfg: FilterConfig) -> bool:
    return cfg.min_followers <= profile.followers_count <= cfg.max_followers


def _passes_language(post: Post, profile: Profile, cfg: FilterConfig) -> bool:
    if not cfg.exclude_japanese:
        return True
    return not is_japanese(post.caption) and not is_japanese(profile.biography)


def _pick_latest_post_per_user(posts: Iterable[Post]) -> dict[str, Post]:
    latest: dict[str, Post] = {}
    for post in posts:
        existing = latest.get(post.owner_username)
        if existing is None or post.timestamp > existing.timestamp:
            latest[post.owner_username] = post
    return latest


def filter_candidates(
    *,
    posts: Iterable[Post],
    profiles: dict[str, Profile],
    seen_users: set[str],
    config: FilterConfig,
    fetched_at: datetime,
) -> list[Lead]:
    latest_post_per_user = _pick_latest_post_per_user(posts)

    leads: list[Lead] = []
    for username, post in latest_post_per_user.items():
        if username in seen_users:
            continue
        profile = profiles.get(username)
        if profile is None:
            continue
        if not _passes_followers(profile, config):
            continue
        if not _passes_language(post, profile, config):
            continue
        leads.append(
            Lead(
                fetched_at=fetched_at,
                username=username,
                full_name=profile.full_name,
                follower_count=profile.followers_count,
                following_count=profile.follows_count,
                bio=profile.biography,
                bio_lang=_classify_lang(profile.biography),
                latest_post_url=post.url,
                latest_post_caption=post.caption,
                caption_lang=_classify_lang(post.caption),
                post_timestamp=post.timestamp,
                matched_hashtag=post.matched_hashtag,
                profile_url=profile.url,
            )
        )
    leads.sort(key=lambda lead: lead.follower_count, reverse=True)
    return leads
