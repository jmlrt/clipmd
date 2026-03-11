"""CLI tests for init command."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from click.testing import CliRunner

from clipmd.cli import main

if TYPE_CHECKING:
    import pytest


class TestInitCommand:
    """Tests for the init command."""

    def test_help(self) -> None:
        """Test --help option."""
        runner = CliRunner()
        result = runner.invoke(main, ["init", "--help"])
        assert result.exit_code == 0
        assert "init" in result.output.lower()

    def test_creates_minimal_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test creating minimal config in XDG location."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        # Use --force because fixture pre-creates a config
        result = runner.invoke(main, ["init", "--minimal", "--force"])
        assert result.exit_code == 0, f"Output: {result.output}"

        # Config should be created at ~/.config/clipmd/config.yaml
        xdg_config_home = Path(os.environ["XDG_CONFIG_HOME"])
        config_file = xdg_config_home / "clipmd" / "config.yaml"
        assert config_file.exists()

        content = config_file.read_text()
        assert "version: 1" in content
        assert "vault:" in content
        assert "cache:" in content

    def test_creates_full_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test creating full config."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(main, ["init", "--force"])
        assert result.exit_code == 0, f"Output: {result.output}"

        xdg_config_home = Path(os.environ["XDG_CONFIG_HOME"])
        config_file = xdg_config_home / "clipmd" / "config.yaml"
        assert config_file.exists()

        content = config_file.read_text()
        assert "version: 1" in content
        assert "vault:" in content
        assert "cache:" in content

    def test_creates_clipmd_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that .clipmd directory is created in vault."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(main, ["init", "--minimal", "--force"])
        assert result.exit_code == 0, f"Output: {result.output}"

        # .clipmd directory should be created in the vault (current directory)
        clipmd_dir = tmp_path / ".clipmd"
        assert clipmd_dir.exists()
        assert clipmd_dir.is_dir()

    def test_refuses_overwrite_without_force(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that existing config is not overwritten without --force."""
        monkeypatch.chdir(tmp_path)

        # Create a config file in XDG location
        xdg_config_home = Path(os.environ["XDG_CONFIG_HOME"])
        config_dir = xdg_config_home / "clipmd"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text("version: 1\nvault: .\n# old config\n")

        runner = CliRunner()
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 1
        assert "already exists" in result.output

        # Verify content was not changed
        content = config_file.read_text()
        assert "# old config" in content

    def test_force_overwrites_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that --force overwrites existing config."""
        monkeypatch.chdir(tmp_path)

        # Create a config file in XDG location
        xdg_config_home = Path(os.environ["XDG_CONFIG_HOME"])
        config_dir = xdg_config_home / "clipmd"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.yaml"
        config_file.write_text("version: 1\nvault: .\n# old config\n")

        runner = CliRunner()
        result = runner.invoke(main, ["init", "--minimal", "--force"])
        assert result.exit_code == 0, f"Output: {result.output}"

        # Verify content was changed
        content = config_file.read_text()
        assert "# old config" not in content
        assert "version: 1" in content
        assert "vault:" in content

    def test_counts_markdown_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that markdown file count is shown."""
        monkeypatch.chdir(tmp_path)

        # Create some markdown files
        for i in range(5):
            (tmp_path / f"article{i}.md").write_text("# Test")

        runner = CliRunner()
        result = runner.invoke(main, ["init", "--minimal", "--force"])
        assert result.exit_code == 0, f"Output: {result.output}"
        assert "5 markdown files" in result.output

    def test_shows_next_steps(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that next steps are shown."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(main, ["init", "--minimal", "--force"])
        assert result.exit_code == 0, f"Output: {result.output}"
        assert "Next steps" in result.output
        assert "preprocess" in result.output
        assert "extract" in result.output
