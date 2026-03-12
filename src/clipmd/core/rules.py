"""Domain rule matching for article categorization."""

from __future__ import annotations

from urllib.parse import urlsplit


def _normalize_domain(domain: str) -> str:
    """Normalize domain to lowercase without port or userinfo.

    Handles:
    - IPv6 addresses (e.g. "[::1]:8000" -> "::1")
    - Domains with ports (e.g. "example.com:443" -> "example.com")
    - Case sensitivity (all lowercased)

    Args:
        domain: Domain/netloc string to normalize.

    Returns:
        Normalized hostname (lowercase, no port).
    """
    if not domain:
        return ""

    # Use urlsplit to safely parse host/port for IPv6 compatibility
    # Prepend '//' so urlsplit treats it as a netloc
    parsed = urlsplit(f"//{domain}")
    hostname = parsed.hostname or ""
    return hostname.lower()


def match_domain(domain: str, rules: dict[str, str] | None) -> str | None:
    """Match a domain against rules using exact matching.

    Args:
        domain: Domain/netloc to match (e.g. "github.com" or "[::1]:8000").
        rules: Dict mapping domain -> folder. None if no rules configured.

    Returns:
        Matched folder name, or None if no match.
    """
    if not rules:
        return None

    # Normalize input domain for comparison
    normalized_input = _normalize_domain(domain)
    if not normalized_input:
        return None

    # Check for exact match in rules
    for rule_domain, folder in rules.items():
        # Normalize rule domain the same way
        normalized_rule = _normalize_domain(rule_domain)
        if normalized_input == normalized_rule:
            return folder

    return None
