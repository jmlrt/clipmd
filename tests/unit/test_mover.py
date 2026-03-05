"""Unit tests for mover core logic."""

from __future__ import annotations

from pathlib import Path

from clipmd.core.mover import (
    MoveInstruction,
    _levenshtein_distance,
    find_suspicious_categories,
    suggest_source_dir,
)


class TestLevenshteinDistance:
    """Tests for _levenshtein_distance helper."""

    def test_identical_strings(self) -> None:
        """Test that identical strings have distance 0."""
        assert _levenshtein_distance("Life-Tips", "Life-Tips") == 0

    def test_single_substitution(self) -> None:
        """Test single character substitution."""
        assert _levenshtein_distance("Lifr-Tips", "Life-Tips") == 1

    def test_single_insertion(self) -> None:
        """Test single character insertion."""
        assert _levenshtein_distance("LifeTips", "Life-Tips") == 1

    def test_single_deletion(self) -> None:
        """Test single character deletion."""
        assert _levenshtein_distance("Life--Tips", "Life-Tips") == 1

    def test_empty_strings(self) -> None:
        """Test distance between empty strings."""
        assert _levenshtein_distance("", "") == 0

    def test_one_empty(self) -> None:
        """Test distance when one string is empty."""
        assert _levenshtein_distance("", "abc") == 3
        assert _levenshtein_distance("abc", "") == 3

    def test_very_different_strings(self) -> None:
        """Test strings with high distance."""
        assert _levenshtein_distance("Science", "Technology") > 2


class TestFindSuspiciousCategories:
    """Tests for find_suspicious_categories function."""

    def _make_instruction(self, category: str, filename: str = "article.md") -> MoveInstruction:
        return MoveInstruction(
            index=1,
            category=category,
            filename=filename,
            line_number=1,
            is_trash=False,
        )

    def test_detects_typo(self, tmp_path: Path) -> None:
        """Test that a typo in category name close to an existing folder is detected."""
        (tmp_path / "Life-Tips").mkdir()
        instructions = [self._make_instruction("Lifr-Tips")]
        suspicious = find_suspicious_categories(instructions, tmp_path)
        assert "Lifr-Tips" in suspicious
        assert suspicious["Lifr-Tips"] == "Life-Tips"

    def test_ignores_exact_match(self, tmp_path: Path) -> None:
        """Test that a category matching an existing folder exactly is not suspicious."""
        (tmp_path / "Life-Tips").mkdir()
        instructions = [self._make_instruction("Life-Tips")]
        suspicious = find_suspicious_categories(instructions, tmp_path)
        assert "Life-Tips" not in suspicious

    def test_ignores_very_different_names(self, tmp_path: Path) -> None:
        """Test that a very different category name is not flagged."""
        (tmp_path / "Science").mkdir()
        instructions = [self._make_instruction("Technology")]
        suspicious = find_suspicious_categories(instructions, tmp_path)
        assert "Technology" not in suspicious

    def test_ignores_trash_category(self, tmp_path: Path) -> None:
        """Test that TRASH instructions are not checked for fuzzy matching."""
        (tmp_path / "Tras").mkdir()
        instruction = MoveInstruction(
            index=1,
            category="TRASH",
            filename="article.md",
            line_number=1,
            is_trash=True,
        )
        suspicious = find_suspicious_categories([instruction], tmp_path)
        assert len(suspicious) == 0

    def test_no_existing_folders(self, tmp_path: Path) -> None:
        """Test with no existing folders — nothing is suspicious."""
        instructions = [self._make_instruction("NewFolder")]
        suspicious = find_suspicious_categories(instructions, tmp_path)
        assert len(suspicious) == 0

    def test_custom_max_distance(self, tmp_path: Path) -> None:
        """Test custom max_distance parameter."""
        (tmp_path / "Life-Tips").mkdir()
        # "Lif-Tps" has distance 2 from "Life-Tips" (delete 'e', delete 'i')
        instructions = [self._make_instruction("Lif-Tps")]
        # With max_distance=1 it should NOT be flagged
        suspicious = find_suspicious_categories(instructions, tmp_path, max_distance=1)
        assert "Lif-Tps" not in suspicious
        # With max_distance=2 it SHOULD be flagged
        suspicious = find_suspicious_categories(instructions, tmp_path, max_distance=2)
        assert "Lif-Tps" in suspicious


class TestSuggestSourceDir:
    """Tests for suggest_source_dir function."""

    def test_finds_subdirectory_containing_file(self, tmp_path: Path) -> None:
        """Test that the subdirectory containing a missing file is suggested."""
        inbox = tmp_path / "Inbox"
        inbox.mkdir()
        (inbox / "article.md").write_text("content")
        result = suggest_source_dir(["article.md"], tmp_path)
        assert result == ["Inbox"]

    def test_returns_multiple_dirs_when_files_spread(self, tmp_path: Path) -> None:
        """Test that multiple directories are returned when files are in different subdirs."""
        (tmp_path / "Inbox").mkdir()
        (tmp_path / "Inbox" / "article1.md").write_text("content")
        (tmp_path / "Archive").mkdir()
        (tmp_path / "Archive" / "article2.md").write_text("content")
        result = suggest_source_dir(["article1.md", "article2.md"], tmp_path)
        assert result == ["Archive", "Inbox"]

    def test_returns_empty_when_file_not_found_anywhere(self, tmp_path: Path) -> None:
        """Test that an empty list is returned when the file doesn't exist anywhere."""
        result = suggest_source_dir(["nonexistent.md"], tmp_path)
        assert result == []

    def test_ignores_files_at_vault_root(self, tmp_path: Path) -> None:
        """Test that files at vault root (not in a subdirectory) are not suggested."""
        (tmp_path / "article.md").write_text("content")
        result = suggest_source_dir(["article.md"], tmp_path)
        assert result == []
