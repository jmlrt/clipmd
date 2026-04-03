"""Unit tests for fetcher core logic."""

from __future__ import annotations

from unittest.mock import patch

from clipmd.core.fetcher import _extract_tracking_destination, extract_content_trafilatura


class TestExtractTrackingDestination:
    """Tests for _extract_tracking_destination function."""

    def test_extract_literal_l0_pattern(self) -> None:
        """Test extracting destination from /L0/https format."""
        url = "https://tracker.example.com/L0/https://actual-destination.com/article"
        result = _extract_tracking_destination(url)
        assert result == "https://actual-destination.com/article"

    def test_extract_literal_cl0_pattern(self) -> None:
        """Test extracting destination from /CL0/https format."""
        url = "https://tracker.example.com/CL0/https://destination.org/page"
        result = _extract_tracking_destination(url)
        assert result == "https://destination.org/page"

    def test_extract_literal_l_with_higher_digits(self) -> None:
        """Test extracting destination from /L123/https format."""
        url = "https://tracker.example.com/L123/https://test.com/path"
        result = _extract_tracking_destination(url)
        assert result == "https://test.com/path"

    def test_extract_percent_encoded_url(self) -> None:
        """Test extracting destination from percent-encoded /L0/https%3A%2F%2F format."""
        url = "https://tracker.example.com/L0/https%3A%2F%2Factual-destination.com%2Farticle"
        result = _extract_tracking_destination(url)
        assert result == "https://actual-destination.com/article"

    def test_extract_percent_encoded_with_cl_pattern(self) -> None:
        """Test extracting destination from percent-encoded /CL0/https%3A%2F%2F format."""
        url = "https://tracker.example.com/CL0/https%3A%2F%2Fdest.org%2Fpage%3Fq%3D1"
        result = _extract_tracking_destination(url)
        assert result == "https://dest.org/page?q=1"

    def test_extract_lowercase_percent_encoded_url(self) -> None:
        """Test extracting destination from lowercase percent-encoded format."""
        url = "https://tracker.example.com/L0/https%3a%2f%2fdest.org%2farticle"
        result = _extract_tracking_destination(url)
        assert result == "https://dest.org/article"

    def test_non_tracking_url_returns_none(self) -> None:
        """Test that non-tracking URLs return None."""
        url = "https://example.com/regular/article"
        result = _extract_tracking_destination(url)
        assert result is None

    def test_malformed_encoded_url(self) -> None:
        """Test that malformed encoding extracts partial result gracefully."""
        # Invalid percent encoding should still extract something (unquote is lenient)
        url = "https://tracker.example.com/L0/https%3A%2F%2F%ZZ%invalid"
        result = _extract_tracking_destination(url)
        # unquote() is lenient and will partially decode invalid sequences
        # The important thing is that the function doesn't crash
        assert result is not None
        assert result.startswith("https://")  # Should at least have the protocol


class TestExtractContentTrafilatura:
    """Tests for extract_content_trafilatura function."""

    def test_overflow_error_fallback(self) -> None:
        """Test that OverflowError (Python 3.14+ lxml issue) returns None for fallback."""
        html = "<html><body>Test content</body></html>"
        url = "https://example.com"

        with patch("clipmd.core.fetcher.trafilatura.extract") as mock_extract:
            mock_extract.side_effect = OverflowError("Python int too large to convert to C int")
            content, metadata = extract_content_trafilatura(html, url)

            # Should return None to signal failure (triggers fallback in fetch_url)
            assert content is None
            assert metadata == {}
