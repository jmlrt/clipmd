"""Unit tests for frontmatter parsing."""

from __future__ import annotations

import pytest

from clipmd.config import FrontmatterConfig
from clipmd.core.frontmatter import (
    extract_field,
    fix_frontmatter,
    fix_multiline_wikilinks,
    fix_unclosed_quotes,
    fix_unquoted_colons,
    fix_wikilinks,
    get_author,
    get_description,
    get_published_date,
    get_source_url,
    get_title,
    parse_frontmatter,
    serialize_frontmatter,
)
from clipmd.exceptions import ParseError


class TestParseFrontmatter:
    """Tests for parse_frontmatter function."""

    def test_valid_frontmatter(self) -> None:
        """Test parsing valid frontmatter."""
        text = """---
title: Test Article
author: John Doe
---

Content here.
"""
        result = parse_frontmatter(text)
        assert result.has_frontmatter is True
        assert result.data["title"] == "Test Article"
        assert result.data["author"] == "John Doe"
        assert result.content.strip() == "Content here."

    def test_no_frontmatter(self) -> None:
        """Test parsing text without frontmatter."""
        text = "Just content, no frontmatter."
        result = parse_frontmatter(text)
        assert result.has_frontmatter is False
        assert result.data == {}
        assert result.content == text

    def test_empty_frontmatter(self) -> None:
        """Test parsing empty frontmatter."""
        text = """---
---

Content here.
"""
        result = parse_frontmatter(text)
        assert result.has_frontmatter is True
        assert result.data == {}

    def test_invalid_yaml(self) -> None:
        """Test parsing invalid YAML frontmatter."""
        text = """---
title: "unclosed quote
---

Content.
"""
        with pytest.raises(ParseError, match="Invalid frontmatter"):
            parse_frontmatter(text)

    def test_date_values(self) -> None:
        """Test parsing date values in frontmatter."""
        text = """---
published: 2024-01-15
---

Content.
"""
        result = parse_frontmatter(text)
        # YAML parses dates as date objects
        from datetime import date

        assert result.data["published"] == date(2024, 1, 15)


class TestExtractField:
    """Tests for extract_field function."""

    def test_first_match(self) -> None:
        """Test extracting first matching field."""
        data = {"url": "https://example.com", "source": "other"}
        result = extract_field(data, ["source", "url", "link"])
        assert result == "other"

    def test_second_match(self) -> None:
        """Test extracting when first field doesn't exist."""
        data = {"url": "https://example.com"}
        result = extract_field(data, ["source", "url", "link"])
        assert result == "https://example.com"

    def test_no_match(self) -> None:
        """Test default when no fields match."""
        data = {"other": "value"}
        result = extract_field(data, ["source", "url"], default="default")
        assert result == "default"

    def test_default_none(self) -> None:
        """Test default None when no fields match."""
        data = {}
        result = extract_field(data, ["source"])
        assert result is None


class TestFieldExtractors:
    """Tests for field extractor functions."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.config = FrontmatterConfig()

    def test_get_source_url(self) -> None:
        """Test extracting source URL."""
        data = {"source": "https://example.com/article"}
        result = get_source_url(data, self.config)
        assert result == "https://example.com/article"

    def test_get_source_url_none(self) -> None:
        """Test source URL when not present."""
        data = {}
        result = get_source_url(data, self.config)
        assert result is None

    def test_get_title(self) -> None:
        """Test extracting title."""
        data = {"title": "My Article"}
        result = get_title(data, self.config)
        assert result == "My Article"

    def test_get_published_date_string(self) -> None:
        """Test extracting published date as string."""
        data = {"published": "2024-01-15"}
        result = get_published_date(data, self.config)
        assert result == "2024-01-15"

    def test_get_published_date_object(self) -> None:
        """Test extracting published date from date object."""
        from datetime import date

        data = {"published": date(2024, 1, 15)}
        result = get_published_date(data, self.config)
        assert result == "2024-01-15"

    def test_get_author(self) -> None:
        """Test extracting author."""
        data = {"author": "Jane Doe"}
        result = get_author(data, self.config)
        assert result == "Jane Doe"

    def test_get_description(self) -> None:
        """Test extracting description."""
        data = {"description": "A short summary"}
        result = get_description(data, self.config)
        assert result == "A short summary"


class TestFixWikilinks:
    """Tests for fix_wikilinks function."""

    def test_fix_wikilinks_in_author_field(self) -> None:
        """Test stripping simple wikilink from a field value."""
        text = "author: [[John Doe]]"
        fixed, fixes = fix_wikilinks(text)
        assert fixed == "author: John Doe"
        assert len(fixes) == 1
        assert fixes[0].fix_type == "wikilink"

    def test_fix_wikilinks_with_alias(self) -> None:
        """Test that alias takes precedence in [[Page|Alias]] syntax."""
        text = "author: [[John Doe Page|John Doe]]"
        fixed, fixes = fix_wikilinks(text)
        assert fixed == "author: John Doe"
        assert len(fixes) == 1

    def test_fix_wikilinks_in_yaml_list(self) -> None:
        """Test stripping wikilinks from YAML list items."""
        text = "tags:\n  - [[Python]]\n  - [[Programming]]"
        fixed, fixes = fix_wikilinks(text)
        assert fixed == "tags:\n  - Python\n  - Programming"
        assert len(fixes) == 2

    def test_no_wikilinks_unchanged(self) -> None:
        """Test that content without wikilinks is unchanged."""
        text = "author: John Doe\ntitle: Some Title"
        fixed, fixes = fix_wikilinks(text)
        assert fixed == text
        assert len(fixes) == 0

    def test_fix_wikilinks_recorded_in_result(self) -> None:
        """Test that fix_frontmatter records wikilink fixes in FixResult."""
        text = 'author: [[Jane Smith]]\ntitle: "An Article"'
        result = fix_frontmatter(text)
        assert result.is_valid is True
        wikilink_fixes = [f for f in result.fixes if f.fix_type == "wikilink"]
        assert len(wikilink_fixes) == 1


class TestFixUnclosedQuotes:
    """Tests for fix_unclosed_quotes function."""

    def test_fix_unclosed_quote_in_url_field(self) -> None:
        """Test closing unclosed quote in a URL field."""
        text = 'source: "https://example.com'
        fixed, fixes = fix_unclosed_quotes(text)
        assert fixed == 'source: "https://example.com"'
        assert len(fixes) == 1
        assert fixes[0].fix_type == "unclosed_quote"

    def test_fix_unclosed_quote_in_list_item(self) -> None:
        """Test closing unclosed quote in a list item."""
        text = '  - "John Doe'
        fixed, fixes = fix_unclosed_quotes(text)
        assert fixed == '  - "John Doe"'
        assert len(fixes) == 1

    def test_properly_quoted_value_unchanged(self) -> None:
        """Test that a properly closed quote is not modified."""
        text = 'source: "https://example.com"'
        fixed, fixes = fix_unclosed_quotes(text)
        assert fixed == text
        assert len(fixes) == 0

    def test_unclosed_quote_with_inline_comment(self) -> None:
        """Test that inline comment is preserved after fix."""
        text = 'source: "https://example.com #comment'
        fixed, fixes = fix_unclosed_quotes(text)
        assert fixed == 'source: "https://example.com" #comment'
        assert len(fixes) == 1

    def test_fix_unclosed_quote_recorded_in_result(self) -> None:
        """Test that fix_frontmatter records unclosed_quote fixes in FixResult."""
        text = 'source: "https://example.com\ntitle: "My Article"'
        result = fix_frontmatter(text)
        quote_fixes = [f for f in result.fixes if f.fix_type == "unclosed_quote"]
        assert len(quote_fixes) == 1


class TestFixMultilineWikilinks:
    """Tests for fix_multiline_wikilinks function."""

    def test_fixes_multiline_wikilink(self) -> None:
        """Test fixing a multi-line wikilink."""
        text = 'title: "Article with [[Broken\nWikilink]]"'
        fixed, fixes = fix_multiline_wikilinks(text)
        assert "[[Broken Wikilink]]" in fixed
        assert len(fixes) == 1
        assert fixes[0].fix_type == "multiline_wikilink"

    def test_no_wikilinks(self) -> None:
        """Test text without wikilinks."""
        text = "title: Normal Title"
        fixed, fixes = fix_multiline_wikilinks(text)
        assert fixed == text
        assert len(fixes) == 0

    def test_valid_wikilink(self) -> None:
        """Test valid single-line wikilink is not changed."""
        text = 'title: "[[Valid Link]]"'
        fixed, fixes = fix_multiline_wikilinks(text)
        assert fixed == text
        assert len(fixes) == 0


class TestFixUnquotedColons:
    """Tests for fix_unquoted_colons function."""

    def test_fixes_unquoted_colon(self) -> None:
        """Test fixing unquoted value with colon."""
        text = "title: Chapter 1: Introduction"
        fixed, fixes = fix_unquoted_colons(text)
        assert fixed == 'title: "Chapter 1: Introduction"'
        assert len(fixes) == 1

    def test_already_quoted(self) -> None:
        """Test already quoted value is not changed."""
        text = 'title: "Chapter 1: Introduction"'
        fixed, fixes = fix_unquoted_colons(text)
        assert fixed == text
        assert len(fixes) == 0

    def test_no_colon_in_value(self) -> None:
        """Test value without colon is not changed."""
        text = "title: Simple Title"
        fixed, fixes = fix_unquoted_colons(text)
        assert fixed == text
        assert len(fixes) == 0


class TestFixFrontmatter:
    """Tests for fix_frontmatter function."""

    def test_fix_multiple_issues(self) -> None:
        """Test fixing multiple issues."""
        text = """title: "[[Multi
line]] and colons: here"
author: Some Author"""
        result = fix_frontmatter(text)
        assert result.is_valid is True
        assert len(result.fixes) >= 1

    def test_valid_frontmatter(self) -> None:
        """Test valid frontmatter returns empty fixes."""
        text = """title: "Valid Title"
author: "Valid Author"
"""
        result = fix_frontmatter(text)
        assert result.is_valid is True
        assert len(result.fixes) == 0


class TestSerializeFrontmatter:
    """Tests for serialize_frontmatter function."""

    def test_serialize_simple(self) -> None:
        """Test serializing simple data."""
        data = {"title": "Test", "author": "Jane"}
        result = serialize_frontmatter(data)
        assert result.startswith("---\n")
        assert result.endswith("---\n")
        assert "title: Test" in result

    def test_serialize_empty(self) -> None:
        """Test serializing empty data."""
        result = serialize_frontmatter({})
        assert result == ""
