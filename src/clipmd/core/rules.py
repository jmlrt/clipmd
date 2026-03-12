"""Domain rule matching for article categorization."""

from __future__ import annotations


def match_domain(domain: str, rules: dict[str, str] | None) -> str | None:
    """Match a domain against rules using exact matching (case-insensitive).

    Matches standard domain names like 'github.com' or 'arxiv.org'.
    Strips common ports (80, 443) and leading 'www.' prefix for flexibility.

    Args:
        domain: Domain to match (e.g. "github.com" or "www.github.com").
        rules: Dict mapping domain -> folder. None if no rules configured.

    Returns:
        Matched folder name, or None if no match.
    """
    if not rules or not domain:
        return None

    # Normalize input: lowercase, strip www., strip default ports
    normalized = domain.lower().strip()
    if normalized.startswith("www."):
        normalized = normalized[4:]
    # Strip common default ports if present
    if normalized.endswith(":80") or normalized.endswith(":443"):
        normalized = normalized.rsplit(":", 1)[0]

    # Check against rules (also normalized the same way)
    for rule_domain, folder in rules.items():
        rule_norm = rule_domain.lower().strip()
        if rule_norm.startswith("www."):
            rule_norm = rule_norm[4:]
        if rule_norm.endswith(":80") or rule_norm.endswith(":443"):
            rule_norm = rule_norm.rsplit(":", 1)[0]

        if normalized == rule_norm:
            return folder

    return None
