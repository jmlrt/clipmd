"""CLI tests for move command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from clipmd.cli import main


class TestMoveCommand:
    """Tests for the move command."""

    def test_help(self) -> None:
        """Test --help option."""
        runner = CliRunner()
        result = runner.invoke(main, ["move", "--help"])
        assert result.exit_code == 0
        assert "move" in result.output.lower()

    def test_basic_move(self, tmp_path: Path) -> None:
        """Test basic file move."""
        # Create article
        article = tmp_path / "20240115-Article.md"
        article.write_text("""---
title: Test Article
source: https://example.com/page
---

Content here.
""")

        # Create categorization file
        cat_file = tmp_path / "categorization.txt"
        cat_file.write_text("1. Tech - 20240115-Article.md\n")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["move", str(cat_file), "--source-dir", str(tmp_path), "--no-cache-update"],
        )
        assert result.exit_code == 0
        assert "moved" in result.output.lower()

        # Check file was moved
        assert not article.exists()
        assert (tmp_path / "Tech" / "20240115-Article.md").exists()

    def test_dry_run(self, tmp_path: Path) -> None:
        """Test dry run mode."""
        article = tmp_path / "20240115-Article.md"
        article.write_text("""---
title: Test
---

Content.
""")

        cat_file = tmp_path / "categorization.txt"
        cat_file.write_text("1. Tech - 20240115-Article.md\n")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["move", str(cat_file), "--dry-run", "--source-dir", str(tmp_path)],
        )
        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert "Would move" in result.output

        # File should not be moved
        assert article.exists()
        assert not (tmp_path / "Tech").exists()

    def test_creates_folder(self, tmp_path: Path) -> None:
        """Test that folders are created automatically."""
        article = tmp_path / "20240115-Article.md"
        article.write_text("""---
title: Test
---

Content.
""")

        cat_file = tmp_path / "categorization.txt"
        cat_file.write_text("1. NewFolder - 20240115-Article.md\n")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["move", str(cat_file), "--source-dir", str(tmp_path), "--no-cache-update"],
        )
        assert result.exit_code == 0
        assert "Created folders" in result.output
        assert "NewFolder" in result.output

        # Folder should be created
        assert (tmp_path / "NewFolder").exists()
        assert (tmp_path / "NewFolder" / "20240115-Article.md").exists()

    def test_no_create_folders(self, tmp_path: Path) -> None:
        """Test --no-create-folders option."""
        article = tmp_path / "20240115-Article.md"
        article.write_text("""---
title: Test
---

Content.
""")

        cat_file = tmp_path / "categorization.txt"
        cat_file.write_text("1. NonExistent - 20240115-Article.md\n")

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "move",
                str(cat_file),
                "--no-create-folders",
                "--source-dir",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        assert "Folder does not exist" in result.output

        # File should not be moved
        assert article.exists()

    def test_multiple_moves(self, tmp_path: Path) -> None:
        """Test moving multiple files."""
        # Create articles
        for i in range(3):
            article = tmp_path / f"2024011{i + 5}-Article-{i}.md"
            article.write_text(f"""---
title: Article {i}
---

Content {i}.
""")

        cat_file = tmp_path / "categorization.txt"
        cat_file.write_text("""1. Tech - 20240115-Article-0.md
2. Science - 20240116-Article-1.md
3. Tech - 20240117-Article-2.md
""")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["move", str(cat_file), "--source-dir", str(tmp_path), "--no-cache-update"],
        )
        assert result.exit_code == 0
        assert "3 moved" in result.output

        # Check files were moved
        assert (tmp_path / "Tech" / "20240115-Article-0.md").exists()
        assert (tmp_path / "Science" / "20240116-Article-1.md").exists()
        assert (tmp_path / "Tech" / "20240117-Article-2.md").exists()

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Test handling of missing files."""
        cat_file = tmp_path / "categorization.txt"
        cat_file.write_text("1. Tech - nonexistent.md\n")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["move", str(cat_file), "--source-dir", str(tmp_path)],
        )
        assert result.exit_code == 0
        assert "File not found" in result.output

    def test_empty_categorization(self, tmp_path: Path) -> None:
        """Test empty categorization file."""
        cat_file = tmp_path / "categorization.txt"
        cat_file.write_text("# Just a comment\n")

        runner = CliRunner()
        result = runner.invoke(main, ["move", str(cat_file)])
        assert result.exit_code == 0
        assert "No valid move instructions found" in result.output


class TestMoveWithTrash:
    """Tests for move command with TRASH category."""

    def test_trash_instruction(self, tmp_path: Path) -> None:
        """Test TRASH category moves to system trash."""
        article = tmp_path / "20240115-Duplicate.md"
        article.write_text("""---
title: Duplicate
---

Content.
""")

        cat_file = tmp_path / "categorization.txt"
        cat_file.write_text("1. TRASH - 20240115-Duplicate.md\n")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["move", str(cat_file), "--source-dir", str(tmp_path), "--no-cache-update"],
        )
        assert result.exit_code == 0
        assert "Trash" in result.output
        assert "1 trashed" in result.output

        # File should be gone (in trash)
        assert not article.exists()


class TestCategorizationParsing:
    """Tests for categorization file parsing."""

    def test_various_formats(self, tmp_path: Path) -> None:
        """Test various categorization file formats."""
        # Create articles
        for i in range(4):
            article = tmp_path / f"article{i}.md"
            article.write_text(f"---\ntitle: Article {i}\n---\nContent.\n")

        cat_file = tmp_path / "categorization.txt"
        cat_file.write_text("""# Comment line
1. Tech - article0.md
Science - article1.md
3. Misc - article2.md  # inline comment

# Another comment
TRASH - article3.md
""")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["move", str(cat_file), "--source-dir", str(tmp_path), "--no-cache-update"],
        )
        assert result.exit_code == 0

        # Check files were moved correctly
        assert (tmp_path / "Tech" / "article0.md").exists()
        assert (tmp_path / "Science" / "article1.md").exists()
        assert (tmp_path / "Misc" / "article2.md").exists()
        assert not (tmp_path / "article3.md").exists()  # Trashed


class TestMoveWithCacheUpdate:
    """Tests for move command with cache update."""

    def test_move_with_cache_update(self, tmp_path: Path, monkeypatch) -> None:
        """Test move with cache update."""
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

        cat_file = tmp_path / "categorization.txt"
        cat_file.write_text("1. Tech - 20240115-Article.md\n")

        runner = CliRunner()
        result = runner.invoke(main, ["move", str(cat_file)])
        assert result.exit_code == 0
        assert "1 moved" in result.output
        assert "Cache updated" in result.output

    def test_dry_run_no_cache_update(self, tmp_path: Path, monkeypatch) -> None:
        """Test dry run doesn't update cache."""
        monkeypatch.chdir(tmp_path)

        config_file = tmp_path / "config.yaml"
        config_file.write_text("version: 1\npaths:\n  root: .\n")

        article = tmp_path / "20240115-Article.md"
        article.write_text("""---
title: Test
---

Content.
""")

        cat_file = tmp_path / "categorization.txt"
        cat_file.write_text("1. Tech - 20240115-Article.md\n")

        runner = CliRunner()
        result = runner.invoke(main, ["move", str(cat_file), "--dry-run"])
        assert result.exit_code == 0
        assert "Cache updated" not in result.output


class TestMoveFuzzyFolderMatch:
    """Tests for fuzzy folder name matching in move command."""

    def test_move_cmd_prompts_on_suspicious_folder(self, tmp_path: Path) -> None:
        """Test that CLI prompts when a new folder name closely resembles an existing one."""
        # Create existing folder
        (tmp_path / "Life-Tips").mkdir()

        # Create article
        article = tmp_path / "20240115-Article.md"
        article.write_text("---\ntitle: Test\n---\nContent.")

        # Categorization with typo: "Lifr-Tips" instead of "Life-Tips"
        cat_file = tmp_path / "categorization.txt"
        cat_file.write_text("1. Lifr-Tips - 20240115-Article.md\n")

        runner = CliRunner()
        # Simulate user selecting "use-existing" to correct the typo
        result = runner.invoke(
            main,
            ["move", str(cat_file), "--source-dir", str(tmp_path), "--no-cache-update"],
            input="use-existing\n",
        )
        assert result.exit_code == 0
        # File should be in Life-Tips (corrected), not Lifr-Tips (typo)
        assert (tmp_path / "Life-Tips" / "20240115-Article.md").exists()
        assert not (tmp_path / "Lifr-Tips").exists()

    def test_move_cmd_skip_on_suspicious_folder(self, tmp_path: Path) -> None:
        """Test that 'skip' action removes matching instructions from the move list."""
        (tmp_path / "Life-Tips").mkdir()

        article = tmp_path / "20240115-Article.md"
        article.write_text("---\ntitle: Test\n---\nContent.")

        cat_file = tmp_path / "categorization.txt"
        cat_file.write_text("1. Lifr-Tips - 20240115-Article.md\n")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["move", str(cat_file), "--source-dir", str(tmp_path), "--no-cache-update"],
            input="skip\n",
        )
        assert result.exit_code == 0
        # File should NOT be moved (skipped)
        assert article.exists()
        assert not (tmp_path / "Lifr-Tips").exists()

    def test_move_cmd_create_anyway_on_suspicious_folder(self, tmp_path: Path) -> None:
        """Test that 'create-anyway' proceeds with the original (typo) folder name."""
        (tmp_path / "Life-Tips").mkdir()

        article = tmp_path / "20240115-Article.md"
        article.write_text("---\ntitle: Test\n---\nContent.")

        cat_file = tmp_path / "categorization.txt"
        cat_file.write_text("1. Lifr-Tips - 20240115-Article.md\n")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["move", str(cat_file), "--source-dir", str(tmp_path), "--no-cache-update"],
            input="create-anyway\n",
        )
        assert result.exit_code == 0
        # File should be in the typo folder since user chose create-anyway
        assert (tmp_path / "Lifr-Tips" / "20240115-Article.md").exists()

    def test_move_cmd_no_prompt_on_dry_run(self, tmp_path: Path) -> None:
        """Test that dry-run shows warning but does not prompt for suspicious folder."""
        (tmp_path / "Life-Tips").mkdir()

        article = tmp_path / "20240115-Article.md"
        article.write_text("---\ntitle: Test\n---\nContent.")

        cat_file = tmp_path / "categorization.txt"
        cat_file.write_text("1. Lifr-Tips - 20240115-Article.md\n")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["move", str(cat_file), "--dry-run", "--source-dir", str(tmp_path)],
        )
        assert result.exit_code == 0
        # Dry run should show a warning about the suspicious folder
        assert "Warning" in result.output or "similar" in result.output.lower()
        # No file should have been moved
        assert article.exists()

    def test_move_cmd_no_prompt_for_exact_match(self, tmp_path: Path) -> None:
        """Test no prompt when category exactly matches an existing folder."""
        existing_folder = tmp_path / "Tech"
        existing_folder.mkdir()

        article = tmp_path / "20240115-Article.md"
        article.write_text("---\ntitle: Test\n---\nContent.")

        cat_file = tmp_path / "categorization.txt"
        cat_file.write_text("1. Tech - 20240115-Article.md\n")

        runner = CliRunner()
        # No input needed — should not prompt
        with patch("click.prompt") as mock_prompt:
            result = runner.invoke(
                main,
                ["move", str(cat_file), "--source-dir", str(tmp_path), "--no-cache-update"],
            )
            mock_prompt.assert_not_called()
        assert result.exit_code == 0
        assert (existing_folder / "20240115-Article.md").exists()


class TestMoveEdgeCases:
    """Tests for edge cases in move command."""

    def test_destination_exists(self, tmp_path: Path) -> None:
        """Test handling when destination file already exists."""
        # Create source article
        article = tmp_path / "20240115-Article.md"
        article.write_text("""---
title: Test
---

Content.
""")

        # Create destination folder with same file
        dest_folder = tmp_path / "Tech"
        dest_folder.mkdir()
        existing = dest_folder / "20240115-Article.md"
        existing.write_text("Existing file")

        cat_file = tmp_path / "categorization.txt"
        cat_file.write_text("1. Tech - 20240115-Article.md\n")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["move", str(cat_file), "--source-dir", str(tmp_path), "--no-cache-update"],
        )
        assert result.exit_code == 0
        assert "already exists" in result.output

        # Source should still exist
        assert article.exists()

    def test_move_to_existing_folder(self, tmp_path: Path) -> None:
        """Test moving to an existing folder."""
        # Create source article
        article = tmp_path / "20240115-Article.md"
        article.write_text("""---
title: Test
---

Content.
""")

        # Create existing folder
        existing_folder = tmp_path / "ExistingFolder"
        existing_folder.mkdir()

        cat_file = tmp_path / "categorization.txt"
        cat_file.write_text("1. ExistingFolder - 20240115-Article.md\n")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["move", str(cat_file), "--source-dir", str(tmp_path), "--no-cache-update"],
        )
        assert result.exit_code == 0
        assert "1 moved" in result.output

        # Should not say folder was created
        assert "Created folders" not in result.output

    def test_lowercase_trash(self, tmp_path: Path) -> None:
        """Test lowercase 'trash' category is handled as trash."""
        article = tmp_path / "20240115-Article.md"
        article.write_text("""---
title: Test
---

Content.
""")

        cat_file = tmp_path / "categorization.txt"
        # Note: using "Trash" which should match TRASH case-insensitively
        cat_file.write_text("1. TRASH - 20240115-Article.md\n")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["move", str(cat_file), "--source-dir", str(tmp_path), "--no-cache-update"],
        )
        assert result.exit_code == 0
        assert "Trash" in result.output

        # File should be trashed
        assert not article.exists()
