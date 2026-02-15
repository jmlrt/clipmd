"""CLI tests for duplicates command."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from click.testing import CliRunner

from clipmd.cli import main

if TYPE_CHECKING:
    import pytest


class TestDuplicatesCommand:
    """Tests for the duplicates command."""

    def test_help(self) -> None:
        """Test --help option."""
        runner = CliRunner()
        result = runner.invoke(main, ["duplicates", "--help"])
        assert result.exit_code == 0
        assert "duplicate" in result.output.lower()

    def test_no_duplicates(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test with no duplicates."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        # Create unique articles
        for i in range(3):
            (tmp_path / f"article{i}.md").write_text(
                f"---\ntitle: Article {i}\nurl: https://example{i}.com/\n---\nUnique content {i}."
            )

        runner = CliRunner()
        result = runner.invoke(main, ["duplicates"])
        assert result.exit_code == 0
        assert "No duplicates found" in result.output

    def test_duplicates_by_url(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test finding duplicates by URL."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        # Create articles with same URL
        same_url = "https://example.com/article"
        (tmp_path / "article1.md").write_text(
            f"---\ntitle: Article 1\nurl: {same_url}\n---\nContent 1."
        )
        (tmp_path / "article2.md").write_text(
            f"---\ntitle: Article 2\nurl: {same_url}\n---\nContent 2."
        )

        runner = CliRunner()
        result = runner.invoke(main, ["duplicates", "--by-url"])
        assert result.exit_code == 0
        assert "By URL" in result.output
        assert "article1.md" in result.output
        assert "article2.md" in result.output

    def test_duplicates_by_hash(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test finding duplicates by content hash."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        # Create articles with same content
        same_content = "Identical content here."
        (tmp_path / "article1.md").write_text(f"---\ntitle: Article 1\n---\n{same_content}")
        (tmp_path / "article2.md").write_text(f"---\ntitle: Article 2\n---\n{same_content}")

        runner = CliRunner()
        result = runner.invoke(main, ["duplicates", "--by-hash"])
        assert result.exit_code == 0
        assert "By Content Hash" in result.output
        assert "article1.md" in result.output
        assert "article2.md" in result.output

    def test_duplicates_by_filename(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test finding duplicates by similar filename."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        # Create folders
        folder1 = tmp_path / "Tech"
        folder1.mkdir()
        folder2 = tmp_path / "Archive"
        folder2.mkdir()

        # Create articles with same filename (after removing date prefix)
        (folder1 / "20240101-my-article.md").write_text("---\ntitle: My Article\n---\nContent 1.")
        (folder2 / "20240202-my-article.md").write_text("---\ntitle: My Article\n---\nContent 2.")

        runner = CliRunner()
        result = runner.invoke(main, ["duplicates", "--by-filename"])
        assert result.exit_code == 0
        assert "By Similar Filename" in result.output
        assert "my-article" in result.output

    def test_json_format(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test JSON output format."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        # Create duplicates
        same_url = "https://example.com/article"
        (tmp_path / "article1.md").write_text(
            f"---\ntitle: Article 1\nurl: {same_url}\n---\nContent 1."
        )
        (tmp_path / "article2.md").write_text(
            f"---\ntitle: Article 2\nurl: {same_url}\n---\nContent 2."
        )

        runner = CliRunner()
        result = runner.invoke(main, ["duplicates", "--format", "json"])
        assert result.exit_code == 0
        assert '"by_url"' in result.output
        assert '"by_hash"' in result.output
        assert '"by_filename"' in result.output

    def test_output_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test output to file."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        output_file = tmp_path / "duplicates.md"

        runner = CliRunner()
        result = runner.invoke(main, ["duplicates", "-o", str(output_file)])
        assert result.exit_code == 0
        assert output_file.exists()
        assert "Duplicates saved to" in result.output

    def test_multiple_methods(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test combining multiple detection methods."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        # Create articles
        (tmp_path / "article1.md").write_text(
            "---\ntitle: Article 1\nurl: https://example.com/\n---\nContent."
        )
        (tmp_path / "article2.md").write_text(
            "---\ntitle: Article 2\nurl: https://example.com/\n---\nContent."
        )

        runner = CliRunner()
        result = runner.invoke(main, ["duplicates", "--by-url", "--by-hash"])
        assert result.exit_code == 0
        # Should find by URL and by hash
        assert "By URL" in result.output
        assert "By Content Hash" in result.output

    def test_hidden_files_excluded(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that hidden files are excluded."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        # Create visible and hidden duplicates
        same_url = "https://example.com/article"
        (tmp_path / "article.md").write_text(f"---\ntitle: Article\nurl: {same_url}\n---\nContent.")
        (tmp_path / ".hidden.md").write_text(f"---\ntitle: Hidden\nurl: {same_url}\n---\nContent.")

        runner = CliRunner()
        result = runner.invoke(main, ["duplicates", "--by-url"])
        assert result.exit_code == 0
        # Should not find duplicates because hidden file is excluded
        assert "No duplicates found" in result.output
