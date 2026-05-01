from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv


@dataclass(frozen=True)
class FilterConfig:
    min_followers: int
    max_followers: int
    exclude_japanese: bool
    dedupe_window_days: int


@dataclass(frozen=True)
class ScraperConfig:
    posts_per_hashtag: int
    lookback_hours: int
    location_id: str
    hashtags: tuple[str, ...]


@dataclass(frozen=True)
class ExcelConfig:
    output_path: str


@dataclass(frozen=True)
class Secrets:
    apify_token: str


@dataclass(frozen=True)
class Config:
    filters: FilterConfig
    scraper: ScraperConfig
    excel: ExcelConfig
    secrets: Secrets


def load_config(
    config_path: Path | str = "config.yml",
    *,
    require_secrets: bool = True,
) -> Config:
    load_dotenv()

    raw = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))

    secrets = Secrets(apify_token=os.environ.get("APIFY_TOKEN", ""))

    if require_secrets and not secrets.apify_token:
        raise RuntimeError("Missing required environment variable: APIFY_TOKEN")

    return Config(
        filters=FilterConfig(**raw["filters"]),
        scraper=ScraperConfig(
            posts_per_hashtag=raw["scraper"]["posts_per_hashtag"],
            lookback_hours=raw["scraper"]["lookback_hours"],
            location_id=str(raw["scraper"]["location_id"]),
            hashtags=tuple(raw["scraper"]["hashtags"]),
        ),
        excel=ExcelConfig(output_path=raw["excel"]["output_path"]),
        secrets=secrets,
    )
