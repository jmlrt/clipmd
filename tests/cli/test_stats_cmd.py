"""CLI tests for stats command."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from click.testing import CliRunner

from clipmd.cli import main

if TYPE_CHECKING:
    import pytest


class TestStatsCommand:
    """Tests for the stats command."""

    def test_help(self) -> None:
        """Test --help option."""
        runner = CliRunner()
        result = runner.invoke(main, ["stats", "--help"])
        assert result.exit_code == 0
        assert "stats" in result.output.lower()

    def test_empty_directory(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test stats on empty directory."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        runner = CliRunner()
        result = runner.invoke(main, ["stats"])
        assert result.exit_code == 0
        assert "0 articles" in result.output

    def test_basic_stats(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test basic statistics output."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        # Create articles in root
        for i in range(3):
            (tmp_path / f"article{i}.md").write_text(f"---\ntitle: Article {i}\n---\nContent.")

        # Create folder with articles
        folder = tmp_path / "Tech"
        folder.mkdir()
        for i in range(5):
            (folder / f"tech{i}.md").write_text(f"---\ntitle: Tech {i}\n---\nContent.")

        runner = CliRunner()
        result = runner.invoke(main, ["stats"])
        assert result.exit_code == 0
        assert "8 articles" in result.output
        assert "Tech" in result.output

    def test_json_format(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test JSON output format."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        folder = tmp_path / "Tech"
        folder.mkdir()
        (folder / "article.md").write_text("---\ntitle: Test\n---\nContent.")

        runner = CliRunner()
        result = runner.invoke(main, ["stats", "--format", "json"])
        assert result.exit_code == 0
        assert '"total_articles"' in result.output
        assert '"total_folders"' in result.output

    def test_yaml_format(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test YAML output format."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        folder = tmp_path / "Tech"
        folder.mkdir()
        (folder / "article.md").write_text("---\ntitle: Test\n---\nContent.")

        runner = CliRunner()
        result = runner.invoke(main, ["stats", "--format", "yaml"])
        assert result.exit_code == 0
        assert "total_articles:" in result.output

    def test_warnings_only(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test --warnings-only option."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "version: 1\npaths:\n  root: .\nfolders:\n  warn_below: 5\n  warn_above: 100\n"
        )

        # Create folder below threshold
        folder = tmp_path / "SmallFolder"
        folder.mkdir()
        for i in range(2):
            (folder / f"article{i}.md").write_text(f"---\ntitle: Article {i}\n---\nContent.")

        # Create folder within threshold
        folder2 = tmp_path / "NormalFolder"
        folder2.mkdir()
        for i in range(10):
            (folder2 / f"article{i}.md").write_text(f"---\ntitle: Article {i}\n---\nContent.")

        runner = CliRunner()
        result = runner.invoke(main, ["stats", "--warnings-only"])
        assert result.exit_code == 0
        assert "SmallFolder" in result.output
        assert "NormalFolder" not in result.output

    def test_exclude_special_folders(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that special folders are excluded by default."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        # Create normal folder
        folder = tmp_path / "Tech"
        folder.mkdir()
        (folder / "article.md").write_text("---\ntitle: Test\n---\nContent.")

        # Create special folder
        special = tmp_path / "0-Inbox"
        special.mkdir()
        (special / "article.md").write_text("---\ntitle: Test\n---\nContent.")

        # Create hidden folder
        hidden = tmp_path / ".hidden"
        hidden.mkdir()
        (hidden / "article.md").write_text("---\ntitle: Test\n---\nContent.")

        runner = CliRunner()
        result = runner.invoke(main, ["stats"])
        assert result.exit_code == 0
        assert "Tech" in result.output
        assert "0-Inbox" not in result.output
        assert ".hidden" not in result.output

    def test_include_special_folders(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test --include-special option."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        # Create special folder
        special = tmp_path / "0-Inbox"
        special.mkdir()
        (special / "article.md").write_text("---\ntitle: Test\n---\nContent.")

        runner = CliRunner()
        result = runner.invoke(main, ["stats", "--include-special"])
        assert result.exit_code == 0
        assert "0-Inbox" in result.output
