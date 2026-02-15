"""Unit tests for content hashing."""

from __future__ import annotations

from clipmd.core.hasher import hash_content


class TestHashContent:
    """Tests for hash_content function."""

    def test_sha256_default(self) -> None:
        """Test default SHA256 hashing."""
        result = hash_content("Hello, World!")
        # SHA256 of "Hello, World!" truncated to 16 chars
        assert len(result) == 16
        assert result.isalnum()

    def test_full_hash(self) -> None:
        """Test full hash (no truncation)."""
        result = hash_content("Hello, World!", length=None)
        # Full SHA256 is 64 hex characters
        assert len(result) == 64

    def test_custom_length(self) -> None:
        """Test custom length truncation."""
        result = hash_content("Hello, World!", length=8)
        assert len(result) == 8

    def test_consistent_hash(self) -> None:
        """Test that same content produces same hash."""
        content = "Test content"
        hash1 = hash_content(content)
        hash2 = hash_content(content)
        assert hash1 == hash2

    def test_different_content_different_hash(self) -> None:
        """Test that different content produces different hash."""
        hash1 = hash_content("Content A")
        hash2 = hash_content("Content B")
        assert hash1 != hash2
