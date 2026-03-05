"""Frontmatter parsing and manipulation for markdown files."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import frontmatter as fm
import yaml

from clipmd.config import FrontmatterConfig
from clipmd.exceptions import ParseError

# Regex to match YAML frontmatter delimiters
# Matches: ---\n ... \n--- (closing delimiter on its own line; newline optional for empty frontmatter)
FRONTMATTER_PATTERN = re.compile(
    r"^---\s*\n(.*?)(?:\n)?---\s*(?:\n|$)",
    re.DOTALL | re.MULTILINE,
)

# Regex to find multi-line wikilinks like [[link\ntext]]
MULTILINE_WIKILINK_PATTERN = re.compile(r"\[\[([^\]]*?)\n([^\]]*?)\]\]")


@dataclass
class FrontmatterResult:
    """Result of parsing frontmatter from a markdown file."""

    data: dict[str, Any]
    content: str
    raw_frontmatter: str
    has_frontmatter: bool = True


@dataclass
class FrontmatterFix:
    """Description of a fix applied to frontmatter."""

    fix_type: str
    description: str
    field: str | None = None


@dataclass
class FixResult:
    """Result of fixing frontmatter."""

    fixed_frontmatter: str
    fixes: list[FrontmatterFix] = field(default_factory=list)
    is_valid: bool = True
    error: str | None = None


def parse_frontmatter(text: str) -> FrontmatterResult:
    """Parse YAML frontmatter from markdown text.

    Args:
        text: The full markdown text including frontmatter.

    Returns:
        FrontmatterResult with parsed data and remaining content.

    Raises:
        ParseError: If frontmatter is present but invalid YAML.
    """
    if not text.startswith("---"):
        return FrontmatterResult(
            data={},
            content=text,
            raw_frontmatter="",
            has_frontmatter=False,
        )

    try:
        post = fm.loads(text)

        # Extract raw frontmatter (needed by fix_frontmatter)
        # The library doesn't expose this, so extract manually
        raw_frontmatter = ""
        if text.startswith("---\n"):
            end_match = re.search(r"\n---\s*(?:\n|$)", text[4:])
            if end_match:
                raw_frontmatter = text[4 : 4 + end_match.start()]

        metadata = post.metadata if post.metadata else {}
        if not isinstance(metadata, dict):
            raise ParseError(
                f"Invalid frontmatter YAML: top-level content must be a mapping "
                f"(got {type(metadata).__name__})"
            )

        return FrontmatterResult(
            data=metadata,
            content=post.content,
            raw_frontmatter=raw_frontmatter,
            has_frontmatter=True,
        )
    except yaml.YAMLError as e:
        raise ParseError(f"Invalid frontmatter YAML: {e}") from e
    except Exception as e:
        raise ParseError(f"Invalid frontmatter: {e}") from e


def extract_field(
    data: dict[str, Any],
    field_names: list[str],
    default: Any = None,
) -> Any:
    """Extract a field from frontmatter using multiple possible names.

    Args:
        data: The frontmatter dictionary.
        field_names: List of possible field names to try in order.
        default: Default value if no field is found.

    Returns:
        The field value or default.
    """
    for name in field_names:
        if name in data:
            return data[name]
    return default


def get_source_url(data: dict[str, Any], config: FrontmatterConfig) -> str | None:
    """Extract source URL from frontmatter.

    Args:
        data: The frontmatter dictionary.
        config: Frontmatter configuration with field mappings.

    Returns:
        The source URL or None.
    """
    value = extract_field(data, config.source_url)
    return str(value) if value is not None else None


def get_title(data: dict[str, Any], config: FrontmatterConfig) -> str | None:
    """Extract title from frontmatter.

    Args:
        data: The frontmatter dictionary.
        config: Frontmatter configuration with field mappings.

    Returns:
        The title or None.
    """
    value = extract_field(data, config.title)
    return str(value) if value is not None else None


def get_published_date(data: dict[str, Any], config: FrontmatterConfig) -> str | None:
    """Extract published date from frontmatter.

    Args:
        data: The frontmatter dictionary.
        config: Frontmatter configuration with field mappings.

    Returns:
        The published date as string or None.
    """
    value = extract_field(data, config.published_date)
    if value is None:
        return None
    # Handle datetime objects
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def get_author(data: dict[str, Any], config: FrontmatterConfig) -> str | None:
    """Extract author from frontmatter.

    Args:
        data: The frontmatter dictionary.
        config: Frontmatter configuration with field mappings.

    Returns:
        The author or None.
    """
    value = extract_field(data, config.author)
    return str(value) if value is not None else None


def get_description(data: dict[str, Any], config: FrontmatterConfig) -> str | None:
    """Extract description from frontmatter.

    Args:
        data: The frontmatter dictionary.
        config: Frontmatter configuration with field mappings.

    Returns:
        The description or None.
    """
    value = extract_field(data, config.description)
    return str(value) if value is not None else None


def fix_wikilinks(text: str) -> tuple[str, list[FrontmatterFix]]:
    """Strip wikilink syntax from frontmatter field values.

    Converts [[Name]] to Name and [[Page|Alias]] to Alias.

    Args:
        text: The raw frontmatter text.

    Returns:
        Tuple of (fixed text, list of fixes applied).
    """
    fixes: list[FrontmatterFix] = []
    wikilink_re = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")

    def replacer(match: re.Match[str]) -> str:
        page_name = match.group(1).strip()
        alias = match.group(2)
        replacement = alias.strip() if alias else page_name
        fixes.append(
            FrontmatterFix(
                fix_type="wikilink",
                description=f"Stripped wikilink syntax: {match.group(0)} → {replacement}",
            )
        )
        return replacement

    fixed = wikilink_re.sub(replacer, text)
    return fixed, fixes


def fix_multiline_wikilinks(text: str) -> tuple[str, list[FrontmatterFix]]:
    """Fix multi-line wikilinks in frontmatter text.

    Converts [[link\ntext]] to [[link text]].

    Args:
        text: The raw frontmatter text.

    Returns:
        Tuple of (fixed text, list of fixes applied).
    """
    fixes: list[FrontmatterFix] = []

    def replacer(match: re.Match[str]) -> str:
        # Replace newline with space
        link_text = match.group(1) + " " + match.group(2)
        # Remove extra whitespace
        link_text = " ".join(link_text.split())
        fixes.append(
            FrontmatterFix(
                fix_type="multiline_wikilink",
                description=f"Fixed multi-line wikilink: [[{link_text}]]",
            )
        )
        return f"[[{link_text}]]"

    fixed = MULTILINE_WIKILINK_PATTERN.sub(replacer, text)
    return fixed, fixes


def fix_unclosed_quotes(text: str) -> tuple[str, list[FrontmatterFix]]:
    """Fix unclosed quote strings in YAML frontmatter fields.

    Handles lines like:
        source: "https://example.com   (missing closing quote)
        - "John Doe                    (list item with unclosed quote)

    Args:
        text: The raw frontmatter text.

    Returns:
        Tuple of (fixed text, list of fixes applied).
    """
    fixes: list[FrontmatterFix] = []
    lines = text.split("\n")
    fixed_lines = []

    for line in lines:
        stripped = line.rstrip()
        # Match YAML key-value lines or list items where value starts with "
        # Patterns: "  key: "value" or "  - "value"
        key_value_re = re.compile(r'^(\s*\S+:\s+)(")(.*)')
        list_item_re = re.compile(r'^(\s*-\s+)(")(.*)')

        match = key_value_re.match(stripped) or list_item_re.match(stripped)
        if match:
            prefix = match.group(1)
            value_body = match.group(3)
            # Unclosed if value doesn't end with an unescaped "
            if not value_body.endswith('"'):
                # Strip inline comment if present: split at first ' #'
                comment = ""
                actual_body = value_body
                if " #" in value_body:
                    parts = value_body.split(" #", 1)
                    actual_body = parts[0]
                    comment = " #" + parts[1]
                fixed_lines.append(f'{prefix}"{actual_body}"{comment}')
                fixes.append(
                    FrontmatterFix(
                        fix_type="unclosed_quote",
                        description=f"Closed unclosed quote in: {stripped!r}",
                    )
                )
                continue

        fixed_lines.append(line)

    return "\n".join(fixed_lines), fixes


def fix_unquoted_colons(text: str) -> tuple[str, list[FrontmatterFix]]:
    """Fix unquoted values containing colons.

    Args:
        text: The raw frontmatter text.

    Returns:
        Tuple of (fixed text, list of fixes applied).
    """
    fixes: list[FrontmatterFix] = []
    lines = text.split("\n")
    fixed_lines = []

    for line in lines:
        if ":" in line:
            # Split on first colon only
            parts = line.split(":", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                # Check if value contains colon and isn't already quoted
                if ":" in value and not (
                    (value.startswith('"') and value.endswith('"'))
                    or (value.startswith("'") and value.endswith("'"))
                ):
                    # Split value and comment (# followed by space indicates comment)
                    # Simple heuristic: find " #" that's not inside quotes
                    comment = ""
                    actual_value = value
                    if " #" in value:
                        # Split at first " #" - this is a simple approach
                        # A more robust solution would parse quotes, but this handles common cases
                        parts = value.split(" #", 1)
                        actual_value = parts[0]
                        comment = " #" + parts[1]

                    # Quote only the actual value part
                    escaped_value = actual_value.replace('"', '\\"')
                    fixed_lines.append(f'{key}: "{escaped_value}"{comment}')
                    fixes.append(
                        FrontmatterFix(
                            fix_type="unquoted_colon",
                            description=f"Quoted value with colon in field: {key}",
                            field=key,
                        )
                    )
                    continue
        fixed_lines.append(line)

    return "\n".join(fixed_lines), fixes


def fix_frontmatter(raw_frontmatter: str) -> FixResult:
    """Apply all frontmatter fixes.

    Args:
        raw_frontmatter: The raw frontmatter text (without --- delimiters).

    Returns:
        FixResult with fixed frontmatter and list of fixes applied.
    """
    all_fixes: list[FrontmatterFix] = []

    # Apply fixes in order
    text = raw_frontmatter

    # Fix multi-line wikilinks (must run before fix_wikilinks so single-line
    # regex can match the normalized result)
    text, fixes = fix_multiline_wikilinks(text)
    all_fixes.extend(fixes)

    # Strip wikilink syntax from field values
    text, fixes = fix_wikilinks(text)
    all_fixes.extend(fixes)

    # Fix unclosed quote strings
    text, fixes = fix_unclosed_quotes(text)
    all_fixes.extend(fixes)

    # Fix unquoted colons
    text, fixes = fix_unquoted_colons(text)
    all_fixes.extend(fixes)

    # Validate the result
    try:
        yaml.safe_load(text)
        return FixResult(
            fixed_frontmatter=text,
            fixes=all_fixes,
            is_valid=True,
        )
    except yaml.YAMLError as e:
        return FixResult(
            fixed_frontmatter=text,
            fixes=all_fixes,
            is_valid=False,
            error=str(e),
        )


def serialize_frontmatter(data: dict[str, Any]) -> str:
    """Serialize a dictionary to YAML frontmatter format.

    Args:
        data: Dictionary to serialize.

    Returns:
        YAML frontmatter string with --- delimiters.
    """
    if not data:
        return ""

    # Create a Post object with empty content and metadata
    post = fm.Post(content="", **data)
    result = fm.dumps(post)

    # Format: "---\nYAML\n---\n" (strip extra content newlines)
    return result.rstrip() + "\n"


def build_frontmatter(
    url: str,
    title: str | None,
    author: str | None,
    published: str | None,
    description: str | None,
    clipped: str | None = None,
) -> str:
    """Build YAML frontmatter.

    Args:
        url: Source URL.
        title: Article title.
        author: Author name.
        published: Published date.
        description: Article description.
        clipped: Clipped date.

    Returns:
        YAML frontmatter string.
    """
    if clipped is None:
        clipped = datetime.now().strftime("%Y-%m-%d")

    frontmatter_data = {
        "title": title or "Untitled",
        "source": url,
        "clipped": clipped,
    }

    if author:
        frontmatter_data["author"] = author

    if published:
        frontmatter_data["published"] = published

    if description:
        # Truncate long descriptions
        desc = description[:300] if len(description) > 300 else description
        # Normalize multiline descriptions to single line
        frontmatter_data["description"] = desc.replace("\n", " ")

    yaml_content = yaml.dump(frontmatter_data, default_flow_style=False, sort_keys=False)
    return f"---\n{yaml_content}---"
