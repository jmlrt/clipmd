"""CLI tests for trash command."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from clipmd.cli import main


class TestTrashCommand:
    """Tests for the trash command."""

    def test_help(self) -> None:
        """Test --help option."""
        runner = CliRunner()
        result = runner.invoke(main, ["trash", "--help"])
        assert result.exit_code == 0
        assert "trash" in result.output.lower()

    def test_basic_trash(self, tmp_path: Path, monkeypatch) -> None:
        """Test basic file trash."""
        monkeypatch.chdir(tmp_path)

        # Create config
        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        # Create article
        article = tmp_path / "20240115-Article.md"
        article.write_text("""---
title: Test Article
---

Content here.
""")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["trash", "20240115-Article.md", "--no-cache-update"],
        )
        assert result.exit_code == 0
        assert "Trashed" in result.output
        assert "1 trashed" in result.output

        # File should be gone
        assert not article.exists()

    def test_dry_run(self, tmp_path: Path, monkeypatch) -> None:
        """Test dry run mode."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        article = tmp_path / "20240115-Article.md"
        article.write_text("""---
title: Test
---

Content.
""")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["trash", "20240115-Article.md", "--dry-run"],
        )
        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert "Would trash" in result.output

        # File should still exist
        assert article.exists()

    def test_multiple_files(self, tmp_path: Path, monkeypatch) -> None:
        """Test trashing multiple files."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        # Create articles
        for i in range(3):
            article = tmp_path / f"article{i}.md"
            article.write_text(f"---\ntitle: Article {i}\n---\nContent.\n")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["trash", "article0.md", "article1.md", "article2.md", "--no-cache-update"],
        )
        assert result.exit_code == 0
        assert "3 trashed" in result.output

        # All files should be gone
        for i in range(3):
            assert not (tmp_path / f"article{i}.md").exists()

    def test_file_not_found(self, tmp_path: Path, monkeypatch) -> None:
        """Test handling of missing files."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["trash", "nonexistent.md"],
        )
        assert result.exit_code == 0
        assert "File not found" in result.output


class TestTrashGlobPatterns:
    """Tests for trash command with glob patterns."""

    def test_glob_pattern(self, tmp_path: Path, monkeypatch) -> None:
        """Test glob pattern expansion."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        # Create articles
        for i in range(3):
            article = tmp_path / f"to-delete-{i}.md"
            article.write_text(f"---\ntitle: Delete {i}\n---\nContent.\n")

        # Also create one to keep
        keep = tmp_path / "keep-this.md"
        keep.write_text("---\ntitle: Keep\n---\nContent.\n")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["trash", "to-delete-*.md", "--no-cache-update"],
        )
        assert result.exit_code == 0
        assert "3 trashed" in result.output

        # Only glob-matched files should be gone
        for i in range(3):
            assert not (tmp_path / f"to-delete-{i}.md").exists()
        assert keep.exists()

    def test_no_matches(self, tmp_path: Path, monkeypatch) -> None:
        """Test when glob matches nothing."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["trash", "nonexistent-*.md"],
        )
        assert result.exit_code == 0
        assert "No files match" in result.output

    def test_directory_skipped(self, tmp_path: Path, monkeypatch) -> None:
        """Test that directories are skipped."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        # Create a directory
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Create a file
        article = tmp_path / "article.md"
        article.write_text("---\ntitle: Test\n---\nContent.\n")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["trash", "subdir", "article.md", "--no-cache-update"],
        )
        assert result.exit_code == 0
        # Only the file should be trashed
        assert "1 trashed" in result.output
        # Directory should still exist
        assert subdir.exists()

    def test_with_cache_update(self, tmp_path: Path, monkeypatch) -> None:
        """Test trash with cache update."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n  cache: .clipmd/cache.json\n")

        # Create cache directory
        cache_dir = tmp_path / ".clipmd"
        cache_dir.mkdir()

        article = tmp_path / "20240115-Article.md"
        article.write_text("""---
title: Test Article
source: https://example.com/page
---

Content here.
""")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["trash", "20240115-Article.md"],
        )
        assert result.exit_code == 0
        assert "1 trashed" in result.output
        assert "Cache updated" in result.output
