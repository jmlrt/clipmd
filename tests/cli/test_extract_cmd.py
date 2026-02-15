"""CLI tests for extract command."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from click.testing import CliRunner

from clipmd.cli import main


class TestExtractCommand:
    """Tests for the extract command."""

    def test_help(self) -> None:
        """Test --help option."""
        runner = CliRunner()
        result = runner.invoke(main, ["extract", "--help"])
        assert result.exit_code == 0
        assert "extract" in result.output.lower()

    def test_basic_extraction(self, tmp_path: Path) -> None:
        """Test basic metadata extraction."""
        article = tmp_path / "20240115-Article.md"
        article.write_text("""---
title: Test Article
source: https://example.com/page
description: This is a test article description.
---

Article content here.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["extract", str(tmp_path)])
        assert result.exit_code == 0
        assert "Articles Metadata" in result.output
        assert "Total: 1 articles" in result.output
        assert "20240115-Article.md" in result.output
        assert "Test Article" in result.output

    def test_json_format(self, tmp_path: Path) -> None:
        """Test JSON output format."""
        article = tmp_path / "20240115-Article.md"
        article.write_text("""---
title: JSON Test
source: https://example.com/json
---

Content here.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["extract", "--format", "json", str(tmp_path)])
        assert result.exit_code == 0

        # Parse JSON output
        data = json.loads(result.output)
        assert data["total"] == 1
        assert len(data["articles"]) == 1
        assert data["articles"][0]["title"] == "JSON Test"

    def test_yaml_format(self, tmp_path: Path) -> None:
        """Test YAML output format."""
        article = tmp_path / "20240115-Article.md"
        article.write_text("""---
title: YAML Test
source: https://example.com/yaml
---

Content here.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["extract", "--format", "yaml", str(tmp_path)])
        assert result.exit_code == 0

        # Parse YAML output
        data = yaml.safe_load(result.output)
        assert data["total"] == 1
        assert len(data["articles"]) == 1

    def test_max_chars(self, tmp_path: Path) -> None:
        """Test max-chars option limits description."""
        article = tmp_path / "20240115-Article.md"
        article.write_text("""---
title: Long Description Test
source: https://example.com/long
description: This is a very long description that should be truncated when the max-chars option is set to a small value.
---

Content here.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["extract", "--max-chars", "20", str(tmp_path)])
        assert result.exit_code == 0
        # Description should be truncated with ellipsis
        assert "..." in result.output

    def test_include_folders(self, tmp_path: Path) -> None:
        """Test --folders option includes existing folders."""
        # Create folders
        (tmp_path / "Tech").mkdir()
        (tmp_path / "Science").mkdir()
        (tmp_path / ".hidden").mkdir()  # Should be excluded

        article = tmp_path / "20240115-Article.md"
        article.write_text("""---
title: Test
---

Content.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["extract", "--folders", str(tmp_path)])
        assert result.exit_code == 0
        assert "Existing Folders" in result.output
        assert "Tech" in result.output
        assert "Science" in result.output
        assert ".hidden" not in result.output

    def test_no_content_option(self, tmp_path: Path) -> None:
        """Test --no-content option skips content preview."""
        article = tmp_path / "20240115-Article.md"
        article.write_text("""---
title: No Content Test
source: https://example.com/no-content
---

This content should not appear in the description.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["extract", "--no-content", str(tmp_path)])
        assert result.exit_code == 0
        # Content should not be used as description fallback
        assert "This content should not appear" not in result.output

    def test_content_as_description_fallback(self, tmp_path: Path) -> None:
        """Test content is used when no description field."""
        article = tmp_path / "20240115-Article.md"
        article.write_text("""---
title: Content Fallback Test
source: https://example.com/content
---

This content should be used as description.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["extract", str(tmp_path)])
        assert result.exit_code == 0
        assert "This content should be used" in result.output

    def test_output_file(self, tmp_path: Path) -> None:
        """Test writing output to file."""
        article = tmp_path / "20240115-Article.md"
        article.write_text("""---
title: Output File Test
---

Content.
""")

        output_file = tmp_path / "metadata.txt"
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["extract", "--output", str(output_file), str(tmp_path)],
        )
        assert result.exit_code == 0
        assert output_file.exists()
        content = output_file.read_text()
        assert "Output File Test" in content

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Test extraction from empty directory."""
        runner = CliRunner()
        result = runner.invoke(main, ["extract", str(tmp_path)])
        assert result.exit_code == 0
        assert "Total: 0 articles" in result.output


class TestExtractWithStats:
    """Tests for extract command with --include-stats."""

    def test_word_count(self, tmp_path: Path) -> None:
        """Test word count is included with --include-stats."""
        article = tmp_path / "20240115-Article.md"
        article.write_text("""---
title: Word Count Test
source: https://example.com/words
---

This is some content with multiple words to count.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["extract", "--include-stats", str(tmp_path)])
        assert result.exit_code == 0
        # Should include word count
        assert "words" in result.output


class TestExtractMultipleFiles:
    """Tests for extracting multiple files."""

    def test_multiple_articles(self, tmp_path: Path) -> None:
        """Test extracting multiple articles."""
        for i in range(3):
            article = tmp_path / f"2024011{i + 5}-Article-{i}.md"
            article.write_text(f"""---
title: Article {i}
source: https://example.com/article{i}
---

Content {i}.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["extract", str(tmp_path)])
        assert result.exit_code == 0
        assert "Total: 3 articles" in result.output
        assert "Article 0" in result.output
        assert "Article 1" in result.output
        assert "Article 2" in result.output

    def test_excludes_hidden_files(self, tmp_path: Path) -> None:
        """Test that hidden files are excluded."""
        visible = tmp_path / "20240115-Visible.md"
        visible.write_text("""---
title: Visible
---

Content.
""")

        hidden = tmp_path / ".hidden-article.md"
        hidden.write_text("""---
title: Hidden
---

Content.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["extract", str(tmp_path)])
        assert result.exit_code == 0
        assert "Total: 1 articles" in result.output
        assert "Visible" in result.output
        assert "Hidden" not in result.output

    def test_only_root_files(self, tmp_path: Path) -> None:
        """Test that only files in root are extracted (not subfolders)."""
        root_article = tmp_path / "20240115-Root.md"
        root_article.write_text("""---
title: Root Article
---

Content.
""")

        subfolder = tmp_path / "Subfolder"
        subfolder.mkdir()
        nested_article = subfolder / "20240116-Nested.md"
        nested_article.write_text("""---
title: Nested Article
---

Content.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["extract", str(tmp_path)])
        assert result.exit_code == 0
        assert "Total: 1 articles" in result.output
        assert "Root Article" in result.output
        assert "Nested Article" not in result.output


class TestExtractEdgeCases:
    """Tests for edge cases in extract."""

    def test_file_read_error(self, tmp_path: Path) -> None:
        """Test handling file read errors gracefully."""
        # Create an article with invalid encoding simulation
        article = tmp_path / "20240115-Article.md"
        article.write_text("""---
title: Test
---

Content.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["extract", str(tmp_path)])
        assert result.exit_code == 0

    def test_missing_frontmatter_fields(self, tmp_path: Path) -> None:
        """Test extraction when frontmatter has minimal fields."""
        article = tmp_path / "20240115-Minimal.md"
        article.write_text("""---
title: Minimal Article
---

Just content, no URL or description.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["extract", "--format", "json", str(tmp_path)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total"] == 1
        assert data["articles"][0]["title"] == "Minimal Article"

    def test_short_description(self, tmp_path: Path) -> None:
        """Test description shorter than max_chars doesn't get truncated."""
        article = tmp_path / "20240115-Short.md"
        article.write_text("""---
title: Short Description
description: Short desc.
---

Content.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["extract", "--max-chars", "200", str(tmp_path)])
        assert result.exit_code == 0
        assert "Short desc." in result.output
        # No ellipsis since it's short
        assert "Short desc...." not in result.output

    def test_short_content_fallback(self, tmp_path: Path) -> None:
        """Test content fallback when content is shorter than max_chars."""
        article = tmp_path / "20240115-ShortContent.md"
        article.write_text("""---
title: Short Content
---

Very short.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["extract", "--max-chars", "200", str(tmp_path)])
        assert result.exit_code == 0
        assert "Very short." in result.output


class TestExtractParseErrors:
    """Tests for extract error handling."""

    def test_invalid_yaml_frontmatter(self, tmp_path: Path) -> None:
        """Test handling of invalid YAML in frontmatter."""
        article = tmp_path / "20240115-Invalid.md"
        article.write_text("""---
title: Missing quote
description: Value with : colon: everywhere
invalid: [unclosed bracket
---

Content here.
""")

        runner = CliRunner()
        result = runner.invoke(main, ["extract", "--format", "json", str(tmp_path)])
        # Should not crash, may include error or skip the file
        assert result.exit_code == 0
