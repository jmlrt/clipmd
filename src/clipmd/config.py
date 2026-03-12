"""Configuration loading and validation for clipmd."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from clipmd.exceptions import ConfigError


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


class Config(BaseModel):
    """Main configuration for clipmd."""

    version: int = 1
    vault: Path | None = None  # Path to the vault (required when using clipmd)
    cache: Path | None = None  # Path to the cache file
    special_folders: SpecialFoldersConfig = Field(default_factory=SpecialFoldersConfig)
    frontmatter: FrontmatterConfig = Field(default_factory=FrontmatterConfig)
    dates: DatesConfig = Field(default_factory=DatesConfig)
    url_cleaning: UrlCleaningConfig = Field(default_factory=UrlCleaningConfig)
    filenames: FilenamesConfig = Field(default_factory=FilenamesConfig)
    folders: FoldersConfig = Field(default_factory=FoldersConfig)
    cache_config: CacheConfig = Field(default_factory=CacheConfig)
    fetch: FetchConfig = Field(default_factory=FetchConfig)

    def model_post_init(self, __context: object) -> None:
        """Expand environment variables and user home in vault and cache paths.

        Resolves relative cache paths against the vault path (if configured).
        """
        del __context  # Unused, required by pydantic interface

        # Normalize vault path
        if self.vault is not None:
            vault_str = str(self.vault)
            self.vault = Path(os.path.expandvars(vault_str)).expanduser()

        # Normalize cache path and relate it to vault when relative
        if self.cache is not None:
            cache_str = str(self.cache)
            cache_path = Path(os.path.expandvars(cache_str)).expanduser()

            if cache_path.is_absolute():
                self.cache = cache_path
            else:
                if self.vault is None:
                    raise ConfigError(
                        "Relative cache path configured without a vault path. "
                        "Either provide an absolute 'cache' path or set 'vault' so "
                        "the cache path can be resolved relative to it."
                    )
                # Resolve relative cache path against vault
                self.cache = self.vault / cache_path


def get_xdg_config_home() -> Path:
    """Get the XDG config home directory.

    Returns:
        Path to the XDG config home (respects XDG_CONFIG_HOME env var).
    """
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def get_config_file_path(config_path: Path | None = None) -> Path:
    """Get the configuration file path.

    With the simplified config approach, there is a single canonical location:
    $XDG_CONFIG_HOME/clipmd/config.yaml (typically ~/.config/clipmd/config.yaml)

    Args:
        config_path: Optional explicit config path from command line.

    Returns:
        Path to config file.

    Raises:
        ConfigError: If explicit config_path is provided but doesn't exist.
    """
    if config_path is not None:
        if config_path.exists():
            return config_path
        raise ConfigError(f"Config file not found: {config_path}")

    # Default to XDG config location
    return get_xdg_config_home() / "clipmd" / "config.yaml"


def load_config(config_path: Path | None = None) -> Config:
    """Load configuration from $XDG_CONFIG_HOME/clipmd/config.yaml or return defaults.

    The config file location follows XDG Base Directory Specification:
    - Checks $XDG_CONFIG_HOME/clipmd/config.yaml (typically ~/.config/clipmd/config.yaml)
    - Falls back to default ~/.config/clipmd/config.yaml if XDG_CONFIG_HOME is not set

    Args:
        config_path: Optional explicit config path override.

    Returns:
        Config object with loaded or default values.

    Raises:
        ConfigError: If config file exists but is invalid, or vault/cache are not configured.
    """
    config_file = get_config_file_path(config_path)

    # If config file doesn't exist, return defaults
    if not config_file.exists():
        return Config()

    try:
        with config_file.open() as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in config file {config_file}: {e}") from e
    except OSError as e:
        raise ConfigError(f"Could not read config file {config_file}: {e}") from e

    if data is None:
        return Config()

    try:
        config = Config.model_validate(data)

        # Validate that vault and cache are configured
        if config.vault is None:
            raise ConfigError(
                f"Configuration file {config_file} must specify 'vault' path. "
                f"Example:\n  vault: $HOME/Documents/Articles\n  cache: $HOME/.cache/clipmd/cache.json"
            )
        if config.cache is None:
            raise ConfigError(
                f"Configuration file {config_file} must specify 'cache' path. "
                f"Example:\n  vault: $HOME/Documents/Articles\n  cache: $HOME/.cache/clipmd/cache.json"
            )

        return config
    except ValueError as e:
        raise ConfigError(f"Invalid configuration in {config_file}: {e}") from e
