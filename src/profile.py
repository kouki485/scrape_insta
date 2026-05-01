from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from apify_client import ApifyClient

PROFILE_ACTOR = "apify/instagram-profile-scraper"


@dataclass(frozen=True)
class Profile:
    username: str
    full_name: str
    biography: str
    followers_count: int
    follows_count: int
    url: str


def parse_profile_items(items: Iterable[dict]) -> dict[str, Profile]:
    out: dict[str, Profile] = {}
    for item in items:
        username = item.get("username")
        if not username:
            continue
        out[username] = Profile(
            username=username,
            full_name=item.get("fullName") or "",
            biography=item.get("biography") or "",
            followers_count=int(item.get("followersCount") or 0),
            follows_count=int(item.get("followsCount") or 0),
            url=item.get("url") or f"https://www.instagram.com/{username}/",
        )
    return out


def fetch_profiles(
    *,
    apify_token: str,
    usernames: Iterable[str],
) -> dict[str, Profile]:
    usernames = list({u for u in usernames if u})
    if not usernames:
        return {}
    client = ApifyClient(apify_token)
    run_input = {"usernames": usernames}
    run = client.actor(PROFILE_ACTOR).call(run_input=run_input)
    if not run or "defaultDatasetId" not in run:
        return {}
    items = client.dataset(run["defaultDatasetId"]).iterate_items()
    return parse_profile_items(items)
