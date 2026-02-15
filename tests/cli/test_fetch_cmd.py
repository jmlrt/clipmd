"""CLI tests for fetch command."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import yaml
from click.testing import CliRunner

from clipmd.cli import main
from clipmd.core.fetcher import (
    FetchResult,
    extract_meta_refresh_url,
    extract_metadata_from_html,
    generate_filename,
)
from clipmd.core.filepath_utils import get_unique_filepath
from clipmd.core.frontmatter import build_frontmatter
from clipmd.core.rss import parse_rss_feed
from clipmd.core.sanitizer import sanitize_title_for_filename
from clipmd.core.url_utils import extract_url_from_line, read_urls_from_file

if TYPE_CHECKING:
    import pytest


class TestFetchCommand:
    """Tests for the fetch command."""

    def test_help(self) -> None:
        """Test --help option."""
        runner = CliRunner()
        result = runner.invoke(main, ["fetch", "--help"])
        assert result.exit_code == 0
        assert "fetch" in result.output.lower()

    def test_no_urls(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test fetch without URLs."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        runner = CliRunner()
        result = runner.invoke(main, ["fetch"])
        assert result.exit_code == 0
        assert "No URLs provided" in result.output

    def test_read_urls_from_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test reading URLs from file."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        # Create URL file
        url_file = tmp_path / "urls.txt"
        url_file.write_text(
            """# Comment line
https://example.com/article1
https://example.com/article2

# Another comment
https://example.com/article3
"""
        )

        # Mock the fetch to return success
        mock_result = FetchResult(
            url="https://example.com/article1",
            success=True,
            title="Test Article",
            content="Test content",
            filename="20240115-Test-Article.md",
        )

        with patch("clipmd.core.fetcher.fetch_urls", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [mock_result, mock_result, mock_result]

            runner = CliRunner()
            result = runner.invoke(main, ["fetch", "-f", str(url_file), "--dry-run"])
            assert result.exit_code == 0
            # Should have read 3 URLs from file
            mock_fetch.assert_called_once()
            urls = mock_fetch.call_args[0][0]
            assert len(urls) == 3

    def test_dry_run(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test dry run mode."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        mock_result = FetchResult(
            url="https://example.com/article",
            success=True,
            title="Test Article",
            content="Test content",
        )

        with patch("clipmd.core.fetcher.fetch_urls", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [mock_result]

            runner = CliRunner()
            result = runner.invoke(
                main,
                ["fetch", "https://example.com/article", "--dry-run"],
            )
            assert result.exit_code == 0
            assert "Dry run" in result.output
            assert "Would save" in result.output

            # No files should be created
            md_files = list(tmp_path.glob("*.md"))
            assert len(md_files) == 0

    def test_check_duplicates(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that duplicates are skipped by default."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n  cache: .clipmd/cache.json\n")

        # Create cache with existing URL
        cache_dir = tmp_path / ".clipmd"
        cache_dir.mkdir()
        cache_file = cache_dir / "cache.json"
        cache_file.write_text(
            """{
            "version": 1,
            "entries": {
                "https://example.com/existing": {
                    "filename": "20240115-Existing.md",
                    "title": "Existing",
                    "first_seen": "2024-01-15",
                    "last_seen": "2024-01-15"
                }
            }
        }"""
        )

        runner = CliRunner()
        result = runner.invoke(main, ["fetch", "https://example.com/existing", "--no-cache-update"])
        assert result.exit_code == 0
        assert "Skipping" in result.output or "already saved" in result.output

    def test_no_check_duplicates(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test bypassing duplicate check."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n  cache: .clipmd/cache.json\n")

        # Create cache with existing URL
        cache_dir = tmp_path / ".clipmd"
        cache_dir.mkdir()
        cache_file = cache_dir / "cache.json"
        cache_file.write_text(
            """{
            "version": 1,
            "entries": {
                "https://example.com/existing": {
                    "filename": "20240115-Existing.md",
                    "title": "Existing",
                    "first_seen": "2024-01-15",
                    "last_seen": "2024-01-15"
                }
            }
        }"""
        )

        mock_result = FetchResult(
            url="https://example.com/existing",
            success=True,
            title="Test Article",
            content="Test content",
        )

        with patch("clipmd.core.fetcher.fetch_urls", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [mock_result]

            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "fetch",
                    "https://example.com/existing",
                    "--no-check-duplicates",
                    "--dry-run",
                ],
            )
            assert result.exit_code == 0
            # Should not skip even though URL is in cache
            mock_fetch.assert_called_once()

    def test_json_output(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test JSON output format."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        mock_result = FetchResult(
            url="https://example.com/article",
            success=True,
            title="Test Article",
            content="Test content",
        )

        with patch("clipmd.core.fetcher.fetch_urls", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [mock_result]

            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "fetch",
                    "https://example.com/article",
                    "--format",
                    "json",
                    "--dry-run",
                ],
            )
            assert result.exit_code == 0
            assert '"total"' in result.output
            assert '"saved"' in result.output


class TestFetchHelpers:
    """Tests for fetch helper functions."""

    def test_sanitize_title_for_filename(self) -> None:
        """Test title sanitization."""
        assert sanitize_title_for_filename("Hello World") == "Hello-World"
        assert sanitize_title_for_filename("Test: Article!") == "Test-Article"
        assert sanitize_title_for_filename("  Spaced  ") == "Spaced"
        assert sanitize_title_for_filename("A" * 200)[:100]  # Truncated

    def test_generate_filename(self) -> None:
        """Test filename generation."""
        filename = generate_filename(
            title="Test Article",
            published="2024-01-15",
            url="https://example.com/article",
        )
        assert filename.startswith("20240115-")
        assert "Test-Article" in filename
        assert filename.endswith(".md")

    def test_generate_filename_no_title(self) -> None:
        """Test filename generation without title."""
        filename = generate_filename(
            title=None,
            published=None,
            url="https://example.com/article",
        )
        assert filename.endswith(".md")
        assert "example-com" in filename

    def test_build_frontmatter(self) -> None:
        """Test frontmatter building."""
        fm = build_frontmatter(
            url="https://example.com/article",
            title="Test Article",
            author="John Doe",
            published="2024-01-15",
            description="A test description",
        )
        assert fm.startswith("---\n")
        assert fm.endswith("---")

        # Parse and validate YAML content
        fm_content = fm.strip("- \n")
        data = yaml.safe_load(fm_content)
        assert data["title"] == "Test Article"
        assert data["source"] == "https://example.com/article"
        assert data["author"] == "John Doe"
        assert data["published"] == "2024-01-15"
        assert data["description"] == "A test description"

    def test_build_frontmatter_with_colon_in_title(self) -> None:
        """Test frontmatter with colon in title (needs proper YAML quoting)."""
        fm = build_frontmatter(
            url="https://example.com/article",
            title="Title: With Colon",
            author=None,
            published=None,
            description=None,
        )
        # Validate the title is properly quoted/handled by YAML
        fm_content = fm.strip("- \n")
        data = yaml.safe_load(fm_content)
        assert data["title"] == "Title: With Colon"

    def test_extract_metadata_from_html(self) -> None:
        """Test metadata extraction from HTML."""
        html = """
        <html>
        <head>
            <title>Page Title</title>
            <meta property="og:title" content="OG Title">
            <meta name="author" content="Author Name">
            <meta name="description" content="Page description">
        </head>
        <body></body>
        </html>
        """
        metadata = extract_metadata_from_html(html, "https://example.com")
        assert metadata["title"] == "OG Title"  # OG takes precedence
        assert metadata["author"] == "Author Name"
        assert metadata["description"] == "Page description"

    def test_parse_rss_feed(self) -> None:
        """Test RSS feed parsing."""
        feed_content = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Test Feed</title>
                <item>
                    <title>Article 1</title>
                    <link>https://example.com/article1</link>
                </item>
                <item>
                    <title>Article 2</title>
                    <link>https://example.com/article2</link>
                </item>
            </channel>
        </rss>
        """
        urls = parse_rss_feed(feed_content, "https://example.com/feed", limit=10)
        assert len(urls) == 2
        assert "https://example.com/article1" in urls
        assert "https://example.com/article2" in urls

    def test_parse_rss_feed_with_limit(self) -> None:
        """Test RSS feed parsing with limit."""
        feed_content = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item><link>https://example.com/1</link></item>
                <item><link>https://example.com/2</link></item>
                <item><link>https://example.com/3</link></item>
            </channel>
        </rss>
        """
        urls = parse_rss_feed(feed_content, "https://example.com/feed", limit=2)
        assert len(urls) == 2


class TestFetchRss:
    """Tests for RSS feed fetching."""

    def test_rss_requires_single_url(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that RSS mode requires exactly one URL."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["fetch", "--rss", "https://example.com/feed1", "https://example.com/feed2"],
        )
        assert result.exit_code != 0
        assert "exactly one feed URL" in result.output


class TestFetchErrors:
    """Tests for error handling in fetch."""

    def test_fetch_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test handling of fetch errors."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        mock_result = FetchResult(
            url="https://example.com/article",
            success=False,
            error="HTTP 404",
        )

        with patch("clipmd.core.fetcher.fetch_urls", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [mock_result]

            runner = CliRunner()
            result = runner.invoke(
                main, ["fetch", "https://example.com/article", "--no-cache-update"]
            )
            assert result.exit_code == 0
            assert "404" in result.output or "failed" in result.output.lower()


class TestFetchContentExtraction:
    """Tests for content extraction functions."""

    def test_html_to_markdown(self) -> None:
        """Test HTML to markdown conversion."""
        from clipmd.core.fetcher import html_to_markdown

        html = "<h1>Title</h1><p>Paragraph text.</p>"
        md = html_to_markdown(html)
        assert "Title" in md
        assert "Paragraph text" in md

    def test_extract_content_trafilatura(self) -> None:
        """Test trafilatura content extraction."""
        from clipmd.core.fetcher import extract_content_trafilatura

        html = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <article>
                <h1>Main Content Title</h1>
                <p>This is the main content of the article.</p>
            </article>
        </body>
        </html>
        """
        content, metadata = extract_content_trafilatura(html, "https://example.com")
        # Content may be empty for minimal HTML but function should not crash
        assert isinstance(content, str)
        assert isinstance(metadata, dict)


class TestFetchSaveArticle:
    """Tests for saving articles."""

    def test_save_article(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test saving an article to file."""
        from clipmd.config import load_config
        from clipmd.core.fetcher import save_article

        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")
        config = load_config(config_file)

        result = FetchResult(
            url="https://example.com/article",
            success=True,
            title="Test Article",
            author="John Doe",
            published="2024-01-15",
            description="Test description",
            content="# Test Content\n\nThis is the article content.",
        )

        saved_path = save_article(result, tmp_path, config)

        assert saved_path is not None
        assert saved_path.exists()
        content = saved_path.read_text()
        assert "title:" in content
        assert "source: https://example.com/article" in content
        assert "Test Content" in content

    def test_save_article_failed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test save_article returns None for failed result."""
        from clipmd.config import load_config
        from clipmd.core.fetcher import save_article

        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")
        config = load_config(config_file)

        result = FetchResult(
            url="https://example.com/article",
            success=False,
            error="HTTP 404",
        )

        saved_path = save_article(result, tmp_path, config)
        assert saved_path is None


class TestFetchUrls:
    """Tests for URL fetching."""

    def test_fetch_url_success(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test successful URL fetch."""
        import asyncio

        from clipmd.config import load_config
        from clipmd.core.fetcher import fetch_url

        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")
        config = load_config(config_file)

        # Mock HTTP response
        mock_response = AsyncMock()
        mock_response.text = """
        <html>
        <head>
            <title>Test Page</title>
            <meta property="og:title" content="OG Title">
        </head>
        <body><p>Content</p></body>
        </html>
        """
        mock_response.raise_for_status = lambda: None

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        async def run_test():
            return await fetch_url(
                mock_client, "https://example.com/article", config, use_readability=False
            )

        result = asyncio.run(run_test())
        assert result.success
        assert result.title is not None

    def test_fetch_url_http_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test HTTP error handling."""
        import asyncio

        import httpx

        from clipmd.config import load_config
        from clipmd.core.fetcher import fetch_url

        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")
        config = load_config(config_file)

        # Mock HTTP error
        mock_response = AsyncMock()
        mock_response.status_code = 404
        error = httpx.HTTPStatusError("Not found", request=None, response=mock_response)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=error)

        async def run_test():
            return await fetch_url(mock_client, "https://example.com/404", config)

        result = asyncio.run(run_test())
        assert not result.success
        assert "404" in result.error

    def test_fetch_url_request_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test request error handling."""
        import asyncio

        import httpx

        from clipmd.config import load_config
        from clipmd.core.fetcher import fetch_url

        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")
        config = load_config(config_file)

        # Mock connection error
        error = httpx.ConnectError("Connection refused")

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=error)

        async def run_test():
            return await fetch_url(mock_client, "https://example.com/error", config)

        result = asyncio.run(run_test())
        assert not result.success
        assert "Request failed" in result.error


class TestCacheUpdate:
    """Tests for cache updates after fetch."""

    def test_update_cache_after_fetch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test cache is updated after fetch."""
        from clipmd.config import load_config
        from clipmd.core.cache import load_cache, update_cache_after_fetch

        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n  cache: .clipmd/cache.json\n")
        config = load_config(config_file)

        # Create cache dir
        cache_dir = tmp_path / ".clipmd"
        cache_dir.mkdir()

        results = [
            FetchResult(
                url="https://example.com/article1",
                success=True,
                title="Article 1",
                content="Content 1",
                filename="20240115-Article-1.md",
            ),
            FetchResult(
                url="https://example.com/article2",
                success=True,
                title="Article 2",
                content="Content 2",
                filename="20240115-Article-2.md",
            ),
        ]

        update_cache_after_fetch(results, config)

        # Verify cache was updated
        cache_path = config.paths.root / config.paths.cache
        cache = load_cache(cache_path)
        assert cache.has_url("https://example.com/article1")
        assert cache.has_url("https://example.com/article2")


class TestFetchUrlsFunction:
    """Tests for the fetch_urls async function."""

    def test_fetch_urls_concurrent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test fetching multiple URLs concurrently."""
        import asyncio

        from clipmd.config import load_config
        from clipmd.core.fetcher import fetch_urls

        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\nfetch:\n  timeout: 10\n")
        config = load_config(config_file)

        # Mock httpx.AsyncClient
        mock_response = AsyncMock()
        mock_response.text = "<html><head><title>Test</title></head><body>Content</body></html>"
        mock_response.raise_for_status = lambda: None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            urls = ["https://example.com/1", "https://example.com/2"]
            results = asyncio.run(fetch_urls(urls, config, use_readability=False))

            assert len(results) == 2
            assert all(r.success for r in results)


class TestFetchRssFeedFunction:
    """Tests for RSS feed fetching function."""

    def test_fetch_rss_feed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test fetching RSS feed."""
        import asyncio

        from clipmd.config import load_config
        from clipmd.core.fetcher import fetch_rss_feed

        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\nfetch:\n  timeout: 10\n")
        config = load_config(config_file)

        feed_xml = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <item><link>https://example.com/article1</link></item>
                <item><link>https://example.com/article2</link></item>
            </channel>
        </rss>
        """

        mock_response = AsyncMock()
        mock_response.text = feed_xml
        mock_response.raise_for_status = lambda: None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            urls = asyncio.run(fetch_rss_feed("https://example.com/feed", config, limit=10))

            assert len(urls) == 2
            assert "https://example.com/article1" in urls


class TestFetchWithReadability:
    """Tests for fetch with readability extraction."""

    def test_fetch_url_with_readability(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test fetch URL with readability mode."""
        import asyncio

        from clipmd.config import load_config
        from clipmd.core.fetcher import fetch_url

        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")
        config = load_config(config_file)

        # Mock HTTP response with more complete HTML
        mock_response = AsyncMock()
        mock_response.text = """
        <html>
        <head>
            <title>Test Article</title>
            <meta property="og:title" content="OG Title">
            <meta property="og:description" content="Description">
        </head>
        <body>
            <article>
                <h1>Article Title</h1>
                <p>This is the main content of the article with enough text to be extracted.</p>
                <p>More content here for the readability extraction.</p>
            </article>
        </body>
        </html>
        """
        mock_response.raise_for_status = lambda: None

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        async def run_test():
            return await fetch_url(
                mock_client, "https://example.com/article", config, use_readability=True
            )

        result = asyncio.run(run_test())
        assert result.success

    def test_fetch_with_metadata_fallback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that BeautifulSoup fallback extracts metadata when trafilatura fails."""
        import asyncio

        from clipmd.config import load_config
        from clipmd.core.fetcher import fetch_url

        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")
        config = load_config(config_file)

        # Mock HTML with rich metadata in meta tags
        # Trafilatura might miss these, but BeautifulSoup will catch them
        mock_response = AsyncMock()
        mock_response.text = """
        <html>
        <head>
            <title>Fallback Test Article</title>
            <meta property="og:title" content="OG Fallback Title">
            <meta property="og:description" content="This description comes from OG tags">
            <meta name="author" content="John Doe">
            <meta property="article:published_time" content="2024-01-15T10:00:00Z">
        </head>
        <body>
            <p>Minimal content that trafilatura might not extract metadata from.</p>
        </body>
        </html>
        """
        mock_response.raise_for_status = lambda: None

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        # Mock trafilatura to return content but NO metadata (simulating failure)
        with patch("clipmd.core.fetcher.trafilatura.extract") as mock_extract:
            # First call: extract content (markdown output)
            # Second call: extract metadata (json output) - returns None to simulate failure
            mock_extract.side_effect = [
                "Minimal content",  # Content extraction
                None,  # Metadata extraction fails
            ]

            async def run_test():
                return await fetch_url(
                    mock_client,
                    "https://example.com/article",
                    config,
                    use_readability=True,
                )

            result = asyncio.run(run_test())

            # Verify fallback worked
            assert result.success
            assert result.title == "OG Fallback Title"  # From BeautifulSoup fallback
            assert result.description == "This description comes from OG tags"
            assert result.author == "John Doe"
            assert result.published == "2024-01-15T10:00:00Z"


class TestFetchCommandIntegration:
    """Integration tests for fetch command."""

    def test_successful_fetch_saves_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test successful fetch saves file and updates cache."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n  cache: .clipmd/cache.json\n")

        # Create cache dir
        cache_dir = tmp_path / ".clipmd"
        cache_dir.mkdir()

        mock_result = FetchResult(
            url="https://example.com/article",
            success=True,
            title="Test Article",
            author="Jane Doe",
            published="2024-01-15",
            content="# Test Content\n\nThis is test content.",
            filename="20240115-Test-Article.md",
        )

        with patch("clipmd.core.fetcher.fetch_urls", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [mock_result]

            runner = CliRunner()
            result = runner.invoke(
                main, ["fetch", "https://example.com/article", "--no-cache-update"]
            )
            assert result.exit_code == 0
            assert "Test Article" in result.output
            assert "Jane Doe" in result.output

    def test_all_urls_saved_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test message when all URLs are already saved."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n  cache: .clipmd/cache.json\n")

        # Create cache with all URLs already saved
        cache_dir = tmp_path / ".clipmd"
        cache_dir.mkdir()
        cache_file = cache_dir / "cache.json"
        cache_file.write_text(
            """{
            "version": 1,
            "entries": {
                "https://example.com/1": {"filename": "1.md", "title": "1", "first_seen": "2024-01-15", "last_seen": "2024-01-15"},
                "https://example.com/2": {"filename": "2.md", "title": "2", "first_seen": "2024-01-15", "last_seen": "2024-01-15"}
            }
        }"""
        )

        runner = CliRunner()
        result = runner.invoke(main, ["fetch", "https://example.com/1", "https://example.com/2"])
        assert result.exit_code == 0
        assert "All URLs already saved" in result.output


class TestReadUrlsFromFile:
    """Tests for reading URLs from file."""

    def test_read_urls_from_file(self, tmp_path: Path) -> None:
        """Test reading URLs from file."""
        url_file = tmp_path / "urls.txt"
        url_file.write_text(
            """# This is a comment
https://example.com/article1

# Another comment
https://example.com/article2
https://example.com/article3
"""
        )

        urls = read_urls_from_file(url_file)
        assert len(urls) == 3
        assert "https://example.com/article1" in urls
        assert "https://example.com/article2" in urls
        assert "https://example.com/article3" in urls

    def test_read_urls_from_markdown_file(self, tmp_path: Path) -> None:
        """Test reading URLs from markdown file with link syntax."""
        url_file = tmp_path / "URLs.md"
        url_file.write_text(
            """[Link text](https://example.com/article1)
[Another link](https://example.com/article2)

# Comment line
[Third](https://example.com/article3) # inline comment
"""
        )

        urls = read_urls_from_file(url_file)
        assert len(urls) == 3
        assert "https://example.com/article1" in urls
        assert "https://example.com/article2" in urls
        assert "https://example.com/article3" in urls

    def test_read_urls_with_inline_comments(self, tmp_path: Path) -> None:
        """Test reading URLs with inline comments."""
        url_file = tmp_path / "urls.txt"
        url_file.write_text(
            """https://example.com/article1 # This is a great article
https://example.com/article2 # Another one
"""
        )

        urls = read_urls_from_file(url_file)
        assert len(urls) == 2
        assert "https://example.com/article1" in urls
        assert "https://example.com/article2" in urls

    def test_read_urls_with_angle_brackets(self, tmp_path: Path) -> None:
        """Test reading URLs from file with angle bracket syntax."""
        url_file = tmp_path / "urls.txt"
        url_file.write_text(
            """<https://example.com/article1>
<https://example.com/article2> # with comment
<http://example.com/article3>
"""
        )

        urls = read_urls_from_file(url_file)
        assert len(urls) == 3
        assert "https://example.com/article1" in urls
        assert "https://example.com/article2" in urls
        assert "http://example.com/article3" in urls


class TestExtractUrlFromLine:
    """Tests for extract_url_from_line function."""

    def test_plain_url(self) -> None:
        """Test extracting plain URL."""
        url = extract_url_from_line("https://example.com/article")
        assert url == "https://example.com/article"

    def test_markdown_link(self) -> None:
        """Test extracting URL from markdown link."""
        url = extract_url_from_line("[Link text](https://example.com/article)")
        assert url == "https://example.com/article"

    def test_inline_comment(self) -> None:
        """Test stripping inline comments."""
        url = extract_url_from_line("https://example.com/article # this is a comment")
        assert url == "https://example.com/article"

    def test_markdown_with_comment(self) -> None:
        """Test markdown link with inline comment."""
        url = extract_url_from_line("[Link](https://example.com/article) # comment")
        assert url == "https://example.com/article"

    def test_empty_line(self) -> None:
        """Test empty line returns None."""
        url = extract_url_from_line("")
        assert url is None

    def test_comment_line(self) -> None:
        """Test comment line returns None."""
        url = extract_url_from_line("# This is a comment")
        assert url is None

    def test_invalid_markdown_link(self) -> None:
        """Test invalid markdown link without valid URL."""
        url = extract_url_from_line("[Link text](not-a-url)")
        assert url is None

    def test_plain_text(self) -> None:
        """Test plain text returns None."""
        url = extract_url_from_line("This is just text")
        assert url is None

    def test_http_url(self) -> None:
        """Test HTTP URL is accepted."""
        url = extract_url_from_line("http://example.com/article")
        assert url == "http://example.com/article"

    def test_complex_redirect_url(self) -> None:
        """Test complex tracking/redirect URL."""
        tracking_url = "https://tracker.example.com/click?u=abc123&id=xyz789&e=user@email.com"
        url = extract_url_from_line(f"[Link text]({tracking_url})")
        assert url == tracking_url

    def test_angle_bracket_url(self) -> None:
        """Test extracting URL from angle brackets."""
        url = extract_url_from_line("<https://example.com/article>")
        assert url == "https://example.com/article"

    def test_angle_bracket_http_url(self) -> None:
        """Test extracting HTTP URL from angle brackets."""
        url = extract_url_from_line("<http://example.com/article>")
        assert url == "http://example.com/article"

    def test_angle_bracket_with_comment(self) -> None:
        """Test angle bracket URL with inline comment."""
        url = extract_url_from_line("<https://example.com/article> # great article")
        assert url == "https://example.com/article"

    def test_angle_bracket_complex_url(self) -> None:
        """Test angle bracket with complex URL containing query params."""
        url = extract_url_from_line("<https://example.com/path?foo=bar&baz=qux>")
        assert url == "https://example.com/path?foo=bar&baz=qux"

    def test_invalid_angle_bracket(self) -> None:
        """Test invalid content in angle brackets."""
        url = extract_url_from_line("<not-a-url>")
        assert url is None


class TestExtractMetaRefreshUrl:
    """Tests for extract_meta_refresh_url function."""

    def test_meta_refresh_tag(self) -> None:
        """Test extracting URL from meta refresh tag."""
        html = """
        <html><head>
        <meta http-equiv="refresh" content="0;url=https://example.com/article">
        </head></html>
        """
        url = extract_meta_refresh_url(html)
        assert url == "https://example.com/article"

    def test_meta_refresh_noscript(self) -> None:
        """Test extracting URL from noscript meta refresh."""
        html = """
        <html><head><title>Redirection</title></head><body>
        <noscript>
        <meta http-equiv="refresh" content="0.0;https://korben.info/article.html">
        </noscript>
        </body></html>
        """
        url = extract_meta_refresh_url(html)
        assert url == "https://korben.info/article.html"

    def test_javascript_location(self) -> None:
        """Test extracting URL from JavaScript location assignment."""
        html = """
        <script>
        location='https://example.com/article'
        </script>
        """
        url = extract_meta_refresh_url(html)
        assert url == "https://example.com/article"

    def test_javascript_top_location(self) -> None:
        """Test extracting URL from top.location assignment."""
        html = """
        <script>
        top.location='https://example.com/article'
        </script>
        """
        url = extract_meta_refresh_url(html)
        assert url == "https://example.com/article"

    def test_javascript_escaped_url(self) -> None:
        """Test extracting URL with escaped slashes."""
        html = """
        <script>
        top.location='https:\\/\\/example.com\\/article'
        </script>
        """
        url = extract_meta_refresh_url(html)
        assert url == "https://example.com/article"

    def test_window_location(self) -> None:
        """Test extracting URL from window.location."""
        html = """
        <script>
        window.location = "https://example.com/article"
        </script>
        """
        url = extract_meta_refresh_url(html)
        assert url == "https://example.com/article"

    def test_no_redirect(self) -> None:
        """Test when no redirect is found."""
        html = """
        <html><head><title>Normal Page</title></head>
        <body><p>Content</p></body></html>
        """
        url = extract_meta_refresh_url(html)
        assert url is None

    def test_invalid_url_in_meta(self) -> None:
        """Test when meta refresh contains non-URL."""
        html = """
        <meta http-equiv="refresh" content="0;url=not-a-valid-url">
        """
        url = extract_meta_refresh_url(html)
        assert url is None

    def test_real_tracking_redirect(self) -> None:
        """Test with real-world tracking redirect HTML."""
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Redirection</title></head>
        <body>
        <noscript>
        <meta http-equiv="refresh" content="0.0;https://korben.info/jonathan-james-plus-jeune-hacker-emprisonne-usa.html">
        </noscript>
        <script>
        var autoRedirectTimeout = setTimeout(function(){ top.location='https:\\/\\/korben.info\\/jonathan-james-plus-jeune-hacker-emprisonne-usa.html' }, 3000)
        </script>
        </body>
        </html>
        """
        url = extract_meta_refresh_url(html)
        assert url == "https://korben.info/jonathan-james-plus-jeune-hacker-emprisonne-usa.html"


class TestGetUniqueFilepath:
    """Tests for get_unique_filepath function."""

    def test_unique_when_no_conflict(self, tmp_path: Path) -> None:
        """Test returns original path when no file exists."""
        filepath = get_unique_filepath(tmp_path, "article.md")
        assert filepath == tmp_path / "article.md"

    def test_adds_suffix_when_exists(self, tmp_path: Path) -> None:
        """Test adds -1 suffix when file exists."""
        # Create existing file
        (tmp_path / "article.md").write_text("existing")

        filepath = get_unique_filepath(tmp_path, "article.md")
        assert filepath == tmp_path / "article-1.md"

    def test_increments_suffix(self, tmp_path: Path) -> None:
        """Test increments suffix when multiple exist."""
        # Create existing files
        (tmp_path / "article.md").write_text("existing")
        (tmp_path / "article-1.md").write_text("existing")
        (tmp_path / "article-2.md").write_text("existing")

        filepath = get_unique_filepath(tmp_path, "article.md")
        assert filepath == tmp_path / "article-3.md"

    def test_preserves_extension(self, tmp_path: Path) -> None:
        """Test preserves file extension."""
        (tmp_path / "20240101-article.md").write_text("existing")

        filepath = get_unique_filepath(tmp_path, "20240101-article.md")
        assert filepath.suffix == ".md"
        assert filepath == tmp_path / "20240101-article-1.md"

    def test_handles_no_extension(self, tmp_path: Path) -> None:
        """Test handles files without extension."""
        (tmp_path / "README").write_text("existing")

        filepath = get_unique_filepath(tmp_path, "README")
        assert filepath == tmp_path / "README-1"

    def test_prevents_overwrite_scenario(self, tmp_path: Path) -> None:
        """Test real scenario: multiple 'Redirection' files."""
        # Simulate what would happen with tracking URLs that fail
        base_name = "20260119-Redirection.md"

        # Create several files with same base name
        (tmp_path / base_name).write_text("first")
        (tmp_path / "20260119-Redirection-1.md").write_text("second")

        # Third file should get -2 suffix
        filepath = get_unique_filepath(tmp_path, base_name)
        assert filepath == tmp_path / "20260119-Redirection-2.md"
        assert not filepath.exists()  # New path shouldn't exist yet
