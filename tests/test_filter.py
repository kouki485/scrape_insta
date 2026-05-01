from datetime import datetime, timedelta, timezone

from src.config import FilterConfig
from src.filter import filter_candidates
from src.profile import Profile
from src.scraper import Post

FETCHED_AT = datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc)
DEFAULT_CFG = FilterConfig(
    min_followers=3000,
    max_followers=500_000,
    exclude_japanese=True,
    dedupe_window_days=7,
)


def _post(username: str, caption: str, hashtag: str = "asakusa", offset_min: int = 0) -> Post:
    base = datetime(2026, 5, 1, 6, 30, tzinfo=timezone.utc)
    return Post(
        post_id=f"id_{username}_{offset_min}",
        shortcode=f"sc_{username}",
        url=f"https://instagram.com/p/{username}_{offset_min}",
        caption=caption,
        timestamp=base + timedelta(minutes=offset_min),
        owner_username=username,
        owner_full_name=username,
        matched_hashtag=hashtag,
    )


def _profile(username: str, followers: int, bio: str) -> Profile:
    return Profile(
        username=username,
        full_name=username,
        biography=bio,
        followers_count=followers,
        follows_count=500,
        url=f"https://instagram.com/{username}",
    )


def test_keeps_foreign_user_with_enough_followers():
    posts = [_post("taylor_travels", "Sunrise at Sensoji was magical")]
    profiles = {
        "taylor_travels": _profile("taylor_travels", 12500, "NYC travel blogger 🌍"),
    }
    leads = filter_candidates(
        posts=posts,
        profiles=profiles,
        seen_users=set(),
        config=DEFAULT_CFG,
        fetched_at=FETCHED_AT,
    )
    assert len(leads) == 1
    assert leads[0].username == "taylor_travels"
    assert leads[0].caption_lang == "non-ja"
    assert leads[0].bio_lang == "non-ja"


def test_drops_user_with_japanese_caption():
    posts = [_post("yamada", "今日は浅草寺に行ってきました")]
    profiles = {"yamada": _profile("yamada", 8000, "Tokyo photographer")}
    leads = filter_candidates(
        posts=posts,
        profiles=profiles,
        seen_users=set(),
        config=DEFAULT_CFG,
        fetched_at=FETCHED_AT,
    )
    assert leads == []


def test_drops_user_with_japanese_bio_even_if_caption_english():
    posts = [_post("hybrid_user", "Visiting Sensoji today, very nice")]
    profiles = {"hybrid_user": _profile("hybrid_user", 8000, "東京在住のフォトグラファー📷")}
    leads = filter_candidates(
        posts=posts,
        profiles=profiles,
        seen_users=set(),
        config=DEFAULT_CFG,
        fetched_at=FETCHED_AT,
    )
    assert leads == []


def test_drops_user_below_min_followers():
    posts = [_post("smol", "Tokyo trip is amazing")]
    profiles = {"smol": _profile("smol", 250, "Random tourist")}
    leads = filter_candidates(
        posts=posts,
        profiles=profiles,
        seen_users=set(),
        config=DEFAULT_CFG,
        fetched_at=FETCHED_AT,
    )
    assert leads == []


def test_drops_user_above_max_followers():
    posts = [_post("celeb", "Tokyo trip was amazing")]
    profiles = {"celeb": _profile("celeb", 2_000_000, "Global megastar")}
    leads = filter_candidates(
        posts=posts,
        profiles=profiles,
        seen_users=set(),
        config=DEFAULT_CFG,
        fetched_at=FETCHED_AT,
    )
    assert leads == []


def test_excludes_already_seen_user():
    posts = [_post("repeat", "Sensoji again, love it")]
    profiles = {"repeat": _profile("repeat", 10_000, "Travel content creator")}
    leads = filter_candidates(
        posts=posts,
        profiles=profiles,
        seen_users={"repeat"},
        config=DEFAULT_CFG,
        fetched_at=FETCHED_AT,
    )
    assert leads == []


def test_picks_latest_post_when_user_has_multiple():
    posts = [
        _post("multi", "Earlier post", offset_min=0),
        _post("multi", "Later post here", offset_min=30),
    ]
    profiles = {"multi": _profile("multi", 5000, "Travel vlogger")}
    leads = filter_candidates(
        posts=posts,
        profiles=profiles,
        seen_users=set(),
        config=DEFAULT_CFG,
        fetched_at=FETCHED_AT,
    )
    assert len(leads) == 1
    assert leads[0].latest_post_caption == "Later post here"


def test_skips_user_without_profile_data():
    posts = [_post("ghost", "Some caption")]
    leads = filter_candidates(
        posts=posts,
        profiles={},
        seen_users=set(),
        config=DEFAULT_CFG,
        fetched_at=FETCHED_AT,
    )
    assert leads == []


def test_results_sorted_by_follower_count_descending():
    posts = [
        _post("small_creator", "Tokyo trip!"),
        _post("big_creator", "Sensoji visit was great"),
        _post("mid_creator", "Loving Asakusa today"),
    ]
    profiles = {
        "small_creator": _profile("small_creator", 4_000, "EN bio"),
        "big_creator": _profile("big_creator", 80_000, "EN bio"),
        "mid_creator": _profile("mid_creator", 15_000, "EN bio"),
    }
    leads = filter_candidates(
        posts=posts,
        profiles=profiles,
        seen_users=set(),
        config=DEFAULT_CFG,
        fetched_at=FETCHED_AT,
    )
    assert [lead.username for lead in leads] == ["big_creator", "mid_creator", "small_creator"]
