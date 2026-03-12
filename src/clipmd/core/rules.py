"""Domain rule matching for article categorization."""

from __future__ import annotations

from urllib.parse import urlparse


def _normalize_domain(domain: str) -> str:
    """Normalize a domain to a canonical form for consistent matching.

    Handles:
    - Lowercase
    - Strips port (for regular domains and bracketed IPv6 addresses)
    - Trims trailing dots
    - Removes IPv6 brackets (e.g. [::1] -> ::1)

    Args:
        domain: Domain string (e.g. "GitHub.com:443" or "[::1]:8000" or "[::1]" or "::1").

    Returns:
        Normalized domain (e.g. "github.com" or "::1").
    """
    if not domain:
        return ""

    # For IPv6 addresses with brackets (standard RFC format),
    # use urlparse to safely strip ports
    if domain.startswith("["):
        parsed = urlparse(f"//{domain}")
        host = parsed.hostname or ""
        return host.lower().rstrip(".")

    # For bare IPv6 addresses (contain multiple colons), urlparse fails
    # because it can't distinguish IPv6 colons from port delimiters.
    # Check for this case and return as-is (just lowercase)
    if ":" in domain and domain.count(":") >= 2:
        # This looks like an IPv6 address
        return domain.lower().rstrip(".")

    # For regular domains (no brackets, at most one colon for port), use urlparse
    # This handles:
    # - Regular domains: "github.com" -> "github.com"
    # - Domains with port: "github.com:443" -> "github.com"
    parsed = urlparse(f"//{domain}")
    host = parsed.hostname or ""
    if host:
        return host.lower().rstrip(".")

    # Fallback for cases where urlparse can't parse
    return domain.lower().rstrip(".")


def match_domain(domain: str, rules: dict[str, str] | None) -> str | None:
    """Match a domain against rules using exact matching (case-insensitive).

    Args:
        domain: Domain to match (e.g. "github.com" or "github.com:443" or "[::1]:8000").
        rules: Dict mapping domain -> folder. None if no rules configured.

    Returns:
        Matched folder name, or None if no match.
    """
    if not rules or not domain:
        return None

    # Normalize input domain
    normalized_input = _normalize_domain(domain)
    if not normalized_input:
        return None

    # Check against rules (with normalized rule domains)
    for rule_domain, folder in rules.items():
        normalized_rule = _normalize_domain(rule_domain)
        if normalized_input == normalized_rule:
            return folder

    return None
