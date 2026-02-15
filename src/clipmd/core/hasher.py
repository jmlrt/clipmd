"""Content hashing for clipmd."""

from __future__ import annotations

import hashlib


def get_hasher() -> hashlib._Hash:
    """Get a SHA256 hasher.

    Returns:
        SHA256 hasher object.
    """
    return hashlib.sha256()


def hash_content(
    content: str,
    length: int | None = 16,
) -> str:
    """Hash text content using SHA256.

    Args:
        content: The text content to hash.
        length: Truncate hash to this many characters (None for full hash).

    Returns:
        Hexadecimal hash string.
    """
    hasher = get_hasher()
    hasher.update(content.encode("utf-8"))
    digest = hasher.hexdigest()

    if length is not None and length > 0:
        return digest[:length]
    return digest
