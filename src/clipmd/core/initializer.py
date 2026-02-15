"""Core initialization logic for clipmd vault setup."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

from clipmd.config import save_default_vault
from clipmd.core.discovery import discover_markdown_files

if TYPE_CHECKING:
    pass


@dataclass
class InitResult:
    """Result of vault initialization."""

    config_path: Path
    clipmd_dir: Path
    markdown_file_count: int
    vault_path: Path | None = None


def get_minimal_config() -> str:
    """Get minimal configuration content.

    Returns:
        Minimal YAML configuration.
    """
    return dedent("""\
        # clipmd minimal configuration
        version: 1

        paths:
          root: "."
        """)


def get_full_config() -> str:
    """Get full configuration content with all options.

    Returns:
        Full YAML configuration.
    """
    return dedent("""\
        # clipmd configuration
        version: 1

        # =============================================================================
        # PATHS
        # =============================================================================
        paths:
          root: "."                           # Root articles directory
          cache: ".clipmd/cache.json"         # URL/content cache

        # Special folders (leave patterns empty if you don't want any)
        special_folders:
          # Folders to exclude from statistics and reorganization
          exclude_patterns:
            - "0-*"        # Folders starting with "0-"
            - ".*"         # Hidden folders
            - "_*"         # Folders starting with "_"

          # Files to ignore in all commands
          ignore_files:
            - "README.md"
            - "CLAUDE.md"

        # =============================================================================
        # FRONTMATTER FIELD MAPPING
        # =============================================================================
        # Map semantic fields to actual field names in your files
        # Tool will try each name in order until one is found
        frontmatter:
          source_url:
            - source
            - url
            - link
            - original_url
            - clip_url

          title:
            - title
            - name

          published_date:
            - published
            - date
            - publish_date

          clipped_date:
            - clipped
            - saved
            - created
            - added

          author:
            - author
            - by
            - writer
            - creator

          description:
            - description
            - summary
            - excerpt
            - abstract

        # =============================================================================
        # DATE HANDLING
        # =============================================================================
        dates:
          # Date formats to try when parsing (in order)
          input_formats:
            - "%Y-%m-%d"           # 2024-01-17
            - "%Y-%m-%dT%H:%M:%S"  # 2024-01-17T14:30:00
            - "%d/%m/%Y"           # 17/01/2024
            - "%B %d, %Y"          # January 17, 2024
            - "%d %B %Y"           # 17 January 2024
            - "%Y/%m/%d"           # 2024/01/17

          # Output format for date prefixes
          output_format: "%Y%m%d"  # 20240117

          # Field priority for date prefix (first found is used)
          prefix_priority:
            - published
            - clipped
            - created

          # Extract dates from article body when frontmatter fields are empty
          extract_from_content: true

        # =============================================================================
        # URL CLEANING
        # =============================================================================
        url_cleaning:
          # Tracking parameters to remove
          remove_params:
            - utm_source
            - utm_medium
            - utm_campaign
            - utm_content
            - utm_term
            - fbclid
            - gclid
            - ref
            - source

        # =============================================================================
        # FILENAME SANITIZATION
        # =============================================================================
        filenames:
          # Normalize unicode (NFC, NFD, NFKC, NFKD, or null)
          unicode_normalize: "NFC"

          # Convert to lowercase
          lowercase: false

          # Max filename length (including extension)
          max_length: 100

          # Collapse multiple dashes
          collapse_dashes: true

        # =============================================================================
        # FOLDER STATISTICS
        # =============================================================================
        folders:
          # Warning thresholds (set to null to disable)
          warn_below: 10    # Warn if folder has fewer articles
          warn_above: 45    # Warn if folder has more articles

        # =============================================================================
        # CACHE SETTINGS
        # =============================================================================
        cache:
          # What to track
          track_urls: true
          track_content_hash: true

          # Truncate hash to N characters (null for full hash)
          hash_length: 16

        # =============================================================================
        # FETCH SETTINGS
        # =============================================================================
        fetch:
          # Request settings
          timeout: 30                    # Timeout in seconds
          user_agent: "clipmd/0.1"       # User-Agent header
          max_concurrent: 5              # Max parallel fetches (async)

          # Retry settings
          max_retries: 3
          retry_delay: 1                 # Seconds between retries

          # Content extraction
          extract_metadata: true         # Try to extract title, author, date

          # Readability mode - extract main content only
          readability: true

        # =============================================================================
        # OUTPUT FORMATS
        # =============================================================================
        output:
          # Default format for metadata extraction
          metadata_format: "markdown"  # markdown, json, yaml

          # Include content preview in metadata
          include_content: true
          max_content_chars: 150

          # Statistics output
          stats_format: "table"  # table, json, yaml
        """)


def initialize_vault(
    config_path: Path,
    minimal: bool,
    force: bool,
    set_default: bool,
) -> InitResult:
    """Initialize clipmd vault with config and directories.

    Args:
        config_path: Path where config file should be created.
        minimal: If True, create minimal config; otherwise full config.
        force: If True, overwrite existing config.
        set_default: If True, set this vault as default in XDG config.

    Returns:
        InitResult with paths and file count information.
    """
    # Check if config already exists
    if config_path.exists() and not force:
        raise FileExistsError(f"Config file already exists: {config_path}")

    # Create .clipmd directory
    clipmd_dir = Path(".clipmd")
    clipmd_dir.mkdir(exist_ok=True)

    # Write config file
    config_content = get_minimal_config() if minimal else get_full_config()
    config_path.write_text(config_content, encoding="utf-8")

    # Count existing markdown files (excluding hidden and ignored files)
    from clipmd.config import Config

    default_config = Config()
    md_files = list(discover_markdown_files(Path("."), default_config))

    # Save as default vault if requested
    vault_path = None
    if set_default:
        vault_path = Path.cwd().resolve()
        save_default_vault(vault_path)

    return InitResult(
        config_path=config_path,
        clipmd_dir=clipmd_dir,
        markdown_file_count=len(md_files),
        vault_path=vault_path,
    )
