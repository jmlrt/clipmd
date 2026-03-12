"""Tests for domain rule matching."""

from __future__ import annotations

from clipmd.core.rules import match_domain


class TestMatchDomain:
    """Test domain rule matching."""

    def test_exact_match(self) -> None:
        """Test exact domain matching."""
        rules = {"github.com": "Dev-Tools", "arxiv.org": "Science"}
        assert match_domain("github.com", rules) == "Dev-Tools"
        assert match_domain("arxiv.org", rules) == "Science"

    def test_case_insensitive(self) -> None:
        """Test that matching is case-insensitive."""
        rules = {"github.com": "Dev-Tools"}
        assert match_domain("GitHub.com", rules) == "Dev-Tools"
        assert match_domain("GITHUB.COM", rules) == "Dev-Tools"
        assert match_domain("GiThUb.CoM", rules) == "Dev-Tools"

    def test_strips_port_from_input(self) -> None:
        """Test that ports are stripped from input domain."""
        rules = {"github.com": "Dev-Tools"}
        assert match_domain("github.com:443", rules) == "Dev-Tools"
        assert match_domain("github.com:8000", rules) == "Dev-Tools"
        assert match_domain("GITHUB.COM:443", rules) == "Dev-Tools"

    def test_no_match(self) -> None:
        """Test when domain doesn't match any rule."""
        rules = {"github.com": "Dev-Tools"}
        assert match_domain("example.com", rules) is None

    def test_empty_domain(self) -> None:
        """Test with empty domain string."""
        rules = {"github.com": "Dev-Tools"}
        assert match_domain("", rules) is None

    def test_none_rules(self) -> None:
        """Test when rules are None."""
        assert match_domain("github.com", None) is None

    def test_empty_rules(self) -> None:
        """Test with empty rules dict."""
        assert match_domain("github.com", {}) is None

    def test_ipv6_with_port(self) -> None:
        """Test IPv6 addresses with ports (bracketed format per RFC 3986)."""
        # Rules can be stored with or without brackets
        rules = {"::1": "Localhost", "2001:db8::1": "Science"}
        # Bracketed IPv6 with port
        assert match_domain("[::1]:8000", rules) == "Localhost"
        assert match_domain("[2001:db8::1]:443", rules) == "Science"
        # Bracketed IPv6 without port
        assert match_domain("[::1]", rules) == "Localhost"
        assert match_domain("[2001:db8::1]", rules) == "Science"
        # Unbracketed IPv6 (non-standard but supported for compatibility)
        assert match_domain("::1", rules) == "Localhost"
        assert match_domain("2001:db8::1", rules) == "Science"

    def test_rule_domain_with_port(self) -> None:
        """Test that rule domains with ports are normalized."""
        rules = {"github.com:443": "Dev-Tools", "example.org:8000": "Examples"}
        # Input without port matches rule with port
        assert match_domain("github.com", rules) == "Dev-Tools"
        # Input with port matches rule with port
        assert match_domain("github.com:443", rules) == "Dev-Tools"
        assert match_domain("example.org:8000", rules) == "Examples"

    def test_rule_domain_ipv6_with_port(self) -> None:
        """Test that rule domains with IPv6 addresses and ports are normalized."""
        # Rules stored with bracketed IPv6 addresses
        rules = {"[::1]:8000": "Localhost", "[2001:db8::1]:443": "Science"}
        # Input with same port matches
        assert match_domain("[::1]:8000", rules) == "Localhost"
        # Input with brackets but different port also matches (ports are stripped)
        assert match_domain("[::1]:9000", rules) == "Localhost"
        # Input with just brackets matches (ports optional in rules)
        assert match_domain("[::1]", rules) == "Localhost"

    def test_mixed_case_and_port(self) -> None:
        """Test case-insensitive matching with ports."""
        rules = {"GitHub.COM:443": "Dev-Tools"}
        assert match_domain("github.com:443", rules) == "Dev-Tools"
        assert match_domain("GITHUB.COM:443", rules) == "Dev-Tools"
        assert match_domain("[::1]:443", rules) is None
