"""Domain rule matching for article categorization."""

from __future__ import annotations


def match_domain(domain: str, rules: dict[str, str] | None) -> str | None:
    """Match a domain against rules using exact matching (case-insensitive).

    Args:
        domain: Domain to match (e.g. "github.com" or "github.com:443").
        rules: Dict mapping domain -> folder. None if no rules configured.

    Returns:
        Matched folder name, or None if no match.
    """
    if not rules or not domain:
        return None

    # Normalize input: lowercase and strip port
    normalized = domain.lower().split(":")[0]

    # Check against rules (also normalized)
    for rule_domain, folder in rules.items():
        if normalized == rule_domain.lower().split(":")[0]:
            return folder

    return None
