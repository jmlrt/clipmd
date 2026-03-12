"""Unit tests for configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from clipmd.config import (
    CacheConfig,
    Config,
    DatesConfig,
    FetchConfig,
    FilenamesConfig,
    FoldersConfig,
    FrontmatterConfig,
    SpecialFoldersConfig,
    UrlCleaningConfig,
    get_config_file_path,
    load_config,
)
from clipmd.exceptions import ConfigError


class TestSpecialFoldersConfig:
    """Tests for SpecialFoldersConfig."""

    def test_defaults(self) -> None:
        """Test default exclude patterns."""
        config = SpecialFoldersConfig()
        assert "0-*" in config.exclude_patterns
        assert ".*" in config.exclude_patterns
        assert "_*" in config.exclude_patterns


class TestFrontmatterConfig:
    """Tests for FrontmatterConfig."""

    def test_defaults(self) -> None:
        """Test default field mappings."""
        config = FrontmatterConfig()
        assert "source" in config.source_url
        assert "url" in config.source_url
        assert "title" in config.title
        assert "published" in config.published_date


class TestDatesConfig:
    """Tests for DatesConfig."""

    def test_defaults(self) -> None:
        """Test default date settings."""
        config = DatesConfig()
        assert "%Y-%m-%d" in config.input_formats
        assert config.output_format == "%Y%m%d"
        assert config.extract_from_content is True

    def test_content_patterns(self) -> None:
        """Test default content patterns exist."""
        config = DatesConfig()
        assert len(config.content_patterns) > 0


class TestUrlCleaningConfig:
    """Tests for UrlCleaningConfig."""

    def test_defaults(self) -> None:
        """Test default URL cleaning settings."""
        config = UrlCleaningConfig()
        assert "utm_source" in config.remove_params
        assert "fbclid" in config.remove_params


class TestFilenamesConfig:
    """Tests for FilenamesConfig."""

    def test_defaults(self) -> None:
        """Test default filename settings."""
        config = FilenamesConfig()
        assert config.replacements[" "] == "-"
        assert config.max_length == 100
        assert config.collapse_dashes is True
        assert config.unicode_normalize == "NFC"


class TestFoldersConfig:
    """Tests for FoldersConfig."""

    def test_defaults(self) -> None:
        """Test default folder thresholds."""
        config = FoldersConfig()
        assert config.warn_below == 10
        assert config.warn_above == 45


class TestCacheConfig:
    """Tests for CacheConfig."""

    def test_defaults(self) -> None:
        """Test default cache settings."""
        config = CacheConfig()
        assert config.track_urls is True
        assert config.hash_length == 16


class TestFetchConfig:
    """Tests for FetchConfig."""

    def test_defaults(self) -> None:
        """Test default fetch settings."""
        config = FetchConfig()
        assert config.timeout == 30
        assert config.max_concurrent == 5
        assert config.user_agent == "clipmd/0.1"


class TestConfig:
    """Tests for main Config class."""

    def test_defaults(self) -> None:
        """Test full default configuration."""
        config = Config()
        assert config.version == 1
        assert config.vault is None  # Defaults to None
        assert config.cache is None  # Defaults to None

    def test_cache_config_defaults(self) -> None:
        """Test cache_config defaults."""
        config = Config()
        assert config.cache_config.hash_length == 16


class TestGetConfigFilePath:
    """Tests for get_config_file_path function."""

    def test_explicit_path(self, tmp_path: Path) -> None:
        """Test with explicit config path that exists."""
        config_file = tmp_path / "custom.yaml"
        config_file.write_text("version: 1\n")
        result = get_config_file_path(config_file)
        assert result == config_file

    def test_explicit_path_not_found(self, tmp_path: Path) -> None:
        """Test with non-existent explicit path."""
        config_file = tmp_path / "nonexistent.yaml"
        with pytest.raises(ConfigError, match="not found"):
            get_config_file_path(config_file)

    def test_default_xdg_path(self) -> None:
        """Test default returns XDG config path."""
        result = get_config_file_path(None)
        assert result.name == "config.yaml"
        assert "clipmd" in str(result)


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_returns_defaults_without_vault_cache(self, tmp_path: Path) -> None:
        """Test loading non-existent file raises error because vault/cache required."""
        config_file = tmp_path / "nonexistent.yaml"
        # When config file doesn't exist, load_config returns defaults
        # But defaults have vault/cache as None, which will fail validation
        # So we need to test that the file path raises error before that
        with pytest.raises(ConfigError, match="not found"):
            load_config(config_file)

    def test_load_with_vault_and_cache(self, tmp_path: Path) -> None:
        """Test loading config with vault and cache paths."""
        vault = tmp_path / "vault"
        vault.mkdir()

        config_file = tmp_path / "config.yaml"
        config_file.write_text(f"""\
version: 1
vault: {vault}
cache: {tmp_path}/cache.json
""")
        config = load_config(config_file)
        assert config.vault == vault
        assert config.cache == tmp_path / "cache.json"

    def test_load_missing_vault_raises_error(self, tmp_path: Path) -> None:
        """Test loading config without vault raises ConfigError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\n")
        with pytest.raises(ConfigError, match="vault"):
            load_config(config_file)

    def test_load_missing_cache_raises_error(self, tmp_path: Path) -> None:
        """Test loading config without cache raises ConfigError."""
        vault = tmp_path / "vault"
        vault.mkdir()

        config_file = tmp_path / "config.yaml"
        config_file.write_text(f"version: 1\nvault: {vault}\n")
        with pytest.raises(ConfigError, match="cache"):
            load_config(config_file)

    def test_load_expands_environment_variables(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that environment variables are expanded in vault and cache paths."""
        vault = tmp_path / "vault"
        vault.mkdir()
        monkeypatch.setenv("TEST_VAULT", str(vault))

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\nvault: $TEST_VAULT\ncache: $TEST_VAULT/cache.json\n")
        config = load_config(config_file)
        assert config.vault == vault
        assert config.cache == vault / "cache.json"

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        """Test error on invalid YAML."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: syntax:\n")
        with pytest.raises(ConfigError, match="Invalid YAML"):
            load_config(config_file)
