"""Unit tests for mover core logic."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from clipmd.core.mover import (
    MoveInstruction,
    _levenshtein_distance,
    _update_cache_after_moves,
    apply_domain_rules_fallback,
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


class TestApplyDomainRulesFallback:
    """Tests for apply_domain_rules_fallback function."""

    def test_no_rules_returns_empty(self, tmp_path: Path) -> None:
        """Test that empty rules dict returns no instructions."""
        from clipmd.config import Config

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "article.md").write_text(
            "---\nsource: https://example.com/article\n---\nContent"
        )

        config = Config(domain_rules={})
        result = apply_domain_rules_fallback(source_dir, config, set())
        assert result == []

    def test_matches_domain_rule(self, tmp_path: Path) -> None:
        """Test that unmapped articles matching domain rules are returned."""
        from clipmd.config import Config

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "article.md").write_text(
            "---\nsource: https://github.com/user/repo\n---\nContent"
        )

        config = Config(domain_rules={"github.com": "Code"})
        result = apply_domain_rules_fallback(source_dir, config, set())
        assert len(result) == 1
        assert result[0].filename == "article.md"
        assert result[0].category == "Code"
        assert result[0].line_number == -1  # Indicates fallback

    def test_skips_mapped_files(self, tmp_path: Path) -> None:
        """Test that files already in categorization are skipped."""
        from clipmd.config import Config

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "article.md").write_text(
            "---\nsource: https://github.com/user/repo\n---\nContent"
        )

        config = Config(domain_rules={"github.com": "Code"})
        result = apply_domain_rules_fallback(source_dir, config, {"article.md"})
        assert result == []

    def test_skips_ignored_files(self, tmp_path: Path) -> None:
        """Test that configured ignored files are skipped."""
        from clipmd.config import Config, SpecialFoldersConfig

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "README.md").write_text(
            "---\nsource: https://github.com/user/repo\n---\nContent"
        )

        special_folders = SpecialFoldersConfig(ignore_files=["README.md"])
        config = Config(
            domain_rules={"github.com": "Code"},
            special_folders=special_folders,
        )
        result = apply_domain_rules_fallback(source_dir, config, set())
        assert result == []

    def test_no_url_skips_file(self, tmp_path: Path) -> None:
        """Test that files without URLs in frontmatter are skipped."""
        from clipmd.config import Config

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "article.md").write_text("---\ntitle: No URL here\n---\nContent")

        config = Config(domain_rules={"github.com": "Code"})
        result = apply_domain_rules_fallback(source_dir, config, set())
        assert result == []

    def test_no_matching_rule_skips_file(self, tmp_path: Path) -> None:
        """Test that files without matching domain rules are skipped."""
        from clipmd.config import Config

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "article.md").write_text(
            "---\nsource: https://example.com/article\n---\nContent"
        )

        config = Config(domain_rules={"github.com": "Code"})
        result = apply_domain_rules_fallback(source_dir, config, set())
        assert result == []

    def test_invalid_folder_from_rule_is_skipped(self, tmp_path: Path) -> None:
        """Test that invalid folder names from rules are skipped (security)."""
        from clipmd.config import Config

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "article.md").write_text(
            "---\nsource: https://example.com/article\n---\nContent"
        )

        # Simulate rule that returns invalid path (path traversal attempt)
        config = Config(domain_rules={"example.com": "../Outside"})
        result = apply_domain_rules_fallback(source_dir, config, set())
        assert result == []

    def test_case_insensitive_domain_matching(self, tmp_path: Path) -> None:
        """Test that domain matching is case-insensitive."""
        from clipmd.config import Config

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "article.md").write_text(
            "---\nsource: https://GitHub.COM/user/repo\n---\nContent"
        )

        config = Config(domain_rules={"github.com": "Code"})
        result = apply_domain_rules_fallback(source_dir, config, set())
        assert len(result) == 1
        assert result[0].category == "Code"

    def test_unparseable_file_is_skipped(self, tmp_path: Path) -> None:
        """Test that files with unicode errors are skipped gracefully."""
        from clipmd.config import Config

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        # Write binary garbage that can't be decoded as UTF-8
        (source_dir / "bad.md").write_bytes(b"\xff\xfe\x00\x00")

        config = Config(domain_rules={"github.com": "Code"})
        # Should not raise, should return empty list
        result = apply_domain_rules_fallback(source_dir, config, set())
        assert result == []

    def test_multiple_files_multiple_rules(self, tmp_path: Path) -> None:
        """Test multiple files against multiple domain rules."""
        from clipmd.config import Config

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "github.md").write_text(
            "---\nsource: https://github.com/user/repo\n---\nContent"
        )
        (source_dir / "news.md").write_text(
            "---\nsource: https://techcrunch.com/article\n---\nContent"
        )
        (source_dir / "doc.md").write_text("---\nsource: https://docs.python.org/\n---\nContent")

        config = Config(
            domain_rules={
                "github.com": "Code",
                "techcrunch.com": "News",
                "docs.python.org": "Docs",
            }
        )
        result = apply_domain_rules_fallback(source_dir, config, set())
        assert len(result) == 3
        # Results should be sorted by filename (glob sorts them)
        filenames = {r.filename for r in result}
        assert filenames == {"doc.md", "github.md", "news.md"}


class TestUpdateCacheAfterMoves:
    """Tests for _update_cache_after_moves function."""

    def _make_instruction(self, filename: str, category: str) -> MoveInstruction:
        return MoveInstruction(
            index=1,
            category=category,
            filename=filename,
            line_number=-1,
            is_trash=False,
        )

    def test_adds_uncached_article_to_cache(self, tmp_path: Path) -> None:
        """Article in organized folder but not in cache gets added to cache."""
        from clipmd.config import Config
        from clipmd.core.cache import load_cache

        cache_path = tmp_path / ".clipmd" / "cache.json"
        cache_path.parent.mkdir()
        dest_folder = tmp_path / "Tech"
        dest_folder.mkdir()
        article = dest_folder / "article.md"
        article.write_text("---\ntitle: Test\nsource: https://example.com/article\n---\nContent")

        config = Config(vault=tmp_path, cache=cache_path)
        instruction = self._make_instruction("article.md", "Tech")
        _update_cache_after_moves([instruction], tmp_path, config)

        cache = load_cache(cache_path)
        entry = cache.get("https://example.com/article")
        assert entry is not None
        assert entry.folder == "Tech"

    def test_trashes_source_when_blocked_by_existing_destination(self, tmp_path: Path) -> None:
        """Source file in vault root is trashed when destination already exists."""
        from clipmd.config import Config

        cache_path = tmp_path / ".clipmd" / "cache.json"
        cache_path.parent.mkdir()
        dest_folder = tmp_path / "Tech"
        dest_folder.mkdir()

        # Destination already exists (organized copy)
        dest_article = dest_folder / "article.md"
        dest_article.write_text("---\ntitle: Test\nsource: https://example.com/article\n---\nOld")

        # Source still exists in vault root (blocked move)
        source_article = tmp_path / "article.md"
        source_article.write_text("---\ntitle: Test\nsource: https://example.com/article\n---\nNew")

        config = Config(vault=tmp_path, cache=cache_path)
        instruction = self._make_instruction("article.md", "Tech")

        with patch("clipmd.core.mover.send2trash") as mock_trash:
            _update_cache_after_moves([instruction], tmp_path, config)
            mock_trash.assert_called_once_with(str(source_article))

    def test_trashes_source_when_url_already_in_cache(self, tmp_path: Path) -> None:
        """Source file is trashed even when URL was already in cache (re-fetch scenario)."""
        from clipmd.config import Config
        from clipmd.core.cache import load_cache

        cache_path = tmp_path / ".clipmd" / "cache.json"
        cache_path.parent.mkdir()
        dest_folder = tmp_path / "Tech"
        dest_folder.mkdir()

        # Pre-populate cache with the URL
        cache = load_cache(cache_path)
        cache.add(url="https://example.com/article", filename="article.md", title="Test")
        cache.save(cache_path)

        dest_article = dest_folder / "article.md"
        dest_article.write_text("---\ntitle: Test\nsource: https://example.com/article\n---\nOld")
        source_article = tmp_path / "article.md"
        source_article.write_text("---\ntitle: Test\nsource: https://example.com/article\n---\nNew")

        config = Config(vault=tmp_path, cache=cache_path)
        instruction = self._make_instruction("article.md", "Tech")

        with patch("clipmd.core.mover.send2trash") as mock_trash:
            _update_cache_after_moves([instruction], tmp_path, config)
            mock_trash.assert_called_once_with(str(source_article))

        # Cache location should be updated to organized folder
        updated_cache = load_cache(cache_path)
        entry = updated_cache.get("https://example.com/article")
        assert entry is not None
        assert entry.folder == "Tech"

    def test_handles_unreadable_dest_gracefully(self, tmp_path: Path) -> None:
        """Unreadable destination file is silently skipped (no exception raised)."""
        from clipmd.config import Config

        cache_path = tmp_path / ".clipmd" / "cache.json"
        cache_path.parent.mkdir()
        dest_folder = tmp_path / "Tech"
        dest_folder.mkdir()
        # Write binary garbage that fails frontmatter parsing
        (dest_folder / "article.md").write_bytes(b"\xff\xfe\x00\x00bad utf8")

        config = Config(vault=tmp_path, cache=cache_path)
        instruction = self._make_instruction("article.md", "Tech")
        # Should not raise
        _update_cache_after_moves([instruction], tmp_path, config)

    def test_skips_when_dest_does_not_exist(self, tmp_path: Path) -> None:
        """When destination doesn't exist (move truly failed), instruction is skipped."""
        from clipmd.config import Config
        from clipmd.core.cache import load_cache

        cache_path = tmp_path / ".clipmd" / "cache.json"
        cache_path.parent.mkdir()
        # No dest folder created, no dest file

        config = Config(vault=tmp_path, cache=cache_path)
        instruction = self._make_instruction("missing.md", "Tech")
        _update_cache_after_moves([instruction], tmp_path, config)

        # Cache should remain empty
        cache = load_cache(cache_path)
        assert len(cache.entries) == 0

    def test_no_url_in_frontmatter_still_trashes_source(self, tmp_path: Path) -> None:
        """Source file is trashed even when destination has no source URL in frontmatter."""
        from clipmd.config import Config

        cache_path = tmp_path / ".clipmd" / "cache.json"
        cache_path.parent.mkdir()
        dest_folder = tmp_path / "Tech"
        dest_folder.mkdir()
        (dest_folder / "article.md").write_text("---\ntitle: Test\n---\nContent")

        source_article = tmp_path / "article.md"
        source_article.write_text("---\ntitle: Test\n---\nContent")

        config = Config(vault=tmp_path, cache=cache_path)
        instruction = self._make_instruction("article.md", "Tech")

        with patch("clipmd.core.mover.send2trash") as mock_trash:
            _update_cache_after_moves([instruction], tmp_path, config)
            mock_trash.assert_called_once_with(str(source_article))

    def test_trash_instruction_marks_removed_in_cache(self, tmp_path: Path) -> None:
        """Trash instruction marks cached URL as removed when file is gone."""
        from clipmd.config import Config
        from clipmd.core.cache import load_cache

        cache_path = tmp_path / ".clipmd" / "cache.json"
        cache_path.parent.mkdir()

        # Pre-populate cache
        cache = load_cache(cache_path)
        cache.add(url="https://example.com/article", filename="article.md", title="Test")
        cache.save(cache_path)

        # File is already gone (was trashed by execute_move)
        config = Config(vault=tmp_path, cache=cache_path)
        trash_instruction = MoveInstruction(
            index=1, category="TRASH", filename="article.md", line_number=-1, is_trash=True
        )
        _update_cache_after_moves([trash_instruction], tmp_path, config)

        updated_cache = load_cache(cache_path)
        entry = updated_cache.get("https://example.com/article")
        assert entry is not None
        assert entry.removed is True

    def test_trash_instruction_skipped_when_file_still_exists(self, tmp_path: Path) -> None:
        """Trash instruction is skipped if source file still exists (move didn't happen)."""
        from clipmd.config import Config
        from clipmd.core.cache import load_cache

        cache_path = tmp_path / ".clipmd" / "cache.json"
        cache_path.parent.mkdir()
        cache = load_cache(cache_path)
        cache.add(url="https://example.com/article", filename="article.md", title="Test")
        cache.save(cache_path)

        # File still exists — trash didn't happen
        (tmp_path / "article.md").write_text("content")

        config = Config(vault=tmp_path, cache=cache_path)
        trash_instruction = MoveInstruction(
            index=1, category="TRASH", filename="article.md", line_number=-1, is_trash=True
        )
        _update_cache_after_moves([trash_instruction], tmp_path, config)

        # Cache entry should NOT be marked as removed
        updated_cache = load_cache(cache_path)
        entry = updated_cache.get("https://example.com/article")
        assert entry is not None
        assert entry.removed is False

    def test_trash_instruction_no_cache_entry(self, tmp_path: Path) -> None:
        """Trash instruction for uncached file is silently ignored."""
        from clipmd.config import Config
        from clipmd.core.cache import load_cache

        cache_path = tmp_path / ".clipmd" / "cache.json"
        cache_path.parent.mkdir()

        # File is gone, but nothing in cache
        config = Config(vault=tmp_path, cache=cache_path)
        trash_instruction = MoveInstruction(
            index=1, category="TRASH", filename="gone.md", line_number=-1, is_trash=True
        )
        _update_cache_after_moves([trash_instruction], tmp_path, config)

        # Cache should remain empty
        cache = load_cache(cache_path)
        assert len(cache.entries) == 0
