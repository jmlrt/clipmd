"""URL and filename sanitization for clipmd.

Note: We use custom sanitize_filename() rather than python-slugify because:
- NFD Unicode normalization required (not supported by library)
- Extension-aware max_length truncation needed
- Backward compatibility with existing vault filenames
"""

from __future__ import annotations

import hashlib
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


def sanitize_title_for_filename(title: str) -> str:
    """Sanitize title for use in filename.

    Removes special characters and normalizes spaces. Enforces a byte-based limit
    (242 bytes) to leave room for date prefix (9 bytes) and extension (3 bytes)
    within the filesystem limit (255 bytes). When truncation is needed, appends
    a short hash to avoid collisions.

    Args:
        title: The title to sanitize.

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

    result = cleaned or "article"

    # Enforce filesystem-safe byte limit (255 total, accounting for all components)
    # Reserve: 9 bytes for date prefix (YYYYMMDD-) + 3 bytes for .md extension
    #          + 5 bytes for counter suffix (-9999) in get_unique_filepath()
    max_bytes = 238  # 255 - 9 - 3 - 5 = 238
    result_bytes = result.encode("utf-8")

    if len(result_bytes) > max_bytes:
        # Truncate and append hash to prevent collisions
        hash_suffix = hashlib.md5(result.encode("utf-8")).hexdigest()[:8]
        # Leave room for hash suffix (9 bytes: "-" + 8 char hash)
        available = max_bytes - 9
        result = result_bytes[:available].decode("utf-8", errors="ignore").rstrip("-")
        result = f"{result}-{hash_suffix}"

    return result
