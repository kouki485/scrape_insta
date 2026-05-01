import json
from datetime import datetime, timezone
from pathlib import Path

from src.profile import parse_profile_items
from src.scraper import parse_hashtag_items

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_parse_hashtag_items_filters_old_posts():
    raw = _load("apify_hashtag_sample.json")
    cutoff = datetime(2026, 4, 30, 0, 0, tzinfo=timezone.utc)
    posts = parse_hashtag_items(raw, matched_hashtag="asakusa", cutoff=cutoff)

    assert len(posts) == 3
    usernames = {p.owner_username for p in posts}
    assert "old_poster" not in usernames
    assert {"taylor_travels", "yamada_taro", "kim_seoul"} == usernames


def test_parse_hashtag_items_attaches_matched_hashtag():
    raw = _load("apify_hashtag_sample.json")
    cutoff = datetime(2020, 1, 1, tzinfo=timezone.utc)
    posts = parse_hashtag_items(raw, matched_hashtag="아사쿠사", cutoff=cutoff)
    assert all(p.matched_hashtag == "아사쿠사" for p in posts)


def test_parse_hashtag_items_skips_entries_missing_required_fields():
    raw = [
        {"id": "x"},  # missing timestamp + username
        {"timestamp": "2026-05-01T00:00:00.000Z"},  # missing username
        {
            "id": "ok",
            "timestamp": "2026-05-01T00:00:00.000Z",
            "ownerUsername": "ok",
            "url": "https://example.com",
        },
    ]
    cutoff = datetime(2020, 1, 1, tzinfo=timezone.utc)
    posts = parse_hashtag_items(raw, matched_hashtag="x", cutoff=cutoff)
    assert len(posts) == 1
    assert posts[0].owner_username == "ok"


def test_parse_profile_items_extracts_followers_and_bio():
    raw = _load("apify_profile_sample.json")
    profiles = parse_profile_items(raw)
    assert "taylor_travels" in profiles
    assert profiles["taylor_travels"].followers_count == 12500
    assert "Travel blogger" in profiles["taylor_travels"].biography


def test_parse_profile_items_handles_missing_url():
    raw = [{"username": "noUrlUser", "followersCount": 100}]
    profiles = parse_profile_items(raw)
    assert profiles["noUrlUser"].url == "https://www.instagram.com/noUrlUser/"
