"""Filepath utilities for clipmd."""

from __future__ import annotations

import time
from pathlib import Path


def get_unique_filepath(output_dir: Path, filename: str) -> Path:
    """Get a unique filepath, adding suffix if file exists.

    If 'article.md' exists, tries 'article-1.md', 'article-2.md', etc.

    Args:
        output_dir: Directory to save to.
        filename: Desired filename.

    Returns:
        Unique filepath that doesn't exist.
    """
    filepath = output_dir / filename
    if not filepath.exists():
        return filepath

    # Split filename into stem and extension
    stem = filepath.stem
    suffix = filepath.suffix

    # Try adding counter suffix
    counter = 1
    while True:
        new_filename = f"{stem}-{counter}{suffix}"
        new_filepath = output_dir / new_filename
        if not new_filepath.exists():
            return new_filepath
        counter += 1
        # Safety limit to prevent infinite loops
        if counter > 1000:
            # Fallback: use timestamp
            ts = int(time.time())
            return output_dir / f"{stem}-{ts}{suffix}"
