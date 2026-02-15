"""Core logic for extracting metadata from articles."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from clipmd.core.discovery import discover_markdown_files
from clipmd.core.frontmatter import (
    get_author,
    get_description,
    get_published_date,
    get_source_url,
    get_title,
    parse_frontmatter,
)
from clipmd.core.sanitizer import extract_domain

if TYPE_CHECKING:
    from clipmd.config import Config


@dataclass
class ArticleMetadata:
    """Metadata extracted from a single article."""

    index: int
    filename: str
    path: Path
    title: str | None = None
    url: str | None = None
    domain: str | None = None
    description: str | None = None
    author: str | None = None
    published: str | None = None
    word_count: int | None = None
    language: str | None = None
    error: str | None = None


@dataclass
class ExtractionResult:
    """Result of extracting metadata from articles."""

    generated: str
    total: int
    folders: list[str] = field(default_factory=list)
    articles: list[ArticleMetadata] = field(default_factory=list)
    errors: list[tuple[Path, str]] = field(default_factory=list)


def extract_article_metadata(
    path: Path,
    index: int,
    config: Config,
    max_chars: int = 150,
    include_content: bool = True,
    include_stats: bool = False,
) -> ArticleMetadata:
    """Extract metadata from a single article.

    Args:
        path: Path to the markdown file.
        index: Index number for the article.
        config: Application configuration.
        max_chars: Maximum characters for description preview.
        include_content: Include content preview if no description.
        include_stats: Include word count and language detection.

    Returns:
        ArticleMetadata with extracted fields.
    """
    metadata = ArticleMetadata(
        index=index,
        filename=path.name,
        path=path,
    )

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        metadata.error = f"Could not read file: {e}"
        return metadata

    # Parse frontmatter
    try:
        parsed = parse_frontmatter(content)
    except Exception as e:
        metadata.error = f"Could not parse frontmatter: {e}"
        return metadata

    # Extract fields
    metadata.title = get_title(parsed.data, config.frontmatter)
    metadata.url = get_source_url(parsed.data, config.frontmatter)
    metadata.author = get_author(parsed.data, config.frontmatter)

    if metadata.url:
        metadata.domain = extract_domain(metadata.url)

    # Get published date (already formatted as string)
    metadata.published = get_published_date(parsed.data, config.frontmatter)

    # Get description (from frontmatter or content)
    description = get_description(parsed.data, config.frontmatter)
    if description:
        if len(description) > max_chars:
            metadata.description = description[:max_chars] + "..."
        else:
            metadata.description = description
    elif include_content and parsed.content:
        # Use first part of content as description
        content_preview = parsed.content.strip()[:max_chars]
        if content_preview:
            if len(parsed.content.strip()) > max_chars:
                metadata.description = content_preview + "..."
            else:
                metadata.description = content_preview

    # Include stats if requested
    if include_stats:
        # Word count
        metadata.word_count = len(parsed.content.split())

        # Language detection (optional dependency)
        try:
            from langdetect import detect as detect_language

            if parsed.content.strip():
                metadata.language = detect_language(parsed.content)
        except ImportError:
            pass
        except Exception:
            pass

    return metadata


def get_existing_folders(path: Path, config: Config) -> list[str]:
    """Get list of existing folders in the articles directory.

    Args:
        path: Root directory to scan.
        config: Application configuration.

    Returns:
        List of folder names.
    """
    folders = []
    for item in path.iterdir():
        if not item.is_dir():
            continue

        # Check if folder matches exclude patterns
        exclude = False
        for pattern in config.special_folders.exclude_patterns:
            if item.name.startswith(pattern.replace("*", "")):
                exclude = True
                break
            if pattern.startswith(".") and item.name.startswith("."):
                exclude = True
                break

        if not exclude:
            folders.append(item.name)

    return sorted(folders)


def extract_metadata(
    path: Path,
    config: Config,
    max_chars: int = 150,
    include_content: bool = True,
    include_stats: bool = False,
    include_folders: bool = False,
) -> ExtractionResult:
    """Extract metadata from all articles in a directory.

    Args:
        path: Directory to scan.
        config: Application configuration.
        max_chars: Maximum characters for description preview.
        include_content: Include content preview if no description.
        include_stats: Include word count and language detection.
        include_folders: Include list of existing folders.

    Returns:
        ExtractionResult with all article metadata.
    """
    result = ExtractionResult(
        generated=datetime.now().isoformat(),
        total=0,
    )

    # Get existing folders
    if include_folders:
        result.folders = get_existing_folders(path, config)

    # Find all markdown files in root (not in subfolders)
    md_files = sorted(discover_markdown_files(path, config, recursive=False))

    result.total = len(md_files)

    # Extract metadata from each file
    for idx, md_file in enumerate(md_files, start=1):
        metadata = extract_article_metadata(
            md_file,
            idx,
            config,
            max_chars=max_chars,
            include_content=include_content,
            include_stats=include_stats,
        )

        if metadata.error:
            result.errors.append((md_file, metadata.error))
            continue

        result.articles.append(metadata)

    return result


def format_markdown(result: ExtractionResult, include_stats: bool = False) -> str:
    """Format extraction result as markdown.

    Args:
        result: Extraction result to format.
        include_stats: Whether stats were included.

    Returns:
        Formatted markdown string.
    """
    lines = [
        "# Articles Metadata",
        f"# Generated: {result.generated}",
        f"# Total: {result.total} articles",
        "",
    ]

    if result.folders:
        lines.extend(
            [
                "## Existing Folders",
                ", ".join(result.folders),
                "",
            ]
        )

    if result.articles:
        lines.extend(
            [
                f"## Articles ({len(result.articles)} articles)",
                "",
            ]
        )
        for meta in result.articles:
            lines.append(f"{meta.index}. {meta.filename}")

            # Build URL line with optional stats
            parts = []
            if meta.domain:
                parts.append(f"URL: {meta.domain}")
            if include_stats:
                if meta.word_count:
                    parts.append(f"{meta.word_count:,} words")
                if meta.language:
                    parts.append(meta.language)
            if parts:
                lines.append(f"   {' | '.join(parts)}")

            if meta.title:
                lines.append(f"   Title: {meta.title}")
            if meta.description:
                lines.append(f"   Desc: {meta.description}")
            lines.append("")

    if result.errors:
        lines.extend(
            [
                f"## Errors ({len(result.errors)} files)",
                "",
            ]
        )
        for file_path, error in result.errors:
            lines.append(f"- {file_path.name}: {error}")

    return "\n".join(lines)


def format_json(result: ExtractionResult) -> str:
    """Format extraction result as JSON.

    Args:
        result: Extraction result to format.

    Returns:
        Formatted JSON string.
    """
    data = {
        "generated": result.generated,
        "total": result.total,
        "folders": result.folders,
        "articles": [
            {
                k: v
                for k, v in {
                    "index": m.index,
                    "filename": m.filename,
                    "url": m.url,
                    "domain": m.domain,
                    "title": m.title,
                    "description": m.description,
                    "author": m.author,
                    "published": m.published,
                    "word_count": m.word_count,
                    "language": m.language,
                }.items()
                if v is not None
            }
            for m in result.articles
        ],
    }

    if result.errors:
        data["errors"] = [{"filename": p.name, "error": e} for p, e in result.errors]

    return json.dumps(data, indent=2)


def format_yaml_output(result: ExtractionResult) -> str:
    """Format extraction result as YAML.

    Args:
        result: Extraction result to format.

    Returns:
        Formatted YAML string.
    """
    data = {
        "generated": result.generated,
        "total": result.total,
        "folders": result.folders,
        "articles": [
            {
                k: v
                for k, v in {
                    "index": m.index,
                    "filename": m.filename,
                    "url": m.url,
                    "domain": m.domain,
                    "title": m.title,
                    "description": m.description,
                    "author": m.author,
                    "published": m.published,
                    "word_count": m.word_count,
                    "language": m.language,
                }.items()
                if v is not None
            }
            for m in result.articles
        ],
    }

    if result.errors:
        data["errors"] = [{"filename": p.name, "error": e} for p, e in result.errors]

    return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
