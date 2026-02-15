"""Core logic for fetching and processing web content."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import httpx
import trafilatura
from bs4 import BeautifulSoup
from markdownify import markdownify

from clipmd.core.cache import filter_duplicate_urls
from clipmd.core.dates import parse_date_string
from clipmd.core.filepath_utils import get_unique_filepath
from clipmd.core.frontmatter import build_frontmatter
from clipmd.core.rss import fetch_rss_feed, validate_rss_mode
from clipmd.core.sanitizer import sanitize_title_for_filename
from clipmd.core.url_utils import collect_urls

if TYPE_CHECKING:
    from clipmd.config import Config


@dataclass
class FetchResult:
    """Result of fetching a single URL."""

    url: str
    success: bool = False
    title: str | None = None
    author: str | None = None
    published: str | None = None
    description: str | None = None
    content: str | None = None
    filename: str | None = None
    error: str | None = None
    skipped: bool = False
    skip_reason: str | None = None
    final_url: str | None = None  # URL after redirects


@dataclass
class FetchStats:
    """Statistics from fetch operations."""

    total: int = 0
    saved: int = 0
    skipped: int = 0
    errors: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class SavedFile:
    """Information about a saved file."""

    filename: str
    path: Path
    url: str
    title: str | None = None


@dataclass
class ProcessResult:
    """Result of processing fetch results."""

    stats: FetchStats
    saved_files: list[SavedFile] = field(default_factory=list)


def extract_meta_refresh_url(html: str) -> str | None:
    """Extract redirect URL from meta-refresh tag or JavaScript.

    Handles:
    - <meta http-equiv="refresh" content="0;url=...">
    - JavaScript: location='...' or top.location='...'

    Args:
        html: HTML content.

    Returns:
        Redirect URL or None if not found.
    """
    # Try meta refresh tag - handles both:
    # content="0;url=https://..." and content="0.0;https://..."
    meta_pattern = r'<meta[^>]+http-equiv=["\']?refresh["\']?[^>]+content=["\']?[\d.]+[;,]\s*(?:url=)?(https?://[^"\'>]+)'
    meta_match = re.search(meta_pattern, html, re.IGNORECASE)
    if meta_match:
        return meta_match.group(1).strip()

    # Try JavaScript location redirect
    js_patterns = [
        r"(?:top\.)?location\s*=\s*['\"]([^'\"]+)['\"]",
        r"(?:top\.)?location\.href\s*=\s*['\"]([^'\"]+)['\"]",
        r"window\.location\s*=\s*['\"]([^'\"]+)['\"]",
    ]
    for pattern in js_patterns:
        js_match = re.search(pattern, html)
        if js_match:
            url = js_match.group(1).replace("\\/", "/")
            if url.startswith(("http://", "https://")):
                return url

    return None


def extract_metadata_from_html(html: str, url: str) -> dict:  # noqa: ARG001
    """Extract metadata from HTML using BeautifulSoup.

    Args:
        html: HTML content.
        url: Source URL.

    Returns:
        Dictionary with extracted metadata.
    """
    soup = BeautifulSoup(html, "html.parser")
    metadata: dict = {}

    # Title: try various sources
    if og_title := soup.find("meta", property="og:title"):
        metadata["title"] = og_title.get("content", "")
    elif title_tag := soup.find("title"):
        metadata["title"] = title_tag.get_text(strip=True)

    # Author
    if author_meta := soup.find("meta", {"name": "author"}):
        metadata["author"] = author_meta.get("content", "")
    elif og_author := soup.find("meta", property="article:author"):
        metadata["author"] = og_author.get("content", "")

    # Published date
    if pub_meta := soup.find("meta", property="article:published_time"):
        metadata["published"] = pub_meta.get("content", "")
    elif time_tag := soup.find("time", {"datetime": True}):
        metadata["published"] = time_tag.get("datetime", "")

    # Description
    if og_desc := soup.find("meta", property="og:description"):
        metadata["description"] = og_desc.get("content", "")
    elif desc_meta := soup.find("meta", {"name": "description"}):
        metadata["description"] = desc_meta.get("content", "")

    return metadata


def extract_content_trafilatura(html: str, url: str) -> tuple[str, dict]:
    """Extract main content using trafilatura.

    Args:
        html: HTML content.
        url: Source URL.

    Returns:
        Tuple of (markdown content, metadata dict).
    """
    # Extract with metadata
    result = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=True,
        include_links=True,
        output_format="markdown",
    )

    # Get metadata separately
    metadata_result = trafilatura.extract(
        html,
        url=url,
        output_format="json",
    )

    metadata = {}
    if metadata_result:
        try:
            meta_json = json.loads(metadata_result)
            metadata = {
                "title": meta_json.get("title"),
                "author": meta_json.get("author"),
                "date": meta_json.get("date"),
                "description": meta_json.get("description") or meta_json.get("excerpt"),
            }
        except json.JSONDecodeError:
            pass

    return result or "", metadata


def html_to_markdown(html: str) -> str:
    """Convert HTML to markdown.

    Args:
        html: HTML content.

    Returns:
        Markdown content.
    """
    return markdownify(html, heading_style="ATX", strip=["script", "style"])


def generate_filename(
    title: str | None,
    published: str | None,
    url: str,
    date_format: str = "%Y%m%d",
) -> str:
    """Generate a filename from metadata.

    Args:
        title: Article title.
        published: Published date string.
        url: Source URL.
        date_format: Format for date prefix.

    Returns:
        Generated filename without extension.
    """
    # Get date
    date_str = datetime.now().strftime(date_format)
    if published:
        parsed_date = parse_date_string(published)
        if parsed_date:
            date_str = parsed_date.strftime(date_format)

    # Get title
    if title:
        title_part = sanitize_title_for_filename(title)
    else:
        # Use domain as fallback
        parsed = urlparse(url)
        title_part = parsed.netloc.replace(".", "-")

    return f"{date_str}-{title_part}.md"


async def fetch_url(
    client: httpx.AsyncClient,
    url: str,
    config: Config,  # noqa: ARG001
    use_readability: bool = True,
) -> FetchResult:
    """Fetch a single URL and extract content.

    Args:
        client: HTTP client.
        url: URL to fetch.
        config: Application configuration.
        use_readability: Whether to use readability extraction.

    Returns:
        FetchResult with extracted content and metadata.
    """
    result = FetchResult(url=url)

    try:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        html = response.text

        # Track final URL after HTTP redirects
        final_url = str(response.url)

        # Check for meta-refresh or JavaScript redirects
        meta_redirect = extract_meta_refresh_url(html)
        if meta_redirect:
            # Follow the meta-refresh redirect
            try:
                redirect_response = await client.get(meta_redirect, follow_redirects=True)
                redirect_response.raise_for_status()
                html = redirect_response.text
                final_url = str(redirect_response.url)
            except (httpx.HTTPStatusError, httpx.RequestError):
                # If redirect fails, use original content
                pass

        result.final_url = final_url

    except httpx.HTTPStatusError as e:
        result.error = f"HTTP {e.response.status_code}"
        return result
    except httpx.RequestError as e:
        result.error = f"Request failed: {e}"
        return result

    # Use final URL for content extraction (after redirects)
    effective_url = result.final_url or url

    # Extract content
    if use_readability:
        content, metadata = extract_content_trafilatura(html, effective_url)
        result.title = metadata.get("title")
        result.author = metadata.get("author")
        result.published = metadata.get("date")
        result.description = metadata.get("description")
    else:
        content = html_to_markdown(html)
        metadata = extract_metadata_from_html(html, effective_url)
        result.title = metadata.get("title")
        result.author = metadata.get("author")
        result.published = metadata.get("published")
        result.description = metadata.get("description")

    # Fallback metadata extraction if trafilatura missed things
    if not result.title or not result.description or not result.author or not result.published:
        html_meta = extract_metadata_from_html(html, effective_url)
        result.title = result.title or html_meta.get("title")
        result.description = result.description or html_meta.get("description")
        result.author = result.author or html_meta.get("author")
        result.published = result.published or html_meta.get("published")

    result.content = content
    result.success = True

    return result


async def fetch_urls(
    urls: list[str],
    config: Config,
    use_readability: bool = True,
    max_concurrent: int = 5,
) -> list[FetchResult]:
    """Fetch multiple URLs concurrently.

    Args:
        urls: List of URLs to fetch.
        config: Application configuration.
        use_readability: Whether to use readability extraction.
        max_concurrent: Maximum concurrent requests.

    Returns:
        List of FetchResult objects.
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_with_semaphore(
        client: httpx.AsyncClient,
        url: str,
    ) -> FetchResult:
        async with semaphore:
            return await fetch_url(client, url, config, use_readability)

    timeout = httpx.Timeout(config.fetch.timeout)
    headers = {"User-Agent": config.fetch.user_agent}

    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        tasks = [fetch_with_semaphore(client, url) for url in urls]
        return list(await asyncio.gather(*tasks))


def save_article(
    result: FetchResult,
    output_dir: Path,
    config: Config,  # noqa: ARG001
) -> Path | None:
    """Save fetched article to file.

    Never overwrites existing files - adds suffix if needed.

    Args:
        result: Fetch result with content.
        output_dir: Directory to save to.
        config: Application configuration.

    Returns:
        Path to saved file, or None if failed.
    """
    if not result.success or not result.content:
        return None

    # Use final URL (after redirects) for saved article
    source_url = result.final_url or result.url

    # Generate filename
    filename = generate_filename(
        result.title,
        result.published,
        source_url,
    )

    # Get unique filepath (never overwrite)
    filepath = get_unique_filepath(output_dir, filename)
    result.filename = filepath.name

    # Build frontmatter with final URL
    frontmatter = build_frontmatter(
        url=source_url,
        title=result.title,
        author=result.author,
        published=result.published,
        description=result.description,
    )

    # Combine frontmatter and content
    full_content = f"{frontmatter}\n\n{result.content}"

    # Save file
    try:
        filepath.write_text(full_content, encoding="utf-8")
        return filepath
    except OSError:
        return None


def process_fetch_results(
    results: list[FetchResult],
    output_dir: Path,
    config: Config,
    dry_run: bool = False,
) -> ProcessResult:
    """Process fetch results by saving articles and collecting stats.

    Args:
        results: List of fetch results to process.
        output_dir: Directory to save articles to.
        config: Application configuration.
        dry_run: If True, don't save files, just simulate.

    Returns:
        ProcessResult with stats and list of saved files.
    """
    stats = FetchStats(total=len(results))
    saved_files = []

    for result in results:
        if result.success:
            if dry_run:
                filename = generate_filename(result.title, result.published, result.url)
                stats.saved += 1
                saved_files.append(
                    SavedFile(
                        filename=filename,
                        path=output_dir / filename,
                        url=result.url,
                        title=result.title,
                    )
                )
            else:
                saved_path = save_article(result, output_dir, config)
                if saved_path:
                    stats.saved += 1
                    saved_files.append(
                        SavedFile(
                            filename=saved_path.name,
                            path=saved_path,
                            url=result.url,
                            title=result.title,
                        )
                    )
                else:
                    stats.errors.append((result.url, "Failed to save"))
        else:
            stats.errors.append((result.url, result.error or "Unknown error"))

    return ProcessResult(stats=stats, saved_files=saved_files)


@dataclass
class FetchOrchestrationResult:
    """Result of orchestrated fetch operation."""

    process_result: ProcessResult
    fetch_results: list[FetchResult] = field(default_factory=list)
    skipped_urls: list[str] = field(default_factory=list)
    feed_entry_count: int | None = None


async def orchestrate_fetch(
    cli_urls: tuple[str, ...],
    url_file: Path | None,
    config: Config,
    output_dir: Path,
    rss: bool = False,
    rss_limit: int = 10,
    check_duplicates: bool = True,
    use_readability: bool = True,
    dry_run: bool = False,
) -> FetchOrchestrationResult:
    """Orchestrate complete fetch workflow.

    Handles URL collection, RSS validation, duplicate filtering, fetching, and processing.

    Args:
        cli_urls: URLs from CLI arguments.
        url_file: Optional file containing URLs.
        config: Application configuration.
        output_dir: Directory to save articles.
        rss: If True, treat URL as RSS feed.
        rss_limit: Max RSS entries to fetch.
        check_duplicates: If True, skip already-cached URLs.
        use_readability: If True, extract main content from HTML.
        dry_run: If True, don't save files.

    Returns:
        FetchOrchestrationResult with process results and metadata.
    """
    # Collect URLs
    all_urls = collect_urls(cli_urls, url_file)

    if not all_urls:
        return FetchOrchestrationResult(
            process_result=ProcessResult(stats=FetchStats(total=0)),
            fetch_results=[],
            skipped_urls=[],
        )

    # Handle RSS feeds
    feed_entry_count = None
    if rss:
        is_valid, _ = validate_rss_mode(all_urls)
        if not is_valid:
            return FetchOrchestrationResult(
                process_result=ProcessResult(stats=FetchStats(total=0)),
                fetch_results=[],
                skipped_urls=[],
            )
        feed_urls = await fetch_rss_feed(all_urls[0], config, rss_limit)
        feed_entry_count = len(feed_urls)
        all_urls = feed_urls

    # Filter duplicates
    skipped_urls = []
    if check_duplicates:
        filter_result = filter_duplicate_urls(all_urls, config)
        skipped_urls = filter_result.skipped_urls
        all_urls = filter_result.filtered_urls

    if not all_urls:
        return FetchOrchestrationResult(
            process_result=ProcessResult(stats=FetchStats(total=0)),
            fetch_results=[],
            skipped_urls=skipped_urls,
            feed_entry_count=feed_entry_count,
        )

    # Fetch URLs
    results = await fetch_urls(
        all_urls,
        config,
        use_readability=use_readability,
        max_concurrent=config.fetch.max_concurrent,
    )

    # Process results
    process_result = process_fetch_results(results, output_dir, config, dry_run=dry_run)

    return FetchOrchestrationResult(
        process_result=process_result,
        fetch_results=results,
        skipped_urls=skipped_urls,
        feed_entry_count=feed_entry_count,
    )
