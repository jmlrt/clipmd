"""Unit tests for URL and content cache."""

from __future__ import annotations

import json
from pathlib import Path

from clipmd.core.cache import Cache, CacheEntry, load_cache


class TestCacheEntry:
    """Tests for CacheEntry class."""

    def test_create_entry(self) -> None:
        """Test creating a cache entry."""
        entry = CacheEntry(
            filename="20240115-Article.md",
            title="My Article",
            folder="Tech",
        )
        assert entry.filename == "20240115-Article.md"
        assert entry.title == "My Article"
        assert entry.folder == "Tech"
        assert entry.removed is False
        assert entry.first_seen != ""
        assert entry.last_seen != ""

    def test_to_dict(self) -> None:
        """Test converting entry to dictionary."""
        entry = CacheEntry(
            filename="article.md",
            title="Article",
            first_seen="2024-01-15",
            last_seen="2024-01-16",
            content_hash="abc123",
        )
        result = entry.to_dict()
        assert result["filename"] == "article.md"
        assert result["title"] == "Article"
        assert result["content_hash"] == "abc123"
        assert "removed_at" not in result

    def test_to_dict_with_removed(self) -> None:
        """Test converting removed entry to dictionary."""
        entry = CacheEntry(
            filename="article.md",
            title="Article",
            removed=True,
            removed_at="2024-01-17T10:00:00Z",
        )
        result = entry.to_dict()
        assert result["removed"] is True
        assert result["removed_at"] == "2024-01-17T10:00:00Z"

    def test_from_dict(self) -> None:
        """Test creating entry from dictionary."""
        data = {
            "filename": "article.md",
            "title": "Article",
            "folder": "Tech",
            "first_seen": "2024-01-15",
            "last_seen": "2024-01-16",
            "removed": False,
            "content_hash": "abc123",
        }
        entry = CacheEntry.from_dict(data)
        assert entry.filename == "article.md"
        assert entry.folder == "Tech"
        assert entry.content_hash == "abc123"


class TestCache:
    """Tests for Cache class."""

    def test_empty_cache(self) -> None:
        """Test creating empty cache."""
        cache = Cache()
        assert cache.version == 1
        assert len(cache.entries) == 0

    def test_add_entry(self) -> None:
        """Test adding an entry."""
        cache = Cache()
        entry = cache.add(
            url="https://example.com/article",
            filename="article.md",
            title="Article",
            folder="Tech",
        )
        assert entry.filename == "article.md"
        assert cache.has_url("https://example.com/article")

    def test_has_url(self) -> None:
        """Test checking if URL exists."""
        cache = Cache()
        cache.add("https://example.com/article", "article.md", "Article")
        assert cache.has_url("https://example.com/article") is True
        assert cache.has_url("https://example.com/other") is False

    def test_has_active_url(self) -> None:
        """Test checking for active URL."""
        cache = Cache()
        cache.add("https://example.com/article", "article.md", "Article")
        cache.mark_removed("https://example.com/article")
        assert cache.has_url("https://example.com/article") is True
        assert cache.has_active_url("https://example.com/article") is False

    def test_get_entry(self) -> None:
        """Test getting an entry."""
        cache = Cache()
        cache.add("https://example.com/article", "article.md", "Article")
        entry = cache.get("https://example.com/article")
        assert entry is not None
        assert entry.filename == "article.md"

    def test_get_nonexistent(self) -> None:
        """Test getting nonexistent entry."""
        cache = Cache()
        entry = cache.get("https://example.com/nonexistent")
        assert entry is None

    def test_update_existing(self) -> None:
        """Test updating an existing entry."""
        cache = Cache()
        cache.add("https://example.com/article", "old.md", "Old Title")
        entry = cache.add("https://example.com/article", "new.md", "New Title")
        assert entry.filename == "new.md"
        assert entry.title == "New Title"

    def test_update_location(self) -> None:
        """Test updating entry location."""
        cache = Cache()
        cache.add("https://example.com/article", "article.md", "Article")
        entry = cache.update_location(
            "https://example.com/article",
            folder="NewFolder",
        )
        assert entry is not None
        assert entry.folder == "NewFolder"

    def test_mark_removed(self) -> None:
        """Test marking entry as removed."""
        cache = Cache()
        cache.add("https://example.com/article", "article.md", "Article")
        entry = cache.mark_removed("https://example.com/article")
        assert entry is not None
        assert entry.removed is True
        assert entry.removed_at is not None

    def test_remove_completely(self) -> None:
        """Test completely removing an entry."""
        cache = Cache()
        cache.add("https://example.com/article", "article.md", "Article")
        result = cache.remove("https://example.com/article")
        assert result is True
        assert cache.has_url("https://example.com/article") is False

    def test_remove_nonexistent(self) -> None:
        """Test removing nonexistent entry."""
        cache = Cache()
        result = cache.remove("https://example.com/nonexistent")
        assert result is False

    def test_find_by_filename(self) -> None:
        """Test finding entry by filename."""
        cache = Cache()
        cache.add("https://example.com/article", "article.md", "Article")
        result = cache.find_by_filename("article.md")
        assert result is not None
        url, _entry = result
        assert url == "https://example.com/article"

    def test_find_by_filename_not_found(self) -> None:
        """Test finding nonexistent filename."""
        cache = Cache()
        result = cache.find_by_filename("nonexistent.md")
        assert result is None

    def test_find_by_hash(self) -> None:
        """Test finding entries by content hash."""
        cache = Cache()
        cache.add("https://example.com/one", "one.md", "One", content_hash="abc123")
        cache.add("https://example.com/two", "two.md", "Two", content_hash="abc123")
        cache.add("https://example.com/three", "three.md", "Three", content_hash="def456")
        results = cache.find_by_hash("abc123")
        assert len(results) == 2

    def test_get_active_entries(self) -> None:
        """Test getting active entries."""
        cache = Cache()
        cache.add("https://example.com/one", "one.md", "One")
        cache.add("https://example.com/two", "two.md", "Two")
        cache.mark_removed("https://example.com/two")
        active = cache.get_active_entries()
        assert len(active) == 1
        assert "https://example.com/one" in active

    def test_get_removed_entries(self) -> None:
        """Test getting removed entries."""
        cache = Cache()
        cache.add("https://example.com/one", "one.md", "One")
        cache.add("https://example.com/two", "two.md", "Two")
        cache.mark_removed("https://example.com/two")
        removed = cache.get_removed_entries()
        assert len(removed) == 1
        assert "https://example.com/two" in removed

    def test_get_entries_by_folder(self) -> None:
        """Test grouping entries by folder."""
        cache = Cache()
        cache.add("https://example.com/one", "one.md", "One", folder="Tech")
        cache.add("https://example.com/two", "two.md", "Two", folder="Tech")
        cache.add("https://example.com/three", "three.md", "Three", folder="Science")
        cache.add("https://example.com/four", "four.md", "Four")
        by_folder = cache.get_entries_by_folder()
        assert len(by_folder["Tech"]) == 2
        assert len(by_folder["Science"]) == 1
        assert len(by_folder[None]) == 1

    def test_clean(self) -> None:
        """Test cleaning entries for missing files."""
        cache = Cache()
        cache.add("https://example.com/one", "one.md", "One")
        cache.add("https://example.com/two", "two.md", "Two")
        existing_files = {"one.md"}
        removed_count = cache.clean(existing_files)
        assert removed_count == 1
        assert cache.get("https://example.com/two").removed is True

    def test_clear(self) -> None:
        """Test clearing all entries."""
        cache = Cache()
        cache.add("https://example.com/one", "one.md", "One")
        cache.add("https://example.com/two", "two.md", "Two")
        cache.clear()
        assert len(cache.entries) == 0

    def test_to_dict(self) -> None:
        """Test converting cache to dictionary."""
        cache = Cache()
        cache.add("https://example.com/article", "article.md", "Article")
        result = cache.to_dict()
        assert result["version"] == 1
        assert "entries" in result
        assert "https://example.com/article" in result["entries"]

    def test_from_dict(self) -> None:
        """Test creating cache from dictionary."""
        data = {
            "version": 1,
            "updated": "2024-01-17T10:00:00Z",
            "entries": {
                "https://example.com/article": {
                    "filename": "article.md",
                    "title": "Article",
                    "folder": "Tech",
                    "first_seen": "2024-01-15",
                    "last_seen": "2024-01-17",
                    "removed": False,
                    "content_hash": None,
                }
            },
        }
        cache = Cache.from_dict(data)
        assert cache.version == 1
        assert len(cache.entries) == 1


class TestCachePersistence:
    """Tests for cache file persistence."""

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Test saving and loading cache."""
        cache_path = tmp_path / ".clipmd" / "cache.json"

        # Create and save cache
        cache = Cache()
        cache.add("https://example.com/article", "article.md", "Article")
        cache.save(cache_path)

        # Load and verify
        loaded = Cache.load(cache_path)
        assert len(loaded.entries) == 1
        assert loaded.has_url("https://example.com/article")

    def test_load_nonexistent(self, tmp_path: Path) -> None:
        """Test loading from nonexistent file."""
        cache_path = tmp_path / "nonexistent.json"
        cache = Cache.load(cache_path)
        assert len(cache.entries) == 0

    def test_save_creates_directory(self, tmp_path: Path) -> None:
        """Test that save creates parent directory."""
        cache_path = tmp_path / "deep" / "nested" / "cache.json"
        cache = Cache()
        cache.save(cache_path)
        assert cache_path.exists()


class TestLoadCache:
    """Tests for load_cache function."""

    def test_load_with_path(self, tmp_path: Path) -> None:
        """Test loading cache with explicit path."""
        cache_path = tmp_path / "cache.json"
        cache_path.write_text(json.dumps({"version": 1, "updated": "", "entries": {}}))
        cache = load_cache(cache_path)
        assert cache.version == 1

    def test_load_default_path(self, tmp_path: Path, monkeypatch) -> None:
        """Test loading cache with default path."""
        monkeypatch.chdir(tmp_path)
        cache = load_cache()
        assert cache.version == 1


class TestCacheUrlCleaning:
    """Tests for URL cleaning in cache operations."""

    def test_add_cleans_utm_params(self) -> None:
        """Test that add() cleans UTM parameters from URLs."""
        cache = Cache()
        url_with_utm = "https://example.com/article?utm_source=twitter&utm_medium=social"
        cache.add(url_with_utm, "article.md", "Article")

        # URL should be stored without UTM params
        assert "https://example.com/article" in cache.entries
        assert url_with_utm not in cache.entries

    def test_has_url_matches_cleaned_url(self) -> None:
        """Test that has_url() matches URLs regardless of UTM params."""
        cache = Cache()
        cache.add("https://example.com/article", "article.md", "Article")

        # Should match with or without UTM params
        assert cache.has_url("https://example.com/article") is True
        assert cache.has_url("https://example.com/article?utm_source=test") is True

    def test_has_active_url_matches_cleaned_url(self) -> None:
        """Test that has_active_url() matches URLs regardless of UTM params."""
        cache = Cache()
        cache.add("https://example.com/article", "article.md", "Article")

        assert cache.has_active_url("https://example.com/article?utm_campaign=test") is True

    def test_get_matches_cleaned_url(self) -> None:
        """Test that get() matches URLs regardless of UTM params."""
        cache = Cache()
        cache.add("https://example.com/article", "article.md", "Article")

        entry = cache.get("https://example.com/article?utm_source=newsletter")
        assert entry is not None
        assert entry.filename == "article.md"

    def test_update_location_with_utm_url(self) -> None:
        """Test that update_location() works with UTM params in URL."""
        cache = Cache()
        cache.add("https://example.com/article", "article.md", "Article")

        result = cache.update_location(
            "https://example.com/article?utm_source=test",
            folder="Tech",
        )
        assert result is not None
        assert result.folder == "Tech"

    def test_mark_removed_with_utm_url(self) -> None:
        """Test that mark_removed() works with UTM params in URL."""
        cache = Cache()
        cache.add("https://example.com/article", "article.md", "Article")

        result = cache.mark_removed("https://example.com/article?utm_medium=email")
        assert result is not None
        assert result.removed is True

    def test_remove_with_utm_url(self) -> None:
        """Test that remove() works with UTM params in URL."""
        cache = Cache()
        cache.add("https://example.com/article", "article.md", "Article")

        result = cache.remove("https://example.com/article?fbclid=test123")
        assert result is True
        assert len(cache.entries) == 0

    def test_add_updates_existing_with_utm_url(self) -> None:
        """Test that add() updates existing entry when URL has UTM params."""
        cache = Cache()
        cache.add("https://example.com/article", "old.md", "Old Title")
        cache.add("https://example.com/article?utm_source=new", "new.md", "New Title")

        # Should have only one entry
        assert len(cache.entries) == 1
        entry = cache.get("https://example.com/article")
        assert entry.filename == "new.md"
        assert entry.title == "New Title"

    def test_cleans_multiple_tracking_params(self) -> None:
        """Test that multiple tracking params are cleaned."""
        cache = Cache()
        messy_url = (
            "https://example.com/article"
            "?utm_source=twitter"
            "&utm_medium=social"
            "&utm_campaign=launch"
            "&utm_content=link"
            "&utm_term=keyword"
            "&fbclid=abc123"
            "&gclid=xyz789"
            "&ref=homepage"
        )
        cache.add(messy_url, "article.md", "Article")

        # Should be stored as clean URL
        assert "https://example.com/article" in cache.entries
        entry = cache.get(messy_url)
        assert entry is not None
