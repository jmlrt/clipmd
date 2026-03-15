"""Unit tests for mover core logic."""

from __future__ import annotations

from pathlib import Path

import pytest

from clipmd.core.mover import (
    MoveInstruction,
    _levenshtein_distance,
    find_suspicious_categories,
    parse_json_categorization,
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


class TestParseJsonCategorization:
    """Tests for parse_json_categorization function."""

    def test_valid_input_multiple_items(self) -> None:
        """Test parsing valid JSON with multiple items."""
        json_str = '[{"file": "article1.md", "folder": "Tech"}, {"file": "article2.md", "folder": "Science"}]'
        instructions = parse_json_categorization(json_str)
        assert len(instructions) == 2
        assert instructions[0].filename == "article1.md"
        assert instructions[0].category == "Tech"
        assert instructions[0].index == 1
        assert not instructions[0].is_trash
        assert instructions[1].filename == "article2.md"
        assert instructions[1].category == "Science"
        assert instructions[1].index == 2

    def test_trash_folder_sets_is_trash(self) -> None:
        """Test that TRASH folder sets is_trash=True."""
        json_str = '[{"file": "duplicate.md", "folder": "TRASH"}]'
        instructions = parse_json_categorization(json_str)
        assert len(instructions) == 1
        assert instructions[0].filename == "duplicate.md"
        assert instructions[0].category == "TRASH"
        assert instructions[0].is_trash is True

    def test_trash_lowercase_sets_is_trash(self) -> None:
        """Test that lowercase 'trash' also sets is_trash=True."""
        json_str = '[{"file": "duplicate.md", "folder": "trash"}]'
        instructions = parse_json_categorization(json_str)
        assert instructions[0].is_trash is True

    def test_invalid_json_raises_error(self) -> None:
        """Test that invalid JSON raises ValueError."""
        json_str = '{"file": "article.md"'  # Invalid: missing closing brace
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_json_categorization(json_str)

    def test_non_list_json_raises_error(self) -> None:
        """Test that non-list JSON raises ValueError."""
        json_str = '{"file": "article.md", "folder": "Tech"}'
        with pytest.raises(ValueError, match="JSON must be a list"):
            parse_json_categorization(json_str)

    def test_missing_file_key_raises_error(self) -> None:
        """Test that missing 'file' key raises ValueError."""
        json_str = '[{"folder": "Tech"}]'
        with pytest.raises(ValueError, match="missing required keys"):
            parse_json_categorization(json_str)

    def test_missing_folder_key_raises_error(self) -> None:
        """Test that missing 'folder' key raises ValueError."""
        json_str = '[{"file": "article.md"}]'
        with pytest.raises(ValueError, match="missing required keys"):
            parse_json_categorization(json_str)

    def test_non_dict_item_raises_error(self) -> None:
        """Test that non-dict items raise ValueError."""
        json_str = '["not a dict"]'
        with pytest.raises(ValueError, match="must be an object"):
            parse_json_categorization(json_str)

    def test_empty_list_returns_empty(self) -> None:
        """Test that empty list returns empty instructions."""
        json_str = "[]"
        instructions = parse_json_categorization(json_str)
        assert instructions == []

    def test_file_with_path_separator_raises_error(self) -> None:
        """Test that file with path separator raises ValueError."""
        json_str = '[{"file": "subdir/article.md", "folder": "Tech"}]'
        with pytest.raises(ValueError, match="'file' must be a basename"):
            parse_json_categorization(json_str)

    def test_file_with_backslash_raises_error(self) -> None:
        """Test that file with backslash raises ValueError."""
        json_str = '[{"file": "subdir\\\\article.md", "folder": "Tech"}]'
        with pytest.raises(ValueError, match="'file' must be a basename"):
            parse_json_categorization(json_str)

    def test_file_with_path_traversal_raises_error(self) -> None:
        """Test that file with path traversal (..) raises ValueError."""
        json_str = '[{"file": "../article.md", "folder": "Tech"}]'
        with pytest.raises(ValueError, match="'file' must be a basename"):
            parse_json_categorization(json_str)

    def test_file_absolute_path_raises_error(self) -> None:
        """Test that absolute file path raises ValueError."""
        json_str = '[{"file": "/article.md", "folder": "Tech"}]'
        with pytest.raises(ValueError, match="'file' must be a basename"):
            parse_json_categorization(json_str)

    def test_folder_with_path_separator_raises_error(self) -> None:
        """Test that folder with path separator raises ValueError."""
        json_str = '[{"file": "article.md", "folder": "Tech/News"}]'
        with pytest.raises(ValueError, match="must contain only letters"):
            parse_json_categorization(json_str)

    def test_folder_with_path_traversal_raises_error(self) -> None:
        """Test that folder with path traversal (..) raises ValueError."""
        json_str = '[{"file": "article.md", "folder": "../Outside"}]'
        with pytest.raises(ValueError, match="must contain only letters"):
            parse_json_categorization(json_str)

    def test_folder_absolute_path_raises_error(self) -> None:
        """Test that absolute folder path raises ValueError."""
        json_str = '[{"file": "article.md", "folder": "/etc/passwd"}]'
        with pytest.raises(ValueError, match="must contain only letters"):
            parse_json_categorization(json_str)

    def test_trash_folder_bypasses_path_validation(self) -> None:
        """Test that TRASH folder is not validated for path separators."""
        json_str = '[{"file": "article.md", "folder": "TRASH"}]'
        instructions = parse_json_categorization(json_str)
        assert len(instructions) == 1
        assert instructions[0].is_trash is True

    def test_file_with_double_dot_in_name_is_allowed(self) -> None:
        """Test that legitimate filenames with .. substring are allowed."""
        json_str = '[{"file": "my..notes.md", "folder": "Tech"}]'
        instructions = parse_json_categorization(json_str)
        assert len(instructions) == 1
        assert instructions[0].filename == "my..notes.md"

    def test_folder_with_invalid_chars_raises_error(self) -> None:
        """Test that folder names with invalid characters are rejected."""
        for invalid_folder in ["News.Updates", "Tech News", "cat@home", "News..Updates"]:
            json_str = f'[{{"file": "article.md", "folder": "{invalid_folder}"}}]'
            with pytest.raises(ValueError, match="must contain only letters"):
                parse_json_categorization(json_str)

    def test_folder_dot_raises_error(self) -> None:
        """Test that '.' as folder name is rejected."""
        json_str = '[{"file": "article.md", "folder": "."}]'
        with pytest.raises(ValueError, match="must contain only letters"):
            parse_json_categorization(json_str)

    def test_folder_dotdot_raises_error(self) -> None:
        """Test that '..' as folder name is rejected."""
        json_str = '[{"file": "article.md", "folder": ".."}]'
        with pytest.raises(ValueError, match="must contain only letters"):
            parse_json_categorization(json_str)

    def test_file_with_leading_trailing_whitespace_is_stripped(self) -> None:
        """Test that whitespace is stripped from file names."""
        json_str = '[{"file": "  article.md  ", "folder": "Tech"}]'
        instructions = parse_json_categorization(json_str)
        assert len(instructions) == 1
        assert instructions[0].filename == "article.md"

    def test_folder_with_leading_trailing_whitespace_is_stripped(self) -> None:
        """Test that whitespace is stripped from folder names."""
        json_str = '[{"file": "article.md", "folder": "  Tech  "}]'
        instructions = parse_json_categorization(json_str)
        assert len(instructions) == 1
        assert instructions[0].category == "Tech"

    def test_trash_with_whitespace_is_recognized(self) -> None:
        """Test that TRASH with surrounding whitespace is still recognized."""
        json_str = '[{"file": "article.md", "folder": "  TRASH  "}]'
        instructions = parse_json_categorization(json_str)
        assert len(instructions) == 1
        assert instructions[0].is_trash is True
        assert instructions[0].category == "TRASH"
