"""URL and content cache for clipmd."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from clipmd.core.hasher import hash_content
from clipmd.core.sanitizer import clean_url

if TYPE_CHECKING:
    from clipmd.config import CacheConfig, Config
    from clipmd.core.fetcher import FetchResult


@dataclass
class CacheEntry:
    """A single cache entry for an article."""

    filename: str
    title: str
    folder: str | None = None
    first_seen: str = ""
    last_seen: str = ""
    removed: bool = False
    removed_at: str | None = None
    content_hash: str | None = None

    def __post_init__(self) -> None:
        """Set default dates if not provided."""
        if not self.first_seen:
            self.first_seen = datetime.now().strftime("%Y-%m-%d")
        if not self.last_seen:
            self.last_seen = datetime.now().strftime("%Y-%m-%d")

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, object] = {
            "filename": self.filename,
            "title": self.title,
            "folder": self.folder,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "removed": self.removed,
            "content_hash": self.content_hash,
        }
        if self.removed_at:
            result["removed_at"] = self.removed_at
        return result

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> CacheEntry:
        """Create from dictionary."""
        return cls(
            filename=str(data.get("filename", "")),
            title=str(data.get("title", "")),
            folder=str(data["folder"]) if data.get("folder") else None,
            first_seen=str(data.get("first_seen", "")),
            last_seen=str(data.get("last_seen", "")),
            removed=bool(data.get("removed", False)),
            removed_at=str(data["removed_at"]) if data.get("removed_at") else None,
            content_hash=str(data["content_hash"]) if data.get("content_hash") else None,
        )


@dataclass
class Cache:
    """URL/content cache for clipmd."""

    version: int = 1
    updated: str = ""
    entries: dict[str, CacheEntry] = field(default_factory=dict)
    _path: Path | None = None

    def __post_init__(self) -> None:
        """Set default updated time if not provided."""
        if not self.updated:
            self.updated = datetime.now(UTC).isoformat()

    def get(self, url: str) -> CacheEntry | None:
        """Get cache entry by URL.

        Args:
            url: The URL to look up (will be cleaned of tracking params).

        Returns:
            CacheEntry if found, None otherwise.
        """
        cleaned_url = clean_url(url)
        return self.entries.get(cleaned_url)

    def has_url(self, url: str) -> bool:
        """Check if URL exists in cache (active or removed).

        Args:
            url: The URL to check (will be cleaned of tracking params).

        Returns:
            True if URL is in cache.
        """
        cleaned_url = clean_url(url)
        return cleaned_url in self.entries

    def has_active_url(self, url: str) -> bool:
        """Check if URL exists in cache and is not removed.

        Args:
            url: The URL to check (will be cleaned of tracking params).

        Returns:
            True if URL is in cache and not removed.
        """
        cleaned_url = clean_url(url)
        entry = self.entries.get(cleaned_url)
        return entry is not None and not entry.removed

    def add(
        self,
        url: str,
        filename: str,
        title: str,
        folder: str | None = None,
        content_hash: str | None = None,
    ) -> CacheEntry:
        """Add or update a cache entry.

        Args:
            url: The article URL (will be cleaned of tracking params).
            filename: The article filename.
            title: The article title.
            folder: Optional folder location.
            content_hash: Optional content hash.

        Returns:
            The created or updated CacheEntry.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        cleaned_url = clean_url(url)

        if cleaned_url in self.entries:
            # Update existing entry
            entry = self.entries[cleaned_url]
            entry.filename = filename
            entry.title = title
            entry.folder = folder
            entry.last_seen = today
            entry.removed = False
            entry.removed_at = None
            if content_hash:
                entry.content_hash = content_hash
        else:
            # Create new entry
            entry = CacheEntry(
                filename=filename,
                title=title,
                folder=folder,
                first_seen=today,
                last_seen=today,
                content_hash=content_hash,
            )
            self.entries[cleaned_url] = entry

        self._mark_updated()
        return entry

    def update_location(
        self,
        url: str,
        filename: str | None = None,
        folder: str | None = None,
    ) -> CacheEntry | None:
        """Update the location of a cached article.

        Args:
            url: The article URL (will be cleaned of tracking params).
            filename: New filename (optional).
            folder: New folder location (optional).

        Returns:
            Updated CacheEntry if found, None otherwise.
        """
        cleaned_url = clean_url(url)
        entry = self.entries.get(cleaned_url)
        if entry is None:
            return None

        if filename is not None:
            entry.filename = filename
        if folder is not None:
            entry.folder = folder
        entry.last_seen = datetime.now().strftime("%Y-%m-%d")
        self._mark_updated()
        return entry

    def mark_removed(self, url: str) -> CacheEntry | None:
        """Mark a cache entry as removed.

        Args:
            url: The URL to mark as removed (will be cleaned of tracking params).

        Returns:
            Updated CacheEntry if found, None otherwise.
        """
        cleaned_url = clean_url(url)
        entry = self.entries.get(cleaned_url)
        if entry is None:
            return None

        entry.removed = True
        entry.removed_at = datetime.now(UTC).isoformat()
        self._mark_updated()
        return entry

    def remove(self, url: str) -> bool:
        """Completely remove a cache entry.

        Args:
            url: The URL to remove (will be cleaned of tracking params).

        Returns:
            True if entry was removed, False if not found.
        """
        cleaned_url = clean_url(url)
        if cleaned_url in self.entries:
            del self.entries[cleaned_url]
            self._mark_updated()
            return True
        return False

    def find_by_filename(self, filename: str) -> tuple[str, CacheEntry] | None:
        """Find cache entry by filename.

        Args:
            filename: The filename to search for.

        Returns:
            Tuple of (url, entry) if found, None otherwise.
        """
        for url, entry in self.entries.items():
            if entry.filename == filename and not entry.removed:
                return (url, entry)
        return None

    def find_by_hash(self, content_hash: str) -> list[tuple[str, CacheEntry]]:
        """Find cache entries by content hash.

        Args:
            content_hash: The hash to search for.

        Returns:
            List of (url, entry) tuples with matching hash.
        """
        results = []
        for url, entry in self.entries.items():
            if entry.content_hash == content_hash and not entry.removed:
                results.append((url, entry))
        return results

    def get_active_entries(self) -> dict[str, CacheEntry]:
        """Get all non-removed entries.

        Returns:
            Dictionary of active entries.
        """
        return {url: entry for url, entry in self.entries.items() if not entry.removed}

    def get_removed_entries(self) -> dict[str, CacheEntry]:
        """Get all removed entries.

        Returns:
            Dictionary of removed entries.
        """
        return {url: entry for url, entry in self.entries.items() if entry.removed}

    def get_entries_by_folder(self) -> dict[str | None, list[tuple[str, CacheEntry]]]:
        """Group active entries by folder.

        Returns:
            Dictionary mapping folder to list of (url, entry) tuples.
        """
        by_folder: dict[str | None, list[tuple[str, CacheEntry]]] = {}
        for url, entry in self.entries.items():
            if not entry.removed:
                folder = entry.folder
                if folder not in by_folder:
                    by_folder[folder] = []
                by_folder[folder].append((url, entry))
        return by_folder

    def clean(self, existing_files: set[str]) -> int:
        """Remove entries for files that no longer exist.

        Args:
            existing_files: Set of filenames that currently exist.

        Returns:
            Number of entries removed.
        """
        urls_to_remove = []
        for url, entry in self.entries.items():
            if not entry.removed and entry.filename not in existing_files:
                urls_to_remove.append(url)

        for url in urls_to_remove:
            self.mark_removed(url)

        return len(urls_to_remove)

    def clear(self) -> None:
        """Clear all entries."""
        self.entries.clear()
        self._mark_updated()

    def _mark_updated(self) -> None:
        """Update the timestamp."""
        self.updated = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "updated": self.updated,
            "entries": {url: entry.to_dict() for url, entry in self.entries.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Cache:
        """Create from dictionary."""
        entries: dict[str, CacheEntry] = {}
        raw_entries = data.get("entries", {})
        if isinstance(raw_entries, dict):
            for url, entry_data in raw_entries.items():
                if isinstance(url, str) and isinstance(entry_data, dict):
                    entries[url] = CacheEntry.from_dict({str(k): v for k, v in entry_data.items()})

        version_raw = data.get("version", 1)
        version = int(version_raw) if isinstance(version_raw, (int, str)) else 1

        return cls(
            version=version,
            updated=str(data.get("updated", "")),
            entries=entries,
        )

    def save(self, path: Path | None = None) -> None:
        """Save cache to file.

        Args:
            path: Path to save to. Uses stored path if not provided.

        Raises:
            ValueError: If no path provided and no stored path.
            OSError: If file cannot be written.
        """
        save_path = path or self._path
        if save_path is None:
            raise ValueError("No path provided for saving cache")

        # Ensure parent directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with save_path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

        self._path = save_path

    @classmethod
    def load(cls, path: Path) -> Cache:
        """Load cache from file.

        Args:
            path: Path to load from.

        Returns:
            Loaded Cache object, or empty cache if file doesn't exist.
        """
        if not path.exists():
            cache = cls()
            cache._path = path
            return cache

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        cache = cls.from_dict(data)
        cache._path = path
        return cache


def load_cache(path: Path | None = None, _config: CacheConfig | None = None) -> Cache:
    """Load cache from configured path.

    Args:
        path: Explicit path to load from.
        _config: Cache configuration (reserved for future use).

    Returns:
        Loaded Cache object.
    """
    if path is None:
        path = Path(".clipmd/cache.json")

    return Cache.load(path)


@dataclass
class FilterResult:
    """Result of filtering duplicate URLs."""

    filtered_urls: list[str]
    skipped_urls: list[str] = field(default_factory=list)


def filter_duplicate_urls(
    urls: list[str],
    config: Config,
) -> FilterResult:
    """Filter URLs already in cache.

    Args:
        urls: List of URLs to filter.
        config: Application configuration.

    Returns:
        FilterResult with filtered and skipped URLs.
    """
    cache_path = config.paths.root / config.paths.cache
    cache = load_cache(cache_path)

    filtered_urls = []
    skipped_urls = []

    for url in urls:
        if cache.has_active_url(url):
            skipped_urls.append(url)
        else:
            filtered_urls.append(url)

    return FilterResult(
        filtered_urls=filtered_urls,
        skipped_urls=skipped_urls,
    )


def update_cache_after_fetch(
    results: list[FetchResult],
    config: Config,
) -> None:
    """Update cache with fetched URLs.

    Args:
        results: List of fetch results.
        config: Application configuration.
    """
    cache_path = config.paths.root / config.paths.cache
    cache = load_cache(cache_path)

    for result in results:
        if result.success and result.filename:
            content_hash = hash_content(result.content or "")
            # Use final URL (after redirects) for cache
            cache_url = result.final_url or result.url
            cache.add(
                url=cache_url,
                filename=result.filename,
                title=result.title or "Untitled",
                content_hash=content_hash,
            )

    cache.save()
