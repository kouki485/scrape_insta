from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator


def format_duration(seconds: float) -> str:
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, sec = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m{sec:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m{sec:02d}s"


@contextmanager
def step(logger, label: str) -> Iterator[None]:
    """Log start, end, and elapsed time of a pipeline step."""
    logger.info("▶ %s …", label)
    start = time.monotonic()
    try:
        yield
    except Exception:
        elapsed = time.monotonic() - start
        logger.error("✗ %s (failed after %s)", label, format_duration(elapsed))
        raise
    else:
        elapsed = time.monotonic() - start
        logger.info("✓ %s (%s)", label, format_duration(elapsed))


class TotalTimer:
    def __init__(self):
        self._start = time.monotonic()

    def elapsed(self) -> float:
        return time.monotonic() - self._start

    def elapsed_str(self) -> str:
        return format_duration(self.elapsed())
