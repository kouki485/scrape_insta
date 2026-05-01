from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.config import load_config
from src.excel import ExcelStore
from src.filter import filter_candidates
from src.profile import parse_profile_items
from src.scraper import parse_hashtag_items

logger = logging.getLogger("asakusa-leads")


FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def _setup_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=logging.INFO,
    )


def _dry_run() -> int:
    """Run pipeline against fixtures without calling Apify. Writes to a tmp xlsx."""
    cfg = load_config(require_secrets=False)
    now = datetime.now(timezone.utc)
    cutoff = datetime(2020, 1, 1, tzinfo=timezone.utc)

    hashtag_items = json.loads((FIXTURES_DIR / "apify_hashtag_sample.json").read_text("utf-8"))
    profile_items = json.loads((FIXTURES_DIR / "apify_profile_sample.json").read_text("utf-8"))

    posts = parse_hashtag_items(hashtag_items, matched_hashtag="asakusa", cutoff=cutoff)
    profiles = parse_profile_items(profile_items)

    dry_path = Path("output/asakusa_leads.dry-run.xlsx")
    store = ExcelStore(dry_path)
    seen = store.load_seen(window_days=cfg.filters.dedupe_window_days, now=now)

    leads = filter_candidates(
        posts=posts,
        profiles=profiles,
        seen_users=seen,
        config=cfg.filters,
        fetched_at=now,
    )

    appended = store.append_leads(leads)
    store.update_seen([lead.username for lead in leads], now=now)
    store.save()

    logger.info("Dry-run produced %d leads (fixtures, no API calls):", len(leads))
    for lead in leads:
        logger.info(
            "  - @%s | %d followers | %s | %s",
            lead.username,
            lead.follower_count,
            lead.bio_lang,
            lead.latest_post_url,
        )
    logger.info("Wrote %d rows to %s", appended, dry_path)
    return 0


def _live_run() -> int:
    from src.profile import fetch_profiles
    from src.scraper import fetch_recent_posts

    cfg = load_config(require_secrets=True)
    now = datetime.now(timezone.utc)

    store = ExcelStore(cfg.excel.output_path)
    seen = store.load_seen(window_days=cfg.filters.dedupe_window_days, now=now)
    logger.info("Loaded %d already-seen users (window=%dd)", len(seen), cfg.filters.dedupe_window_days)

    logger.info("Scraping %d hashtags from Apify...", len(cfg.scraper.hashtags))
    posts = fetch_recent_posts(
        apify_token=cfg.secrets.apify_token,
        hashtags=cfg.scraper.hashtags,
        posts_per_hashtag=cfg.scraper.posts_per_hashtag,
        lookback_hours=cfg.scraper.lookback_hours,
        now=now,
    )
    logger.info("Got %d posts within last %dh", len(posts), cfg.scraper.lookback_hours)

    candidate_usernames = {p.owner_username for p in posts} - seen
    logger.info("Fetching %d unique profiles...", len(candidate_usernames))
    profiles = fetch_profiles(
        apify_token=cfg.secrets.apify_token,
        usernames=candidate_usernames,
    )

    leads = filter_candidates(
        posts=posts,
        profiles=profiles,
        seen_users=seen,
        config=cfg.filters,
        fetched_at=now,
    )
    logger.info("Filter produced %d leads", len(leads))

    appended = store.append_leads(leads)
    store.update_seen([lead.username for lead in leads], now=now)
    store.save()
    logger.info("Wrote %d new rows to %s", appended, store.path)
    return 0


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    parser = argparse.ArgumentParser(description="Asakusa influencer-leads collector")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run pipeline against local fixtures, no Apify calls.",
    )
    args = parser.parse_args(argv)

    try:
        if args.dry_run:
            return _dry_run()
        return _live_run()
    except Exception:
        logger.exception("Pipeline failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
