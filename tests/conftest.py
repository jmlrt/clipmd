"""Shared fixtures for clipmd tests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def isolate_xdg_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate XDG_CONFIG_HOME for all tests to avoid interference from real config."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".xdg-config"))


@pytest.fixture
def fixtures_path() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_vault_path(fixtures_path: Path) -> Path:
    """Return path to sample vault test fixtures."""
    return fixtures_path / "sample-vault"


@pytest.fixture
def temp_dir(tmp_path: Path) -> Iterator[Path]:
    """Return a temporary directory for test files."""
    yield tmp_path


@pytest.fixture
def sample_config_yaml() -> str:
    """Return a sample config.yaml content."""
    return """version: 1

paths:
  root: "."
  cache: ".clipmd/cache.json"

special_folders:
  exclude_patterns:
    - "0-*"
    - ".*"
    - "_*"

frontmatter:
  source_url:
    - source
    - url
  title:
    - title
  published_date:
    - published
  clipped_date:
    - clipped

dates:
  input_formats:
    - "%Y-%m-%d"
  output_format: "%Y%m%d"
  prefix_priority:
    - published
    - clipped
"""


@pytest.fixture
def minimal_config_yaml() -> str:
    """Return a minimal config.yaml content."""
    return """version: 1
paths:
  root: "."
"""
