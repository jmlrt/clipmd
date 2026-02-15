"""Tests for core.discovery module."""

from __future__ import annotations

from pathlib import Path

from clipmd.config import Config
from clipmd.core.discovery import (
    discover_markdown_files,
    is_in_excluded_folder,
    should_exclude_folder,
    should_ignore_file,
)


class TestShouldIgnoreFile:
    """Tests for should_ignore_file function."""

    def test_hidden_file(self, tmp_path: Path) -> None:
        """Test that hidden files are ignored."""
        config = Config()
        hidden_file = tmp_path / ".hidden.md"
        hidden_file.touch()

        assert should_ignore_file(hidden_file, config) is True

    def test_readme_file(self, tmp_path: Path) -> None:
        """Test that README.md is ignored by default."""
        config = Config()
        readme = tmp_path / "README.md"
        readme.touch()

        assert should_ignore_file(readme, config) is True

    def test_claude_file(self, tmp_path: Path) -> None:
        """Test that CLAUDE.md is ignored by default."""
        config = Config()
        claude = tmp_path / "CLAUDE.md"
        claude.touch()

        assert should_ignore_file(claude, config) is True

    def test_normal_file(self, tmp_path: Path) -> None:
        """Test that normal files are not ignored."""
        config = Config()
        normal = tmp_path / "article.md"
        normal.touch()

        assert should_ignore_file(normal, config) is False

    def test_custom_ignore_list(self, tmp_path: Path) -> None:
        """Test custom ignore list."""
        config = Config()
        config.special_folders.ignore_files = ["IGNORE.md", "SKIP.md"]

        ignore = tmp_path / "IGNORE.md"
        ignore.touch()
        skip = tmp_path / "SKIP.md"
        skip.touch()
        normal = tmp_path / "README.md"  # No longer in ignore list
        normal.touch()

        assert should_ignore_file(ignore, config) is True
        assert should_ignore_file(skip, config) is True
        assert should_ignore_file(normal, config) is False


class TestShouldExcludeFolder:
    """Tests for should_exclude_folder function."""

    def test_hidden_folder(self) -> None:
        """Test that hidden folders are excluded."""
        config = Config()
        assert should_exclude_folder(".git", config) is True
        assert should_exclude_folder(".clipmd", config) is True

    def test_underscore_folder(self) -> None:
        """Test that underscore folders are excluded."""
        config = Config()
        assert should_exclude_folder("_archive", config) is True
        assert should_exclude_folder("_temp", config) is True

    def test_zero_prefix_folder(self) -> None:
        """Test that 0- prefixed folders are excluded."""
        config = Config()
        assert should_exclude_folder("0-inbox", config) is True
        assert should_exclude_folder("0-unsorted", config) is True

    def test_normal_folder(self) -> None:
        """Test that normal folders are not excluded."""
        config = Config()
        assert should_exclude_folder("Technology", config) is False
        assert should_exclude_folder("articles", config) is False


class TestIsInExcludedFolder:
    """Tests for is_in_excluded_folder function."""

    def test_file_in_hidden_folder(self, tmp_path: Path) -> None:
        """Test file in hidden folder."""
        config = Config()
        hidden_dir = tmp_path / ".hidden"
        hidden_dir.mkdir()
        file_path = hidden_dir / "article.md"
        file_path.touch()

        assert is_in_excluded_folder(file_path, tmp_path, config) is True

    def test_file_in_normal_folder(self, tmp_path: Path) -> None:
        """Test file in normal folder."""
        config = Config()
        normal_dir = tmp_path / "Technology"
        normal_dir.mkdir()
        file_path = normal_dir / "article.md"
        file_path.touch()

        assert is_in_excluded_folder(file_path, tmp_path, config) is False

    def test_file_in_underscore_folder(self, tmp_path: Path) -> None:
        """Test file in underscore folder."""
        config = Config()
        archive_dir = tmp_path / "_archive"
        archive_dir.mkdir()
        file_path = archive_dir / "old-article.md"
        file_path.touch()

        assert is_in_excluded_folder(file_path, tmp_path, config) is True


class TestDiscoverMarkdownFiles:
    """Tests for discover_markdown_files function."""

    def test_discovers_normal_files(self, tmp_path: Path) -> None:
        """Test that normal markdown files are discovered."""
        config = Config()
        (tmp_path / "article1.md").write_text("content")
        (tmp_path / "article2.md").write_text("content")

        files = list(discover_markdown_files(tmp_path, config))
        assert len(files) == 2

    def test_ignores_readme_and_claude(self, tmp_path: Path) -> None:
        """Test that README.md and CLAUDE.md are ignored."""
        config = Config()
        (tmp_path / "article.md").write_text("content")
        (tmp_path / "README.md").write_text("readme content")
        (tmp_path / "CLAUDE.md").write_text("claude content")

        files = list(discover_markdown_files(tmp_path, config))
        assert len(files) == 1
        assert files[0].name == "article.md"

    def test_ignores_hidden_files(self, tmp_path: Path) -> None:
        """Test that hidden files are ignored."""
        config = Config()
        (tmp_path / "article.md").write_text("content")
        (tmp_path / ".hidden.md").write_text("hidden content")

        files = list(discover_markdown_files(tmp_path, config))
        assert len(files) == 1
        assert files[0].name == "article.md"

    def test_ignores_files_in_hidden_directories(self, tmp_path: Path) -> None:
        """Test that files in hidden directories are ignored."""
        config = Config()
        (tmp_path / "article.md").write_text("content")
        hidden_dir = tmp_path / ".git"
        hidden_dir.mkdir()
        (hidden_dir / "config.md").write_text("git config")

        files = list(discover_markdown_files(tmp_path, config))
        assert len(files) == 1
        assert files[0].name == "article.md"

    def test_recursive_discovery(self, tmp_path: Path) -> None:
        """Test recursive file discovery."""
        config = Config()
        (tmp_path / "root-article.md").write_text("content")
        subdir = tmp_path / "Technology"
        subdir.mkdir()
        (subdir / "tech-article.md").write_text("content")

        files = list(discover_markdown_files(tmp_path, config, recursive=True))
        assert len(files) == 2

    def test_non_recursive_discovery(self, tmp_path: Path) -> None:
        """Test non-recursive file discovery."""
        config = Config()
        (tmp_path / "root-article.md").write_text("content")
        subdir = tmp_path / "Technology"
        subdir.mkdir()
        (subdir / "tech-article.md").write_text("content")

        files = list(discover_markdown_files(tmp_path, config, recursive=False))
        assert len(files) == 1
        assert files[0].name == "root-article.md"

    def test_excludes_special_folders(self, tmp_path: Path) -> None:
        """Test that special folders are excluded."""
        config = Config()
        (tmp_path / "article.md").write_text("content")

        inbox = tmp_path / "0-inbox"
        inbox.mkdir()
        (inbox / "pending.md").write_text("content")

        archive = tmp_path / "_archive"
        archive.mkdir()
        (archive / "old.md").write_text("content")

        files = list(discover_markdown_files(tmp_path, config))
        assert len(files) == 1
        assert files[0].name == "article.md"

    def test_include_special_folders(self, tmp_path: Path) -> None:
        """Test including special folders."""
        config = Config()
        (tmp_path / "article.md").write_text("content")

        inbox = tmp_path / "0-inbox"
        inbox.mkdir()
        (inbox / "pending.md").write_text("content")

        files = list(discover_markdown_files(tmp_path, config, include_special_folders=True))
        assert len(files) == 2

    def test_readme_in_subdirectory_also_ignored(self, tmp_path: Path) -> None:
        """Test that README.md in subdirectories is also ignored."""
        config = Config()
        subdir = tmp_path / "Technology"
        subdir.mkdir()
        (subdir / "article.md").write_text("content")
        (subdir / "README.md").write_text("folder readme")

        files = list(discover_markdown_files(tmp_path, config))
        assert len(files) == 1
        assert files[0].name == "article.md"
