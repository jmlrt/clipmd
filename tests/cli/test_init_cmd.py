"""CLI tests for init command."""

from __future__ import annotations

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
        """Test creating minimal config."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(main, ["init", "--minimal"])
        assert result.exit_code == 0

        config_file = tmp_path / "config.yaml"
        assert config_file.exists()

        content = config_file.read_text()
        assert "version: 1" in content
        assert "paths:" in content
        assert "root:" in content

    def test_creates_full_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test creating full config."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        config_file = tmp_path / "config.yaml"
        assert config_file.exists()

        content = config_file.read_text()
        assert "version: 1" in content
        assert "frontmatter:" in content
        assert "dates:" in content
        assert "url_cleaning:" in content

    def test_creates_clipmd_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that .clipmd directory is created."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(main, ["init", "--minimal"])
        assert result.exit_code == 0

        clipmd_dir = tmp_path / ".clipmd"
        assert clipmd_dir.exists()
        assert clipmd_dir.is_dir()

    def test_refuses_overwrite_without_force(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that existing config is not overwritten without --force."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        # Use valid YAML so cli doesn't fail before init runs
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        runner = CliRunner()
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 1
        assert "already exists" in result.output

        # Verify content was not changed (still has the original version line)
        content = config_file.read_text()
        assert "version: 1" in content
        # Should not have the full config header comment
        assert "clipmd configuration" not in content or "minimal" in content

    def test_force_overwrites_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that --force overwrites existing config."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        # Use valid YAML so cli doesn't fail before init runs
        config_file.write_text("version: 1\npaths:\n  root: .\n# old config\n")

        runner = CliRunner()
        result = runner.invoke(main, ["init", "--minimal", "--force"])
        assert result.exit_code == 0

        # Verify content was changed (new config from init)
        content = config_file.read_text()
        assert "# old config" not in content
        assert "version: 1" in content
        assert "clipmd minimal" in content

    def test_custom_config_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test using custom config path."""
        monkeypatch.chdir(tmp_path)

        # Create parent directory for custom config
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        custom_path = custom_dir / "my-config.yaml"

        runner = CliRunner()
        result = runner.invoke(main, ["init", "--minimal", "--config", str(custom_path)])
        assert result.exit_code == 0
        assert custom_path.exists()

    def test_counts_markdown_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that markdown file count is shown."""
        monkeypatch.chdir(tmp_path)

        # Create some markdown files
        for i in range(5):
            (tmp_path / f"article{i}.md").write_text("# Test")

        runner = CliRunner()
        result = runner.invoke(main, ["init", "--minimal"])
        assert result.exit_code == 0
        assert "5 markdown files" in result.output

    def test_shows_next_steps(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that next steps are shown."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(main, ["init", "--minimal"])
        assert result.exit_code == 0
        assert "Next steps" in result.output
        assert "preprocess" in result.output
        assert "extract" in result.output
