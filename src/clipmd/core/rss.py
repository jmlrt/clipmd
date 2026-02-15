"""RSS/Atom feed handling for clipmd."""

from __future__ import annotations

from typing import TYPE_CHECKING

import feedparser
import httpx

if TYPE_CHECKING:
    from clipmd.config import Config


def parse_rss_feed(content: str, url: str, limit: int = 10) -> list[str]:  # noqa: ARG001
    """Parse RSS/Atom feed and extract article URLs.

    Args:
        content: Feed content (XML).
        url: Feed URL (for resolving relative URLs).
        limit: Maximum number of entries to return.

    Returns:
        List of article URLs.
    """
    feed = feedparser.parse(content)
    urls = []

    for entry in feed.entries[:limit]:
        if link := entry.get("link"):
            urls.append(link)

    return urls


async def fetch_rss_feed(
    feed_url: str,
    config: Config,
    limit: int = 10,
) -> list[str]:
    """Fetch an RSS feed and return article URLs.

    Args:
        feed_url: URL of the RSS/Atom feed.
        config: Application configuration.
        limit: Maximum number of entries.

    Returns:
        List of article URLs from the feed.
    """
    timeout = httpx.Timeout(config.fetch.timeout)
    headers = {"User-Agent": config.fetch.user_agent}

    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        response = await client.get(feed_url, follow_redirects=True)
        response.raise_for_status()
        return parse_rss_feed(response.text, feed_url, limit)


def validate_rss_mode(urls: list[str]) -> tuple[bool, str | None]:
    """Validate RSS mode requirements (exactly one URL).

    Args:
        urls: List of URLs to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if len(urls) != 1:
        return False, "RSS mode requires exactly one feed URL"
    return True, None
