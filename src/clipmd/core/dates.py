"""Date parsing and extraction for clipmd."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING

from dateutil import parser as dateutil_parser

if TYPE_CHECKING:
    from clipmd.config import DatesConfig

# Month name to number mapping
MONTH_NAMES = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


@dataclass
class DateExtractionResult:
    """Result of extracting a date from content."""

    date: date | None
    source: str  # "frontmatter", "content", "filename", "none"
    original_value: str | None = None
    pattern_matched: str | None = None


def parse_date_string(
    date_str: str,
    input_formats: list[str] | None = None,
) -> date | None:
    """Parse a date string using multiple formats.

    Args:
        date_str: The date string to parse.
        input_formats: List of strptime formats to try.

    Returns:
        Parsed date or None if parsing fails.
    """
    if not date_str:
        return None

    date_str = str(date_str).strip()

    # Try explicit formats first
    if input_formats:
        for fmt in input_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.date()
            except ValueError:
                continue

    # Fall back to dateutil parser
    try:
        dt = dateutil_parser.parse(date_str, fuzzy=False)
        return dt.date()
    except (ValueError, TypeError):
        pass

    return None


def format_date(d: date, output_format: str = "%Y%m%d") -> str:
    """Format a date for output.

    Args:
        d: The date to format.
        output_format: strftime format string.

    Returns:
        Formatted date string.
    """
    return d.strftime(output_format)


def extract_date_from_content(
    content: str,
    patterns: list[str] | None = None,
) -> DateExtractionResult:
    """Extract a date from article content using regex patterns.

    Args:
        content: The article content to search.
        patterns: List of regex patterns with named groups (day, month, year).

    Returns:
        DateExtractionResult with extracted date or None.
    """
    if not patterns:
        # Default patterns
        patterns = [
            r"(?P<day>\d{1,2})(?:st|nd|rd|th)?\s+(?P<month>\w+)\s+(?P<year>\d{4})",
            r"(?P<month>\w+)\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?,?\s+(?P<year>\d{4})",
            r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})",
        ]

    for pattern in patterns:
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            match = regex.search(content)
            if match:
                groups = match.groupdict()
                year = int(groups["year"])
                day = int(groups["day"])

                # Handle month - could be name or number
                month_str = groups["month"].lower()
                if month_str.isdigit():
                    month = int(month_str)
                else:
                    month = MONTH_NAMES.get(month_str)
                    if month is None:
                        continue

                # Validate date
                try:
                    extracted_date = date(year, month, day)
                    return DateExtractionResult(
                        date=extracted_date,
                        source="content",
                        original_value=match.group(0),
                        pattern_matched=pattern,
                    )
                except ValueError:
                    # Invalid date (e.g., Feb 30)
                    continue

        except re.error:
            # Invalid regex pattern
            continue

    return DateExtractionResult(
        date=None,
        source="none",
    )


def extract_date_from_filename(filename: str) -> DateExtractionResult:
    """Extract date prefix from filename.

    Expected format: YYYYMMDD-title.md or YYYYMMDD-title.md

    Args:
        filename: The filename to parse.

    Returns:
        DateExtractionResult with extracted date or None.
    """
    # Match YYYYMMDD at start of filename
    match = re.match(r"^(\d{8})-", filename)
    if match:
        date_str = match.group(1)
        try:
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            extracted_date = date(year, month, day)
            return DateExtractionResult(
                date=extracted_date,
                source="filename",
                original_value=date_str,
            )
        except ValueError:
            pass

    return DateExtractionResult(
        date=None,
        source="none",
    )


def get_date_for_prefix(
    frontmatter_data: dict[str, object],
    content: str,
    filename: str,
    config: DatesConfig,
) -> DateExtractionResult:
    """Get the date to use for filename prefix.

    Tries sources in priority order:
    1. Frontmatter fields (in priority order from config)
    2. Content extraction (if enabled)
    3. Existing filename prefix

    Args:
        frontmatter_data: Parsed frontmatter dictionary.
        content: Article content.
        filename: Current filename.
        config: Dates configuration.

    Returns:
        DateExtractionResult with the best date found.
    """
    # Try frontmatter fields in priority order
    for field_name in config.prefix_priority:
        value = frontmatter_data.get(field_name)
        if value:
            parsed = parse_date_string(str(value), config.input_formats)
            if parsed:
                return DateExtractionResult(
                    date=parsed,
                    source="frontmatter",
                    original_value=str(value),
                )

    # Try content extraction if enabled
    if config.extract_from_content:
        result = extract_date_from_content(content, config.content_patterns)
        if result.date:
            return result

    # Try existing filename
    result = extract_date_from_filename(filename)
    if result.date:
        return result

    return DateExtractionResult(
        date=None,
        source="none",
    )


def has_date_prefix(filename: str) -> bool:
    """Check if filename has a YYYYMMDD- date prefix.

    Args:
        filename: The filename to check.

    Returns:
        True if filename starts with YYYYMMDD- pattern.
    """
    return bool(re.match(r"^\d{8}-", filename))


def add_date_prefix(filename: str, d: date, output_format: str = "%Y%m%d") -> str:
    """Add date prefix to filename.

    Args:
        filename: The original filename.
        d: The date to use as prefix.
        output_format: strftime format for the prefix.

    Returns:
        Filename with date prefix.
    """
    # Remove existing date prefix if present
    if has_date_prefix(filename):
        filename = filename[9:]  # Remove YYYYMMDD-

    date_str = format_date(d, output_format)
    return f"{date_str}-{filename}"
