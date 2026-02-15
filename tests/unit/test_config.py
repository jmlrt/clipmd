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
    OutputConfig,
    PathsConfig,
    SpecialFoldersConfig,
    UrlCleaningConfig,
    find_config_file,
    load_config,
)
from clipmd.exceptions import ConfigError


class TestPathsConfig:
    """Tests for PathsConfig."""

    def test_defaults(self) -> None:
        """Test default values."""
        config = PathsConfig()
        assert config.root == Path(".")
        assert config.cache == Path(".clipmd/cache.json")

    def test_custom_values(self) -> None:
        """Test custom values."""
        config = PathsConfig(
            root=Path("/custom/path"),
            cache=Path("custom/cache.json"),
        )
        assert config.root == Path("/custom/path")
        assert config.cache == Path("custom/cache.json")


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
        assert config.readability is True


class TestOutputConfig:
    """Tests for OutputConfig."""

    def test_defaults(self) -> None:
        """Test default output settings."""
        config = OutputConfig()
        assert config.metadata_format == "markdown"
        assert config.max_content_chars == 150


class TestConfig:
    """Tests for main Config class."""

    def test_defaults(self) -> None:
        """Test full default configuration."""
        config = Config()
        assert config.version == 1
        assert config.paths.root == Path(".")

    def test_from_dict(self) -> None:
        """Test creating config from dictionary."""
        data = {
            "version": 1,
            "paths": {"root": "/custom/path"},
        }
        config = Config.model_validate(data)
        assert config.paths.root == Path("/custom/path")


class TestFindConfigFile:
    """Tests for find_config_file function."""

    def test_explicit_path(self, tmp_path: Path) -> None:
        """Test with explicit config path."""
        config_file = tmp_path / "custom.yaml"
        config_file.write_text("version: 1\n")
        result = find_config_file(config_file)
        assert result == config_file

    def test_explicit_path_not_found(self, tmp_path: Path) -> None:
        """Test with non-existent explicit path."""
        config_file = tmp_path / "nonexistent.yaml"
        with pytest.raises(ConfigError, match="not found"):
            find_config_file(config_file)

    def test_no_config_returns_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test returns None when no config found."""
        monkeypatch.chdir(tmp_path)
        # Use tmp_path as XDG_CONFIG_HOME to avoid finding real config
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
        result = find_config_file(None)
        assert result is None

    def test_finds_cwd_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test finds config.yaml in current directory."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\n")
        result = find_config_file(None)
        assert result is not None
        assert result.resolve() == config_file.resolve()

    def test_finds_clipmd_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test finds .clipmd/config.yaml."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
        clipmd_dir = tmp_path / ".clipmd"
        clipmd_dir.mkdir()
        config_file = clipmd_dir / "config.yaml"
        config_file.write_text("version: 1\n")
        result = find_config_file(None)
        assert result is not None
        assert result.resolve() == config_file.resolve()


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_defaults_when_no_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test loads defaults when no config file exists."""
        monkeypatch.chdir(tmp_path)
        config = load_config()
        assert config.version == 1

    def test_load_from_file(self, tmp_path: Path, minimal_config_yaml: str) -> None:
        """Test loading config from file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(minimal_config_yaml)
        config = load_config(config_file)
        assert config.version == 1
        assert config.paths.root == Path(".")

    def test_load_full_config(self, tmp_path: Path, sample_config_yaml: str) -> None:
        """Test loading full config from file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(sample_config_yaml)
        config = load_config(config_file)
        assert config.version == 1
        assert "source" in config.frontmatter.source_url

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        """Test error on invalid YAML."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: syntax:\n")
        with pytest.raises(ConfigError, match="Invalid YAML"):
            load_config(config_file)

    def test_empty_file(self, tmp_path: Path) -> None:
        """Test loading empty config file returns defaults."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")
        config = load_config(config_file)
        assert config.version == 1


class TestDefaultVault:
    """Tests for default vault functionality."""

    def test_save_and_load_default_vault(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test saving and loading default vault."""
        from clipmd.config import get_default_vault, save_default_vault

        # Use tmp_path as XDG_CONFIG_HOME
        xdg_config = tmp_path / ".config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config))

        # Create a vault directory
        vault_dir = tmp_path / "my-vault"
        vault_dir.mkdir()

        # Save the default vault
        save_default_vault(vault_dir)

        # Verify the XDG config was created
        xdg_config_file = xdg_config / "clipmd" / "config.yaml"
        assert xdg_config_file.exists()

        # Load and verify
        loaded_vault = get_default_vault()
        assert loaded_vault is not None
        assert loaded_vault.resolve() == vault_dir.resolve()

    def test_get_default_vault_returns_none_when_not_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test get_default_vault returns None when not configured."""
        from clipmd.config import get_default_vault

        # Use tmp_path as XDG_CONFIG_HOME (no config file)
        xdg_config = tmp_path / ".config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config))

        result = get_default_vault()
        assert result is None

    def test_get_default_vault_returns_none_for_nonexistent_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test get_default_vault returns None if vault path doesn't exist."""
        from clipmd.config import get_default_vault, save_default_vault

        # Use tmp_path as XDG_CONFIG_HOME
        xdg_config = tmp_path / ".config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config))

        # Save a path that doesn't exist
        nonexistent = tmp_path / "does-not-exist"
        save_default_vault(nonexistent)

        # Should return None because path doesn't exist
        result = get_default_vault()
        assert result is None

    def test_resolve_vault_root_explicit_override(self, tmp_path: Path) -> None:
        """Test resolve_vault_root with explicit override."""
        from clipmd.config import resolve_vault_root

        config = Config()
        vault_dir = tmp_path / "override-vault"
        vault_dir.mkdir()

        result = resolve_vault_root(config, vault_dir)
        assert result.resolve() == vault_dir.resolve()

    def test_resolve_vault_root_absolute_paths_root(self, tmp_path: Path) -> None:
        """Test resolve_vault_root uses absolute paths.root."""
        from clipmd.config import resolve_vault_root

        vault_dir = tmp_path / "absolute-vault"
        vault_dir.mkdir()

        config = Config()
        config.paths.root = vault_dir

        result = resolve_vault_root(config, None)
        assert result == vault_dir

    def test_resolve_vault_root_uses_default_vault(self, tmp_path: Path) -> None:
        """Test resolve_vault_root uses default_vault from config."""
        from clipmd.config import resolve_vault_root

        vault_dir = tmp_path / "default-vault"
        vault_dir.mkdir()

        config = Config()
        config.default_vault = vault_dir

        result = resolve_vault_root(config, None)
        assert result == vault_dir

    def test_resolve_vault_root_uses_xdg_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test resolve_vault_root uses XDG default vault."""
        from clipmd.config import resolve_vault_root, save_default_vault

        # Use tmp_path as XDG_CONFIG_HOME
        xdg_config = tmp_path / ".config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config))

        vault_dir = tmp_path / "xdg-vault"
        vault_dir.mkdir()
        save_default_vault(vault_dir)

        config = Config()
        result = resolve_vault_root(config, None)
        assert result.resolve() == vault_dir.resolve()

    def test_resolve_vault_root_falls_back_to_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test resolve_vault_root falls back to cwd with relative root."""
        from clipmd.config import resolve_vault_root

        # Use tmp_path as XDG_CONFIG_HOME (no default vault)
        xdg_config = tmp_path / ".config"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_config))
        monkeypatch.chdir(tmp_path)

        config = Config()
        config.paths.root = Path(".")

        result = resolve_vault_root(config, None)
        assert result.resolve() == tmp_path.resolve()
