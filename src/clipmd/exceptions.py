"""Custom exceptions for clipmd."""

from __future__ import annotations


class ClipmdError(Exception):
    """Base exception for all clipmd errors."""

    exit_code: int = 1


class ConfigError(ClipmdError):
    """Configuration file errors."""


class FetchError(ClipmdError):
    """URL fetching errors."""


class ParseError(ClipmdError):
    """Frontmatter/content parsing errors."""


class CacheError(ClipmdError):
    """Cache read/write errors."""


class ValidationError(ClipmdError):
    """Input validation errors."""


class PartialSuccessError(ClipmdError):
    """Some operations succeeded, some failed."""

    exit_code: int = 2
