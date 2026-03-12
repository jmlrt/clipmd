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

    def test_no_match(self) -> None:
        """Test when domain doesn't match any rule."""
        rules = {"github.com": "Dev-Tools"}
        assert match_domain("example.com", rules) is None

    def test_case_insensitive(self) -> None:
        """Test that matching is case-insensitive."""
        rules = {"github.com": "Dev-Tools"}
        assert match_domain("GitHub.com", rules) == "Dev-Tools"
        assert match_domain("GITHUB.COM", rules) == "Dev-Tools"
        assert match_domain("GiThUb.CoM", rules) == "Dev-Tools"

    def test_domain_with_port(self) -> None:
        """Test matching domains with ports."""
        rules = {"example.com": "Example"}
        assert match_domain("example.com:443", rules) == "Example"
        assert match_domain("example.com:8000", rules) == "Example"
        assert match_domain("EXAMPLE.COM:443", rules) == "Example"

    def test_ipv6_with_port(self) -> None:
        """Test matching IPv6 addresses with ports."""
        rules = {"[::1]": "Localhost"}
        assert match_domain("[::1]:8000", rules) == "Localhost"
        assert match_domain("[::1]:443", rules) == "Localhost"

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

    def test_rule_with_port(self) -> None:
        """Test when rule itself has a port (unusual but handled)."""
        rules = {"example.com:443": "Secure"}
        assert match_domain("example.com:443", rules) == "Secure"

    def test_news_ycombinator(self) -> None:
        """Test news.ycombinator.com domain."""
        rules = {"news.ycombinator.com": "Tech"}
        assert match_domain("news.ycombinator.com", rules) == "Tech"
        assert match_domain("NEWS.YCOMBINATOR.COM", rules) == "Tech"
