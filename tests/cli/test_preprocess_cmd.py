"""CLI tests for preprocess command."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from clipmd.cli import main


class TestPreprocessCommand:
    """Tests for the preprocess command."""

    def test_help(self) -> None:
        """Test --help option."""
        runner = CliRunner()
        result = runner.invoke(main, ["preprocess", "--help"])
        assert result.exit_code == 0
        assert "preprocess" in result.output.lower()

    def test_dry_run(self, tmp_path: Path) -> None:
        """Test dry run mode."""
        # Create a test markdown file
        article = tmp_path / "article.md"
        article.write_text("""---
title: Test Article
source: https://example.com/page?utm_source=twitter
---

Content here.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["preprocess", "--dry-run", str(tmp_path)])
        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert "Scanned: 1 files" in result.output

    def test_url_cleaning(self, tmp_path: Path) -> None:
        """Test URL cleaning."""
        article = tmp_path / "20240115-article.md"
        article.write_text("""---
title: Test Article
source: https://example.com/page?utm_source=twitter&id=123
---

Content here.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["preprocess", str(tmp_path)])
        assert result.exit_code == 0
        assert "Cleaned: 1" in result.output

        # Verify file was updated
        content = article.read_text()
        assert "utm_source" not in content
        assert "id=123" in content

    def test_date_prefix(self, tmp_path: Path) -> None:
        """Test adding date prefix."""
        article = tmp_path / "article.md"
        article.write_text("""---
title: Test Article
source: https://example.com/page
published: 2024-01-15
---

Content here.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["preprocess", str(tmp_path)])
        assert result.exit_code == 0
        assert "Added: 1" in result.output

        # Verify file was renamed
        assert not article.exists()
        new_file = tmp_path / "20240115-article.md"
        assert new_file.exists()

    def test_no_changes_needed(self, tmp_path: Path) -> None:
        """Test when no changes are needed."""
        article = tmp_path / "20240115-Clean-Article.md"
        article.write_text("""---
title: Clean Article
source: https://example.com/page
---

Content here.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["preprocess", str(tmp_path)])
        assert result.exit_code == 0
        assert "Scanned: 1 files" in result.output

    def test_skip_options(self, tmp_path: Path) -> None:
        """Test skip options."""
        # Use a filename that doesn't need sanitization
        article = tmp_path / "Test-Article.md"
        article.write_text("""---
title: Test Article
source: https://example.com/page?utm_source=twitter
published: 2024-01-15
---

Content here.
""")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["preprocess", "--no-url-clean", "--no-date-prefix", str(tmp_path)],
        )
        assert result.exit_code == 0

        # File should still exist (possibly with slightly modified name due to sanitization)
        files = list(tmp_path.glob("*.md"))
        assert len(files) == 1
        content = files[0].read_text()
        # URL should not be cleaned when --no-url-clean is used
        assert "utm_source" in content


class TestPreprocessErrors:
    """Tests for error handling in preprocess command."""

    def test_file_with_invalid_frontmatter(self, tmp_path: Path) -> None:
        """Test handling file with invalid YAML frontmatter."""
        article = tmp_path / "20240115-invalid.md"
        article.write_text("""---
title: "unclosed quote
---

Content here.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["preprocess", str(tmp_path)])
        assert result.exit_code == 0
        # Should still scan the file even with errors
        assert "Scanned: 1 files" in result.output

    def test_frontmatter_fixing(self, tmp_path: Path) -> None:
        """Test frontmatter fixing with multi-line wikilinks."""
        article = tmp_path / "20240115-article.md"
        article.write_text("""---
title: "[[Multi
Line]]"
source: https://example.com/page
---

Content here.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["preprocess", str(tmp_path)])
        assert result.exit_code == 0
        assert "Scanned: 1 files" in result.output

    def test_no_frontmatter_fix_option(self, tmp_path: Path) -> None:
        """Test --no-frontmatter-fix option."""
        article = tmp_path / "20240115-article.md"
        article.write_text("""---
title: Test
source: https://example.com/page
---

Content here.
""")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["preprocess", "--no-frontmatter-fix", str(tmp_path)],
        )
        assert result.exit_code == 0

    def test_no_dedupe_option(self, tmp_path: Path) -> None:
        """Test --no-dedupe option."""
        article = tmp_path / "20240115-article.md"
        article.write_text("""---
title: Test
source: https://example.com/page
---

Content here.
""")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["preprocess", "--no-dedupe", str(tmp_path)],
        )
        assert result.exit_code == 0


class TestPreprocessIntegration:
    """Integration tests for preprocessing."""

    def test_multiple_files(self, tmp_path: Path) -> None:
        """Test processing multiple files."""
        # Create multiple test files
        for i in range(3):
            article = tmp_path / f"article{i}.md"
            article.write_text(f"""---
title: Article {i}
source: https://example.com/page{i}
published: 2024-01-1{i + 5}
---

Content {i}.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["preprocess", str(tmp_path)])
        assert result.exit_code == 0
        assert "Scanned: 3 files" in result.output

    def test_nested_directories(self, tmp_path: Path) -> None:
        """Test processing nested directories."""
        # Create nested structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        article1 = tmp_path / "20240115-root.md"
        article1.write_text("""---
title: Root Article
---

Content.
""")

        article2 = subdir / "20240115-nested.md"
        article2.write_text("""---
title: Nested Article
---

Content.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["preprocess", str(tmp_path)])
        assert result.exit_code == 0
        assert "Scanned: 2 files" in result.output

    def test_exclude_hidden_folders(self, tmp_path: Path) -> None:
        """Test that hidden folders are excluded."""
        # Create hidden folder
        hidden = tmp_path / ".hidden"
        hidden.mkdir()

        article1 = tmp_path / "20240115-visible.md"
        article1.write_text("""---
title: Visible Article
---

Content.
""")

        article2 = hidden / "20240115-hidden.md"
        article2.write_text("""---
title: Hidden Article
---

Content.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["preprocess", str(tmp_path)])
        assert result.exit_code == 0
        # Should only scan the visible file
        assert "Scanned: 1 files" in result.output

    def test_duplicate_detection(self, tmp_path: Path) -> None:
        """Test that duplicates are detected by URL."""
        # Create two files with the same source URL
        article1 = tmp_path / "20240115-article1.md"
        article1.write_text("""---
title: Article 1
source: https://example.com/same-page
---

Content 1.
""")

        article2 = tmp_path / "20240115-article2.md"
        article2.write_text("""---
title: Article 2
source: https://example.com/same-page
---

Content 2.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["preprocess", str(tmp_path)])
        assert result.exit_code == 0
        assert "Duplicates found: 1 groups" in result.output

    def test_filename_sanitization(self, tmp_path: Path) -> None:
        """Test filename sanitization with special characters."""
        # Use characters that are actually removed by the sanitizer
        article = tmp_path / "20240115-Article with spaces.md"
        article.write_text("""---
title: Test Article
source: https://example.com/page
---

Content here.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["preprocess", str(tmp_path)])
        assert result.exit_code == 0
        # Original file should be renamed
        assert not article.exists()
        # Sanitized filename should exist
        files = list(tmp_path.glob("*.md"))
        assert len(files) == 1
        # Check spaces were replaced with dashes
        assert " " not in files[0].name

    def test_no_filename_clean_option(self, tmp_path: Path) -> None:
        """Test --no-filename-clean option."""
        article = tmp_path / "20240115-Test-Article.md"
        article.write_text("""---
title: Test Article
source: https://example.com/page
---

Content here.
""")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["preprocess", "--no-filename-clean", str(tmp_path)],
        )
        assert result.exit_code == 0
        # File should still exist with original name
        assert article.exists()
