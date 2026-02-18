"""URL collection and parsing utilities for clipmd."""

from __future__ import annotations

import re
from pathlib import Path


def extract_url_from_line(line: str) -> str | None:
    """Extract URL from a line that may contain markdown link syntax or inline comments.

    Handles:
    - Plain URLs: https://example.com
    - Markdown links: [text](https://example.com)
    - Angle bracket URLs: <https://example.com>
    - Inline comments: https://example.com # comment
    - Combination: [text](https://example.com) # comment

    Args:
        line: Line of text.

    Returns:
        Extracted URL or None if no valid URL found.
    """
    line = line.strip()

    # Skip empty lines and full-line comments
    if not line or line.startswith("#"):
        return None

    # Try to extract URL from markdown link syntax: [text](url)
    md_link_pattern = r"\[([^\]]*)\]\(([^)]+)\)"
    md_match = re.search(md_link_pattern, line)
    if md_match:
        url = md_match.group(2).strip()
        # Validate it looks like a URL
        if url.startswith(("http://", "https://")):
            return url

    # Handle angle bracket URLs (including tracking URLs with embedded <>)
    if "<http" in line:
        # Strip ALL angle brackets — handles tracking URLs like:
        # <https://tracker.com/L0/https>:%2F%2F<www.example.com>%2Fpath
        stripped = line.replace("<", "").replace(">", "").strip()
        if stripped.startswith(("http://", "https://")) and " " not in stripped:
            return stripped
        # Fallback: simple <url> pattern (e.g., "<https://example.com> some text")
        angle_match = re.search(r"<(https?://[^>]+)>", line)
        if angle_match:
            return angle_match.group(1).strip()

    # Strip inline comments (text after # with space before)
    if " #" in line:
        line = line.split(" #")[0].strip()

    # Check if remaining text is a URL
    if line.startswith(("http://", "https://")):
        return line

    return None


def read_urls_from_file(filepath: Path) -> list[str]:
    """Read URLs from a file.

    Supports multiple formats:
    - Plain URLs (one per line)
    - Markdown links: [text](url)
    - Angle bracket URLs: <url>
    - Inline comments: url # comment

    Args:
        filepath: Path to the file.

    Returns:
        List of URLs.
    """
    urls = []
    content = filepath.read_text(encoding="utf-8")
    for line in content.splitlines():
        url = extract_url_from_line(line)
        if url:
            urls.append(url)
    return urls


def collect_urls(
    cli_urls: tuple[str, ...],
    url_file: Path | None,
) -> list[str]:
    """Collect URLs from CLI arguments and optional file.

    Args:
        cli_urls: URLs provided as CLI arguments.
        url_file: Optional path to file containing URLs.

    Returns:
        Combined list of all URLs.
    """
    all_urls: list[str] = list(cli_urls)
    if url_file:
        all_urls.extend(read_urls_from_file(url_file))
    return all_urls
