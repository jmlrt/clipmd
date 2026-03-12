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

    def test_strips_www_prefix(self) -> None:
        """Test that www. prefix is stripped for matching."""
        rules = {"github.com": "Dev-Tools"}
        assert match_domain("www.github.com", rules) == "Dev-Tools"
        assert match_domain("WWW.GITHUB.COM", rules) == "Dev-Tools"

    def test_strips_default_ports(self) -> None:
        """Test that default ports (80, 443) are stripped."""
        rules = {"github.com": "Dev-Tools"}
        assert match_domain("github.com:443", rules) == "Dev-Tools"
        assert match_domain("github.com:80", rules) == "Dev-Tools"
        assert match_domain("GITHUB.COM:443", rules) == "Dev-Tools"

    def test_no_match_different_ports(self) -> None:
        """Test that non-default ports are not stripped."""
        rules = {"github.com": "Dev-Tools"}
        # Non-default port (8000) is kept, so doesn't match
        assert match_domain("github.com:8000", rules) is None

    def test_rule_domain_with_www_and_port(self) -> None:
        """Test that rule domains with www. and ports are normalized."""
        rules = {"www.github.com:443": "Dev-Tools", "example.org:80": "Examples"}
        # Input without www/port matches rule with www/port
        assert match_domain("github.com", rules) == "Dev-Tools"
        assert match_domain("example.org", rules) == "Examples"
        # Input with www/port also matches
        assert match_domain("www.github.com", rules) == "Dev-Tools"
        assert match_domain("www.github.com:443", rules) == "Dev-Tools"

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
