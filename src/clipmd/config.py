"""Configuration loading and validation for clipmd."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from clipmd.exceptions import ConfigError

# XDG Base Directory specification
XDG_CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


class PathsConfig(BaseModel):
    """Configuration for file paths."""

    root: Path = Path(".")
    cache: Path = Path(".clipmd/cache.json")


class SpecialFoldersConfig(BaseModel):
    """Configuration for special folder handling."""

    exclude_patterns: list[str] = Field(default_factory=lambda: ["0-*", ".*", "_*"])
    ignore_files: list[str] = Field(default_factory=lambda: ["README.md", "CLAUDE.md"])


class FrontmatterConfig(BaseModel):
    """Configuration for frontmatter field mapping."""

    source_url: list[str] = Field(
        default_factory=lambda: ["source", "url", "link", "original_url", "clip_url"]
    )
    title: list[str] = Field(default_factory=lambda: ["title", "name"])
    published_date: list[str] = Field(default_factory=lambda: ["published", "date", "publish_date"])
    clipped_date: list[str] = Field(
        default_factory=lambda: ["clipped", "saved", "created", "added"]
    )
    author: list[str] = Field(default_factory=lambda: ["author", "by", "writer", "creator"])
    description: list[str] = Field(
        default_factory=lambda: ["description", "summary", "excerpt", "abstract"]
    )


class DatesConfig(BaseModel):
    """Configuration for date handling."""

    input_formats: list[str] = Field(
        default_factory=lambda: [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%d/%m/%Y",
            "%B %d, %Y",
            "%d %B %Y",
            "%Y/%m/%d",
        ]
    )
    output_format: str = "%Y%m%d"
    prefix_priority: list[str] = Field(default_factory=lambda: ["published", "clipped", "created"])
    extract_from_content: bool = True
    content_patterns: list[str] = Field(
        default_factory=lambda: [
            r"(?P<day>\d{1,2})(?:st|nd|rd|th)?\s+(?P<month>\w+)\s+(?P<year>\d{4})",
            r"(?P<month>\w+)\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?,?\s+(?P<year>\d{4})",
            r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})",
        ]
    )


class UrlCleaningConfig(BaseModel):
    """Configuration for URL cleaning."""

    remove_params: list[str] = Field(
        default_factory=lambda: [
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_content",
            "utm_term",
            "fbclid",
            "gclid",
            "ref",
            "source",
        ]
    )
    unwrap_patterns: list[dict[str, str | int]] = Field(default_factory=list)


class FilenamesConfig(BaseModel):
    """Configuration for filename sanitization."""

    replacements: dict[str, str] = Field(
        default_factory=lambda: {
            " ": "-",
            "_": "-",
            "'": "",
            '"': "",
            ":": "-",
            "/": "-",
            "\\": "-",
            "|": "-",
            "?": "",
            "*": "",
            "<": "",
            ">": "",
        }
    )
    unicode_normalize: Literal["NFC", "NFD", "NFKC", "NFKD"] | None = "NFC"
    lowercase: bool = False
    max_length: int = 100
    collapse_dashes: bool = True


class ContentCleaningPatternConfig(BaseModel):
    """Configuration for a single content cleaning pattern."""

    name: str
    pattern: str
    flags: str = "im"


class ContentCleaningConfig(BaseModel):
    """Configuration for content cleaning."""

    enabled: bool = False
    patterns: list[ContentCleaningPatternConfig] = Field(default_factory=list)


class FoldersConfig(BaseModel):
    """Configuration for folder statistics."""

    warn_below: int | None = 10
    warn_above: int | None = 45


class CacheConfig(BaseModel):
    """Configuration for cache settings."""

    track_urls: bool = True
    track_content_hash: bool = True
    hash_length: int | None = 16


class FetchConfig(BaseModel):
    """Configuration for URL fetching."""

    timeout: int = 30
    user_agent: str = "clipmd/0.1"
    max_concurrent: int = 5
    max_retries: int = 3
    retry_delay: int = 1
    extract_metadata: bool = True
    include_images: bool = False
    readability: bool = True
    frontmatter_template: str = Field(
        default="""title: "{title}"
source: "{url}"
author: "{author}"
published: "{published}"
clipped: "{clipped}"
description: "{description}"
"""
    )
    filename_template: str = "{date}-{title}"
    defaults: dict[str, str] = Field(
        default_factory=lambda: {
            "author": "",
            "published": "",
            "description": "",
        }
    )


class OutputConfig(BaseModel):
    """Configuration for output formats."""

    metadata_format: Literal["markdown", "json", "yaml"] = "markdown"
    include_content: bool = True
    max_content_chars: int = 150
    stats_format: Literal["table", "json", "yaml"] = "table"


class Config(BaseModel):
    """Main configuration for clipmd."""

    version: int = 1
    default_vault: Path | None = None  # Path to default vault (used from XDG config)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    special_folders: SpecialFoldersConfig = Field(default_factory=SpecialFoldersConfig)
    frontmatter: FrontmatterConfig = Field(default_factory=FrontmatterConfig)
    dates: DatesConfig = Field(default_factory=DatesConfig)
    url_cleaning: UrlCleaningConfig = Field(default_factory=UrlCleaningConfig)
    filenames: FilenamesConfig = Field(default_factory=FilenamesConfig)
    content_cleaning: ContentCleaningConfig = Field(default_factory=ContentCleaningConfig)
    folders: FoldersConfig = Field(default_factory=FoldersConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    fetch: FetchConfig = Field(default_factory=FetchConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)


def get_xdg_config_home() -> Path:
    """Get the XDG config home directory.

    Returns:
        Path to the XDG config home (respects XDG_CONFIG_HOME env var).
    """
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def find_config_file(config_path: Path | None = None) -> Path | None:
    """Find the configuration file using XDG conventions.

    Search order (first found wins):
    1. --config PATH (command line override)
    2. ./config.yaml (current directory)
    3. ./.clipmd/config.yaml (project directory)
    4. $XDG_CONFIG_HOME/clipmd/config.yaml (typically ~/.config/clipmd/config.yaml)

    Args:
        config_path: Optional explicit config path from command line.

    Returns:
        Path to config file if found, None otherwise.
    """
    if config_path is not None:
        if config_path.exists():
            return config_path
        raise ConfigError(f"Config file not found: {config_path}")

    # Check current directory
    cwd_config = Path("config.yaml")
    if cwd_config.exists():
        return cwd_config

    # Check .clipmd directory
    clipmd_config = Path(".clipmd/config.yaml")
    if clipmd_config.exists():
        return clipmd_config

    # Check XDG config home
    xdg_config = get_xdg_config_home() / "clipmd" / "config.yaml"
    if xdg_config.exists():
        return xdg_config

    return None


def load_config(config_path: Path | None = None) -> Config:
    """Load configuration from file or return defaults.

    Args:
        config_path: Optional explicit config path.

    Returns:
        Config object with loaded or default values.

    Raises:
        ConfigError: If config file exists but is invalid.
    """
    found_path = find_config_file(config_path)

    if found_path is None:
        return Config()

    try:
        with found_path.open() as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in config file: {e}") from e
    except OSError as e:
        raise ConfigError(f"Could not read config file: {e}") from e

    if data is None:
        return Config()

    try:
        return Config.model_validate(data)
    except ValueError as e:
        raise ConfigError(f"Invalid configuration: {e}") from e


def get_xdg_config_path() -> Path:
    """Get the XDG config file path.

    Returns:
        Path to the XDG config file (~/.config/clipmd/config.yaml).
    """
    return get_xdg_config_home() / "clipmd" / "config.yaml"


def load_xdg_config() -> dict | None:
    """Load the XDG config file if it exists.

    Returns:
        Parsed YAML data or None if file doesn't exist.
    """
    xdg_config = get_xdg_config_path()
    if not xdg_config.exists():
        return None

    try:
        with xdg_config.open() as f:
            return yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError):
        return None


def save_default_vault(vault_path: Path) -> None:
    """Save the default vault path to XDG config.

    Creates or updates the XDG config file with the default_vault setting.

    Args:
        vault_path: Absolute path to the vault directory.
    """
    xdg_config = get_xdg_config_path()
    xdg_config.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config or create new
    data = load_xdg_config() or {"version": 1}

    # Update default_vault
    data["default_vault"] = str(vault_path.resolve())

    # Write back
    with xdg_config.open("w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


def get_default_vault() -> Path | None:
    """Get the default vault path from XDG config.

    Returns:
        Path to the default vault or None if not configured.
    """
    data = load_xdg_config()
    if data and "default_vault" in data:
        vault_path = Path(data["default_vault"])
        if vault_path.exists() and vault_path.is_dir():
            return vault_path
    return None


def resolve_vault_root(config: Config, vault_override: Path | None = None) -> Path:
    """Resolve the effective vault root directory.

    Priority:
    1. Explicit vault override (from --vault CLI option)
    2. Config's paths.root if it's absolute
    3. Config's default_vault if set
    4. Default vault from XDG config
    5. Current working directory with relative paths.root

    Args:
        config: Application configuration.
        vault_override: Optional vault path override from CLI.

    Returns:
        Resolved absolute path to the vault root.
    """
    # 1. Explicit override
    if vault_override is not None:
        return vault_override.resolve()

    # 2. Absolute paths.root
    if config.paths.root.is_absolute():
        return config.paths.root

    # 3. Config's default_vault
    if config.default_vault is not None and config.default_vault.exists():
        return config.default_vault

    # 4. XDG default vault
    xdg_vault = get_default_vault()
    if xdg_vault is not None:
        return xdg_vault

    # 5. Current directory with relative root
    return Path.cwd() / config.paths.root
