"""URL and filename sanitization for clipmd.

Note: We use custom sanitize_filename() rather than python-slugify because:
- NFD Unicode normalization required (not supported by library)
- Extension-aware max_length truncation needed
- Backward compatibility with existing vault filenames
"""

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

if TYPE_CHECKING:
    from clipmd.config import FilenamesConfig, UrlCleaningConfig


def clean_url(
    url: str,
    config: UrlCleaningConfig | None = None,
) -> str:
    """Clean tracking parameters from URL.

    Removes query parameters like UTM tracking codes, removes URL fragments,
    and optionally removes trailing slashes.

    Args:
        url: The URL to clean.
        config: URL cleaning configuration.

    Returns:
        Cleaned URL with tracking parameters removed.
    """
    if config is None:
        # Default parameters to remove
        remove_params = {
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_content",
            "utm_term",
            "fbclid",
            "gclid",
            "ref",
            "source",
        }
    else:
        # Normalize configured parameters to lowercase for consistent matching
        remove_params = {p.lower() for p in config.remove_params}

    parsed = urlparse(url)

    # Parse query parameters
    query_params = parse_qs(parsed.query, keep_blank_values=True)

    # Remove tracking parameters
    cleaned_params = {k: v for k, v in query_params.items() if k.lower() not in remove_params}

    # Rebuild query string
    new_query = urlencode(cleaned_params, doseq=True) if cleaned_params else ""

    # Rebuild URL
    cleaned = urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            "",  # Remove fragment
        )
    )

    # Remove trailing slash for consistency (but keep for root paths)
    if cleaned.endswith("/") and parsed.path != "/":
        cleaned = cleaned.rstrip("/")

    return cleaned


def extract_domain(url: str) -> str:
    """Extract the domain from a URL.

    Args:
        url: The URL to parse.

    Returns:
        The domain (netloc) portion of the URL.
    """
    parsed = urlparse(url)
    return parsed.netloc


def sanitize_filename(
    filename: str,
    config: FilenamesConfig | None = None,
) -> str:
    """Sanitize a filename for safe filesystem use.

    Only allows A-Za-z0-9, dash (-), and dot (.) characters.
    Accented letters are replaced with their non-accented equivalents.
    All other characters are replaced with dashes.

    Args:
        filename: The filename to sanitize.
        config: Filename configuration.

    Returns:
        Sanitized filename.
    """
    if config is None:
        # When no configuration is provided, use FilenamesConfig defaults
        # but override unicode_normalize to NFD to preserve backward compatibility
        from clipmd.config import FilenamesConfig

        config = FilenamesConfig(unicode_normalize="NFD")

    # Derive behavior from the configuration (or its defaults)
    lowercase = getattr(config, "lowercase", False)
    max_length = getattr(config, "max_length", 100)
    collapse_dashes = getattr(config, "collapse_dashes", True)
    # Allow configuration of Unicode normalization form
    unicode_form = getattr(config, "unicode_normalize", "NFD")
    # Optional custom replacements applied before normalization
    replacements = getattr(config, "replacements", None)

    # Apply configured replacements before Unicode normalization, if any
    result = filename
    if replacements:
        for old, new in replacements.items():
            result = result.replace(old, new)

    # Normalize unicode according to configuration (default NFD)
    if unicode_form:
        result = unicodedata.normalize(unicode_form, result)

    # Remove combining characters (accents) - category Mn (Mark, nonspacing)
    result = "".join(char for char in result if unicodedata.category(char) != "Mn")

    # Replace any character that is NOT alphanumeric, dash, or dot with dash
    result = re.sub(r"[^A-Za-z0-9.\-]", "-", result)

    # Collapse multiple dashes
    if collapse_dashes:
        result = re.sub(r"-+", "-", result)

    # Remove leading/trailing dashes (handling extension separately)
    if "." in result:
        name, ext = result.rsplit(".", 1)
        name = name.strip("-")
        result = f"{name}.{ext}"
    else:
        result = result.strip("-")

    # Apply lowercase if configured
    if lowercase:
        result = result.lower()

    # Truncate if too long (preserve extension)
    if len(result) > max_length:
        # Check if there's an extension
        if "." in result:
            name, ext = result.rsplit(".", 1)
            # Keep room for extension
            available = max_length - len(ext) - 1
            result = f"{name[:available]}.{ext}" if available > 0 else result[:max_length]
        else:
            result = result[:max_length]

    return result


def sanitize_title_for_filename(title: str, max_length: int = 100) -> str:
    """Sanitize title for use in filename.

    Args:
        title: The title to sanitize.
        max_length: Maximum length for the filename part.

    Returns:
        Sanitized title suitable for filename.
    """
    # Remove special characters, keep alphanumeric and spaces
    cleaned = re.sub(r"[^\w\s-]", "", title)
    # Replace spaces with dashes
    cleaned = re.sub(r"\s+", "-", cleaned)
    # Collapse multiple dashes
    cleaned = re.sub(r"-+", "-", cleaned)
    # Strip leading/trailing dashes
    cleaned = cleaned.strip("-")
    # Truncate
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rsplit("-", 1)[0]
    return cleaned or "article"
