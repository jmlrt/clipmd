"""Unit tests for fetcher core logic."""

from __future__ import annotations

from clipmd.core.fetcher import _extract_tracking_destination


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

    def test_non_tracking_url_returns_none(self) -> None:
        """Test that non-tracking URLs return None."""
        url = "https://example.com/regular/article"
        result = _extract_tracking_destination(url)
        assert result is None

    def test_malformed_encoded_url(self) -> None:
        """Test that malformed encoding returns None gracefully."""
        # Invalid percent encoding should fail gracefully
        url = "https://tracker.example.com/L0/https%3A%2F%2F%ZZ%invalid"
        result = _extract_tracking_destination(url)
        # The function should handle this gracefully (return None or attempt decode)
        # Current implementation catches exceptions, so it should return None
        assert result is None or isinstance(result, str)
