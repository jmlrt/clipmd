"""Unit tests for date parsing and extraction."""

from __future__ import annotations

from datetime import date

from clipmd.config import DatesConfig
from clipmd.core.dates import (
    add_date_prefix,
    extract_date_from_content,
    extract_date_from_filename,
    format_date,
    get_date_for_prefix,
    has_date_prefix,
    parse_date_string,
)


class TestParseDateString:
    """Tests for parse_date_string function."""

    def test_iso_format(self) -> None:
        """Test parsing ISO date format."""
        result = parse_date_string("2024-01-15")
        assert result == date(2024, 1, 15)

    def test_us_format(self) -> None:
        """Test parsing US date format."""
        result = parse_date_string("January 15, 2024")
        assert result == date(2024, 1, 15)

    def test_european_format(self) -> None:
        """Test parsing European date format."""
        result = parse_date_string("15 January 2024")
        assert result == date(2024, 1, 15)

    def test_with_explicit_formats(self) -> None:
        """Test parsing with explicit format list."""
        result = parse_date_string("15/01/2024", ["%d/%m/%Y"])
        assert result == date(2024, 1, 15)

    def test_empty_string(self) -> None:
        """Test parsing empty string."""
        result = parse_date_string("")
        assert result is None

    def test_invalid_date(self) -> None:
        """Test parsing invalid date string."""
        result = parse_date_string("not a date")
        assert result is None

    def test_datetime_format(self) -> None:
        """Test parsing datetime string."""
        result = parse_date_string("2024-01-15T10:30:00")
        assert result == date(2024, 1, 15)


class TestFormatDate:
    """Tests for format_date function."""

    def test_default_format(self) -> None:
        """Test default YYYYMMDD format."""
        d = date(2024, 1, 15)
        result = format_date(d)
        assert result == "20240115"

    def test_custom_format(self) -> None:
        """Test custom format."""
        d = date(2024, 1, 15)
        result = format_date(d, "%Y-%m-%d")
        assert result == "2024-01-15"


class TestExtractDateFromContent:
    """Tests for extract_date_from_content function."""

    def test_ordinal_date(self) -> None:
        """Test extracting date with ordinal suffix."""
        content = "Published on 15th January 2024"
        result = extract_date_from_content(content)
        assert result.date == date(2024, 1, 15)
        assert result.source == "content"

    def test_us_format_in_content(self) -> None:
        """Test extracting US format date from content."""
        content = "This was written on January 15, 2024 by John."
        result = extract_date_from_content(content)
        assert result.date == date(2024, 1, 15)

    def test_iso_date_in_content(self) -> None:
        """Test extracting ISO date from content."""
        content = "Date: 2024-01-15"
        result = extract_date_from_content(content)
        assert result.date == date(2024, 1, 15)

    def test_no_date_in_content(self) -> None:
        """Test content without date."""
        content = "This article has no date."
        result = extract_date_from_content(content)
        assert result.date is None
        assert result.source == "none"

    def test_custom_patterns(self) -> None:
        """Test with custom patterns."""
        content = "Date: 15.01.2024"
        patterns = [r"(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{4})"]
        result = extract_date_from_content(content, patterns)
        assert result.date == date(2024, 1, 15)

    def test_invalid_date_values(self) -> None:
        """Test content with invalid date values."""
        content = "Published on 35th January 2024"  # Invalid day
        result = extract_date_from_content(content)
        assert result.date is None


class TestExtractDateFromFilename:
    """Tests for extract_date_from_filename function."""

    def test_valid_prefix(self) -> None:
        """Test extracting date from valid prefix."""
        result = extract_date_from_filename("20240115-Article-Title.md")
        assert result.date == date(2024, 1, 15)
        assert result.source == "filename"

    def test_no_prefix(self) -> None:
        """Test filename without date prefix."""
        result = extract_date_from_filename("Article-Title.md")
        assert result.date is None
        assert result.source == "none"

    def test_invalid_prefix(self) -> None:
        """Test filename with invalid date prefix."""
        result = extract_date_from_filename("20241332-Invalid.md")  # Invalid month
        assert result.date is None


class TestHasDatePrefix:
    """Tests for has_date_prefix function."""

    def test_with_prefix(self) -> None:
        """Test filename with valid prefix."""
        assert has_date_prefix("20240115-Article.md") is True

    def test_without_prefix(self) -> None:
        """Test filename without prefix."""
        assert has_date_prefix("Article.md") is False

    def test_partial_prefix(self) -> None:
        """Test filename with partial prefix."""
        assert has_date_prefix("2024-Article.md") is False


class TestAddDatePrefix:
    """Tests for add_date_prefix function."""

    def test_add_to_plain_filename(self) -> None:
        """Test adding prefix to plain filename."""
        result = add_date_prefix("Article-Title.md", date(2024, 1, 15))
        assert result == "20240115-Article-Title.md"

    def test_replace_existing_prefix(self) -> None:
        """Test replacing existing prefix."""
        result = add_date_prefix("20230101-Article.md", date(2024, 1, 15))
        assert result == "20240115-Article.md"

    def test_custom_format(self) -> None:
        """Test with custom format."""
        result = add_date_prefix("Article.md", date(2024, 1, 15), "%Y-%m-%d")
        assert result == "2024-01-15-Article.md"


class TestGetDateForPrefix:
    """Tests for get_date_for_prefix function."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.config = DatesConfig()

    def test_from_frontmatter_published(self) -> None:
        """Test getting date from published field."""
        frontmatter = {"published": "2024-01-15"}
        result = get_date_for_prefix(frontmatter, "", "file.md", self.config)
        assert result.date == date(2024, 1, 15)
        assert result.source == "frontmatter"

    def test_from_frontmatter_clipped(self) -> None:
        """Test getting date from clipped field when published missing."""
        frontmatter = {"clipped": "2024-01-16"}
        result = get_date_for_prefix(frontmatter, "", "file.md", self.config)
        assert result.date == date(2024, 1, 16)
        assert result.source == "frontmatter"

    def test_from_content(self) -> None:
        """Test getting date from content."""
        frontmatter: dict[str, object] = {}
        content = "Posted on January 15, 2024"
        result = get_date_for_prefix(frontmatter, content, "file.md", self.config)
        assert result.date == date(2024, 1, 15)
        assert result.source == "content"

    def test_from_filename(self) -> None:
        """Test getting date from filename."""
        frontmatter: dict[str, object] = {}
        config = DatesConfig(extract_from_content=False)
        result = get_date_for_prefix(frontmatter, "", "20240115-Article.md", config)
        assert result.date == date(2024, 1, 15)
        assert result.source == "filename"

    def test_no_date_found(self) -> None:
        """Test when no date can be found."""
        frontmatter: dict[str, object] = {}
        config = DatesConfig(extract_from_content=False)
        result = get_date_for_prefix(frontmatter, "", "Article.md", config)
        assert result.date is None
        assert result.source == "none"
