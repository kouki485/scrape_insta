from __future__ import annotations

import re
from functools import lru_cache

from lingua import Language, LanguageDetectorBuilder

# Asian-script-heavy languages help lingua disambiguate JA from ZH/KO efficiently.
_LANGUAGES = (
    Language.JAPANESE,
    Language.CHINESE,
    Language.KOREAN,
    Language.ENGLISH,
    Language.SPANISH,
    Language.FRENCH,
    Language.GERMAN,
    Language.PORTUGUESE,
    Language.RUSSIAN,
    Language.THAI,
    Language.VIETNAMESE,
    Language.INDONESIAN,
    Language.ITALIAN,
    Language.ARABIC,
    Language.HINDI,
    Language.TURKISH,
)

_URL_RE = re.compile(r"https?://\S+")
_HASHTAG_RE = re.compile(r"#\w+")
_MENTION_RE = re.compile(r"@\w+")


@lru_cache(maxsize=1)
def _detector():
    return LanguageDetectorBuilder.from_languages(*_LANGUAGES).build()


def _strip_noise(text: str) -> str:
    text = _URL_RE.sub(" ", text)
    text = _HASHTAG_RE.sub(" ", text)
    text = _MENTION_RE.sub(" ", text)
    return text.strip()


def is_japanese(text: str) -> bool:
    cleaned = _strip_noise(text or "")
    if not cleaned or not any(c.isalpha() for c in cleaned):
        return False
    detected = _detector().detect_language_of(cleaned)
    return detected == Language.JAPANESE
