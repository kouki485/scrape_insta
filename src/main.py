from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from tqdm import tqdm

from src.config import load_config
from src.excel import ExcelStore
from src.filter import filter_candidates
from src.profile import parse_profile_items
from src.progress import TotalTimer, step
from src.scraper import parse_hashtag_items

logger = logging.getLogger("asakusa-leads")


FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def _setup_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=logging.INFO,
    )


def _dry_run() -> int:
    timer = TotalTimer()
    logger.info("=== DRY-RUN START (%s) ===", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    cfg = load_config(require_secrets=False)
    now = datetime.now(timezone.utc)
    cutoff = datetime(2020, 1, 1, tzinfo=timezone.utc)

    with step(logger, "Loading fixtures"):
        hashtag_items = json.loads((FIXTURES_DIR / "apify_hashtag_sample.json").read_text("utf-8"))
        profile_items = json.loads((FIXTURES_DIR / "apify_profile_sample.json").read_text("utf-8"))
        posts = parse_hashtag_items(hashtag_items, matched_hashtag="asakusa", cutoff=cutoff)
        profiles = parse_profile_items(profile_items)

    dry_path = Path("output/asakusa_leads.dry-run.xlsx")
    with step(logger, f"Opening {dry_path}"):
        store = ExcelStore(dry_path)
        seen = store.load_seen(window_days=cfg.filters.dedupe_window_days, now=now)

    with step(logger, "Filtering candidates"):
        leads = filter_candidates(
            posts=posts,
            profiles=profiles,
            seen_users=seen,
            config=cfg.filters,
            fetched_at=now,
        )

    with step(logger, f"Writing {len(leads)} rows"):
        appended = store.append_leads(leads)
        store.update_seen([lead.username for lead in leads], now=now)
        store.save()

    logger.info("=== DRY-RUN DONE: %d leads, total %s ===", appended, timer.elapsed_str())
    for lead in leads:
        logger.info(
            "  - @%s | %d followers | %s | %s",
            lead.username,
            lead.follower_count,
            lead.bio_lang,
            lead.latest_post_url,
        )
    return 0


def _live_run() -> int:
    from src.profile import fetch_profiles
    from src.scraper import fetch_recent_posts

    timer = TotalTimer()
    logger.info("=== LIVE-RUN START (%s) ===", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    cfg = load_config(require_secrets=True)
    now = datetime.now(timezone.utc)

    with step(logger, "Opening Excel + loading seen_users"):
        store = ExcelStore(cfg.excel.output_path)
        seen = store.load_seen(window_days=cfg.filters.dedupe_window_days, now=now)
        logger.info(
            "  loaded %d already-seen users (window=%dd)",
            len(seen),
            cfg.filters.dedupe_window_days,
        )

    posts = []
    with step(logger, f"Scraping {len(cfg.scraper.hashtags)} hashtags via Apify"):
        progress = tqdm(
            total=len(cfg.scraper.hashtags),
            desc="hashtags",
            unit="tag",
            ncols=88,
            leave=True,
        )
        try:
            def _bump(tag: str, count: int) -> None:
                progress.set_postfix_str(f"#{tag} +{count}")
                progress.update(1)

            posts = fetch_recent_posts(
                apify_token=cfg.secrets.apify_token,
                hashtags=cfg.scraper.hashtags,
                posts_per_hashtag=cfg.scraper.posts_per_hashtag,
                lookback_hours=cfg.scraper.lookback_hours,
                now=now,
                on_hashtag_done=_bump,
            )
        finally:
            progress.close()
        logger.info("  → %d posts within last %dh", len(posts), cfg.scraper.lookback_hours)

    candidate_usernames = {p.owner_username for p in posts} - seen
    profiles = {}
    with step(logger, f"Fetching {len(candidate_usernames)} profiles via Apify"):
        # Apify processes profiles as one batch; show indeterminate spinner-style progress.
        with tqdm(
            total=None,
            desc="profiles",
            unit="users",
            ncols=88,
            bar_format="{desc}: {n_fmt} {unit} [{elapsed}]",
        ) as bar:
            bar.update(0)
            profiles = fetch_profiles(
                apify_token=cfg.secrets.apify_token,
                usernames=candidate_usernames,
            )
            bar.update(len(profiles))
        logger.info("  → got %d profiles", len(profiles))

    with step(logger, "Filtering candidates"):
        leads = filter_candidates(
            posts=posts,
            profiles=profiles,
            seen_users=seen,
            config=cfg.filters,
            fetched_at=now,
        )
        logger.info("  → %d leads passed filter", len(leads))

    with step(logger, f"Writing {len(leads)} rows to {store.path}"):
        appended = store.append_leads(leads)
        store.update_seen([lead.username for lead in leads], now=now)
        store.save()

    logger.info(
        "=== LIVE-RUN DONE: %d new leads, total %s ===",
        appended,
        timer.elapsed_str(),
    )
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
