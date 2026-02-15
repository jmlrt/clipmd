# clipmd - Clip, Organize, and Manage Markdown Articles

A CLI tool for saving, organizing, and managing markdown articles with YAML frontmatter. Designed to assist LLM-based workflows by preprocessing files and executing file operations reliably.

## Overview

**clipmd** is a helper tool that:
- **Fetches web content** and converts to markdown with frontmatter
- **Prepares data** for LLM consumption (compact metadata extraction)
- **Executes decisions** made by LLMs or humans (file moving, cleanup)
- **Handles tedious operations** (deduplication, URL cleaning, caching)

It does NOT call LLMs directly. Instead, it produces LLM-optimized output and accepts simple input formats that LLMs can easily generate.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestrator (LLM or Human)                  │
│            Claude Code / Cursor / Aider / Manual                │
├─────────────────────────────────────────────────────────────────┤
│  - Reads clipmd output (metadata, reports, statistics)           │
│  - Makes decisions (categorization, what to keep/remove)        │
│  - Calls clipmd commands to execute decisions                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         clipmd (Executor)                        │
├─────────────────────────────────────────────────────────────────┤
│  Capture:          fetch                                        │
│  Data Extraction:  extract, stats, duplicates                   │
│  Preprocessing:    preprocess                                   │
│  Execution:        move, trash                                  │
│                                                                 │
│  ✓ LLM-optimized output (minimal tokens)                        │
│  ✓ Simple input formats (easy for LLM to generate)              │
│  ✓ Reliable file operations (no edge cases)                     │
│  ✗ No AI/LLM calls (orchestrator handles that)                  │
└─────────────────────────────────────────────────────────────────┘
```

## Design Principles

### 1. Minimize tokens for LLM consumption

Instead of LLM reading 100 files (~200k tokens), generate one compact metadata file (~5k tokens):

```bash
clipmd extract --max-chars 150
# Output: articles-metadata.txt with title, URL, description for each file
```

### 2. Simple input formats LLMs can generate

```
# LLM outputs a simple numbered list:
1. Tech-Tools - 20240115-Some-Article.md
2. Science - 20240116-Another-Article.md
3. TRASH - duplicate-file.md
```

```bash
clipmd move categorization.txt
# Tool handles: folder creation, file moving, cache updates, trash
```

### 3. Atomic, predictable commands

Every command should "just work" without the orchestrator handling edge cases:
- Creates folders if needed
- Uses system trash (recoverable)
- Updates cache automatically
- Validates before executing

### 4. Configuration over convention

All opinionated choices (folder names, field mappings, patterns) live in config:

```bash
clipmd init  # Creates config.yaml with sensible defaults
# User customizes for their setup
```

## Installation

```bash
pip install clipmd
# or
uv add clipmd

# With language detection support (for --include-stats)
pip install clipmd[lang]
# or
uv add clipmd[lang]
```

### Shell Completions

Enable tab completion for your shell:

```bash
# Bash (add to ~/.bashrc)
eval "$(_CLIPMD_COMPLETE=bash_source clipmd)"

# Zsh (add to ~/.zshrc)
eval "$(_CLIPMD_COMPLETE=zsh_source clipmd)"

# Fish (add to ~/.config/fish/completions/clipmd.fish)
_CLIPMD_COMPLETE=fish_source clipmd | source
```

Or generate completion scripts:

```bash
_CLIPMD_COMPLETE=bash_source clipmd > ~/.local/share/bash-completion/completions/clipmd
_CLIPMD_COMPLETE=zsh_source clipmd > ~/.zfunc/_clipmd
_CLIPMD_COMPLETE=fish_source clipmd > ~/.config/fish/completions/clipmd.fish
```

## Quick Start

```bash
# Initialize in your articles directory
cd ~/Documents/Articles
clipmd init

# Edit config.yaml for your setup

# Option A: Fetch articles from URLs
clipmd fetch "https://example.com/article"
clipmd fetch -f urls.txt  # Or from a file

# Option B: Already have markdown files? Skip to preprocessing.

# Preprocess files (clean URLs, sanitize filenames)
clipmd preprocess

# Extract metadata for LLM categorization
clipmd extract > articles-metadata.txt

# [LLM or human creates categorization.txt]

# Execute the categorization
clipmd move categorization.txt

# View statistics
clipmd stats
```

## Configuration

### Config File Location

clipmd searches for configuration in this order (first found wins):

1. `--config PATH` (command line override)
2. `./config.yaml` (current directory)
3. `./.clipmd/config.yaml` (project directory)
4. `$XDG_CONFIG_HOME/clipmd/config.yaml` (typically `~/.config/clipmd/config.yaml`)

For project-specific config, use options 2 or 3. For user-wide defaults, use option 4.

### Minimal Config

```yaml
# config.yaml - minimal setup
version: 1
paths:
  root: "."  # Articles directory
```

### Full Config

```yaml
# config.yaml - full configuration
version: 1

# =============================================================================
# PATHS
# =============================================================================
paths:
  root: "."                          # Root articles directory
  cache: ".clipmd/cache.json"         # URL/content cache

# Special folders (set to null to disable)
special_folders:
  # Folders to exclude from statistics and reorganization
  exclude_patterns:
    - "0-*"        # Folders starting with "0-"
    - ".*"         # Hidden folders
    - "_*"         # Folders starting with "_"

# =============================================================================
# FRONTMATTER FIELD MAPPING
# =============================================================================
# Map semantic fields to actual field names in your files
# Tool will try each name in order until one is found
frontmatter:
  source_url:
    - source
    - url
    - link
    - original_url
    - clip_url

  title:
    - title
    - name

  published_date:
    - published
    - date
    - publish_date

  clipped_date:
    - clipped
    - saved
    - created
    - added

  author:
    - author
    - by
    - writer
    - creator

  description:
    - description
    - summary
    - excerpt
    - abstract

# =============================================================================
# DATE HANDLING
# =============================================================================
dates:
  # Date formats to try when parsing (in order)
  input_formats:
    - "%Y-%m-%d"           # 2024-01-17
    - "%Y-%m-%dT%H:%M:%S"  # 2024-01-17T14:30:00
    - "%d/%m/%Y"           # 17/01/2024
    - "%B %d, %Y"          # January 17, 2024
    - "%d %B %Y"           # 17 January 2024
    - "%Y/%m/%d"           # 2024/01/17

  # Output format for date prefixes
  output_format: "%Y%m%d"  # 20240117

  # Field priority for date prefix (first found is used)
  prefix_priority:
    - published
    - clipped
    - created

  # Extract dates from article body when frontmatter fields are empty
  # Searches for patterns like "9th January 2026", "July 9, 2024", etc.
  extract_from_content: true

  # Patterns for extracting dates from content (regex with named groups)
  # Processed in order, first match wins
  content_patterns:
    - "(?P<day>\\d{1,2})(?:st|nd|rd|th)?\\s+(?P<month>\\w+)\\s+(?P<year>\\d{4})"  # 9th January 2026
    - "(?P<month>\\w+)\\s+(?P<day>\\d{1,2})(?:st|nd|rd|th)?,?\\s+(?P<year>\\d{4})"  # January 9, 2024
    - "(?P<year>\\d{4})-(?P<month>\\d{2})-(?P<day>\\d{2})"  # 2024-01-17

# =============================================================================
# URL CLEANING
# =============================================================================
url_cleaning:
  # Tracking parameters to remove
  remove_params:
    - utm_source
    - utm_medium
    - utm_campaign
    - utm_content
    - utm_term
    - fbclid
    - gclid
    - ref
    - source

  # URL patterns to unwrap (e.g., redirect wrappers)
  unwrap_patterns:
    - pattern: "^https?://.*?[?&]url=(.+)$"
      extract: 1
    - pattern: "^https?://.*?[?&]u=(.+)$"
      extract: 1

# =============================================================================
# FILENAME SANITIZATION
# =============================================================================
filenames:
  # Character replacements
  replacements:
    " ": "-"
    "_": "-"
    "'": ""
    '"': ""
    ":": "-"
    "/": "-"
    "\\": "-"
    "|": "-"
    "?": ""
    "*": ""
    "<": ""
    ">": ""

  # Normalize unicode (NFC, NFD, NFKC, NFKD, or null)
  unicode_normalize: "NFC"

  # Convert to lowercase
  lowercase: false

  # Max filename length (without extension)
  max_length: 100

  # Collapse multiple dashes
  collapse_dashes: true

# =============================================================================
# CONTENT CLEANING (Optional - Not Yet Implemented)
# =============================================================================
# Note: Configuration exists but cleaning logic is not yet implemented.
# This is a placeholder for future functionality.
content_cleaning:
  enabled: false

  # Patterns to remove from content (when implemented)
  patterns:
    - name: "newsletter_cta"
      # Regex pattern (case insensitive by default)
      pattern: "^.*subscribe to (our|the) newsletter.*$"
      flags: "im"  # i=case insensitive, m=multiline

    - name: "social_footer"
      pattern: "^.*follow us on (twitter|facebook|linkedin).*$"
      flags: "im"

    - name: "related_articles"
      pattern: "^## (Related|See Also|More Articles).*?(?=^## |\\Z)"
      flags: "ims"  # s=dotall (. matches newlines)

# =============================================================================
# FOLDER STATISTICS
# =============================================================================
folders:
  # Warning thresholds (set to null to disable)
  warn_below: 10    # Warn if folder has fewer articles
  warn_above: 45    # Warn if folder has more articles

# =============================================================================
# CACHE SETTINGS
# =============================================================================
cache:
  # What to track
  track_urls: true
  track_content_hash: true

  # Hash algorithm (md5, sha1, sha256)
  hash_algorithm: "sha256"

  # Truncate hash to N characters (null for full hash)
  hash_length: 16

# =============================================================================
# FETCH SETTINGS
# =============================================================================
fetch:
  # Request settings
  timeout: 30                    # Timeout in seconds
  user_agent: "clipmd/0.1"        # User-Agent header
  max_concurrent: 5              # Max parallel fetches (async)

  # Retry settings
  max_retries: 3
  retry_delay: 1                 # Seconds between retries

  # Content extraction
  extract_metadata: true         # Try to extract title, author, date
  include_images: false          # Download and embed images (future)

  # Readability mode - extract main content only
  readability: true

  # Frontmatter template (uses extracted or default values)
  frontmatter_template: |
    title: "{title}"
    source: "{url}"
    author: "{author}"
    published: "{published}"
    clipped: "{clipped}"
    description: "{description}"

  # Filename template
  # Available variables: {date}, {title}, {domain}
  filename_template: "{date}-{title}"

  # Default values when extraction fails
  defaults:
    author: ""
    published: ""
    description: ""

# =============================================================================
# OUTPUT FORMATS
# =============================================================================
output:
  # Default format for metadata extraction
  metadata_format: "markdown"  # markdown, json, yaml

  # Include content preview in metadata
  include_content: true
  max_content_chars: 150

  # Statistics output
  stats_format: "table"  # table, json, yaml
```

## Commands Reference

### Global Options

These options apply to all commands:

```bash
clipmd [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --verbose         Increase output verbosity (can be repeated: -vv)
  -q, --quiet           Suppress non-essential output
  --config PATH         Use custom config file
  --no-color            Disable colored output
  --version             Show version and exit
  --help                Show help and exit
```

**Verbosity levels:**
- Default: Normal output (progress, summaries)
- `-q` / `--quiet`: Errors only, machine-readable output
- `-v` / `--verbose`: Detailed progress, debug info
- `-vv`: Very verbose, includes all internal operations

**Examples:**
```bash
clipmd -q fetch "https://example.com"     # Silent, only errors
clipmd -v preprocess                       # Show detailed progress
clipmd --config ~/alt-config.yaml stats   # Use alternate config
clipmd --no-color report > report.md      # Disable colors for file output
```

### Capture Commands

These commands fetch and save web content.

#### `clipmd fetch`

Fetch URLs and convert to markdown with YAML frontmatter.

```bash
clipmd fetch [OPTIONS] URLS...

Arguments:
  URLS                  One or more URLs to fetch

Options:
  --output, -o PATH     Output directory (default: config root)
  --file, -f PATH       Read URLs from file (one per line)
  --rss                 Treat URL as RSS/Atom feed, fetch all entries
  --rss-limit INT       Max entries to fetch from feed (default: 10)
  --check-duplicates    Skip URLs already in cache (default: true)
  --no-readability      Keep full HTML, don't extract main content
  --dry-run             Show what would be fetched without saving
  --format FORMAT       Output info format: text, json (default: text)
  --no-cache-update     Skip cache update
```

**Single URL:**

```bash
clipmd fetch "https://example.com/article"
```

**Output:**

```
Fetching: https://example.com/article
  ✓ Title: How to Write Better Code
  ✓ Author: Jane Smith
  ✓ Published: 2024-01-15
  ✓ Saved: 20240115-How-to-Write-Better-Code.md

1 article saved.
```

**Multiple URLs:**

```bash
clipmd fetch "https://example.com/one" "https://example.com/two"

# Or from a file:
clipmd fetch -f urls.txt
```

**Output:**

```
Fetching 3 URLs...

1/3 https://example.com/article-one
    ✓ 20240115-Article-One.md

2/3 https://example.com/article-two
    ✓ 20240116-Article-Two.md

3/3 https://example.com/duplicate
    ⊘ Skipped (already in cache)

Summary: 2 saved, 1 skipped (duplicate)
```

**With duplicate check disabled:**

```bash
clipmd fetch --no-check-duplicates "https://example.com/article"
```

**Dry run (show metadata without saving):**

```bash
clipmd fetch --dry-run "https://example.com/article"
```

**Output:**

```
Would fetch: https://example.com/article
  Title: How to Write Better Code
  Author: Jane Smith
  Published: 2024-01-15
  Filename: 20240115-How-to-Write-Better-Code.md

  Preview (first 200 chars):
  Writing clean code is essential for maintainability. In this article,
  we'll explore best practices for...

[Dry run - no files created]
```

**Generated file format:**

```markdown
---
title: "How to Write Better Code"
source: "https://example.com/article"
author: "Jane Smith"
published: 2024-01-15
clipped: 2024-01-17
description: "Writing clean code is essential for maintainability..."
---

# How to Write Better Code

Writing clean code is essential for maintainability. In this article,
we'll explore best practices for...

## Section One

Content here...
```

**URL file format (urls.txt):**

```
# Full-line comments start with #
https://example.com/article-one
https://example.com/article-two

# Blank lines are ignored
https://example.com/article-three

# Inline comments are supported (stripped before processing)
https://example.com/ai-article    # Article about AI coding practices
https://example.com/tutorial      # Need to read this for project X
https://blog.com/best-practices   # Points 1 and 3 are most relevant
```

**RSS feeds file (feeds.txt):**

```
# My RSS feeds - run weekly with: clipmd fetch --rss -f feeds.txt

# Tech blogs
https://blog.example.com/feed.xml           # Great AI content
https://another-blog.com/rss                 # Security articles

# News
https://news.site.com/atom.xml               # Daily news digest
```

```bash
# Fetch new articles from all feeds
clipmd fetch --rss -f feeds.txt

# With limit per feed
clipmd fetch --rss --rss-limit 5 -f feeds.txt
```

**Output:**

```
Processing 3 RSS feeds from feeds.txt...

[1/3] https://blog.example.com/feed.xml
      Found 15 entries, fetching up to 5
      ✓ 3 saved, 2 skipped (in cache)

[2/3] https://another-blog.com/rss
      Found 8 entries, fetching up to 5
      ✓ 5 saved, 0 skipped

[3/3] https://news.site.com/atom.xml
      Found 20 entries, fetching up to 5
      ✓ 1 saved, 4 skipped (in cache)

Summary: 9 saved, 6 skipped (duplicates)
```

**RSS/Atom feed support:**

```bash
# Fetch latest 10 articles from a blog's RSS feed
clipmd fetch --rss "https://blog.example.com/feed.xml"

# Fetch up to 50 articles
clipmd fetch --rss --rss-limit 50 "https://blog.example.com/rss"

# Fetch from multiple feeds
clipmd fetch --rss "https://blog1.com/feed" "https://blog2.com/atom.xml"

# Dry run to see what would be fetched
clipmd fetch --rss --dry-run "https://blog.example.com/feed.xml"
```

**Output:**

```
Fetching RSS feed: https://blog.example.com/feed.xml
  Found 25 entries, fetching 10 (--rss-limit)

1/10 https://blog.example.com/post-one
     ✓ 20240115-Post-One.md

2/10 https://blog.example.com/post-two
     ⊘ Skipped (already in cache)

3/10 https://blog.example.com/post-three
     ✓ 20240112-Post-Three.md

...

Summary: 8 saved, 2 skipped (duplicates)
```

**Handling failures:**

```bash
clipmd fetch -f urls.txt --format json

```json
{
  "success": [
    {"url": "https://example.com/one", "file": "20240115-Article.md"}
  ],
  "failed": [
    {"url": "https://paywalled.com/article", "error": "403 Forbidden"},
    {"url": "https://timeout.com/slow", "error": "Timeout after 30s"}
  ],
  "skipped": [
    {"url": "https://example.com/dupe", "reason": "Already in cache"}
  ]
}
```

**Limitations:**
- JavaScript-rendered content may not be fully captured (static HTML only)
- Paywalled content will fail (403/401 errors)
- Some sites may block automated requests
- Rate limiting is basic (sequential fetching with configurable delay)

For complex scraping needs, consider dedicated tools like [Jina Reader](https://jina.ai/reader/) or browser-based clippers, then use clipmd for organization.

### Data Extraction Commands

These commands generate output for LLM or human consumption.

#### `clipmd extract`

Extract metadata from articles into a compact, LLM-optimized format.

```bash
clipmd extract [OPTIONS] [PATH]

Arguments:
  PATH                  Directory to scan (default: config root)

Options:
  --output, -o PATH     Output file (default: stdout)
  --format FORMAT       Output format: markdown, json, yaml (default: markdown)
  --max-chars INT       Max description/content chars (default: 150)
  --include-content     Include content preview (default: from config)
  --include-stats       Include word count and language (requires langdetect)
  --folders             Include list of existing folders
```

**Output (markdown format):**

```markdown
# Articles Metadata
# Generated: 2024-01-17T14:30:00
# Total: 79 articles

## Existing Folders
AI-Tools, Science, Tech, Misc

## Articles

1. 20240115-Some-Article.md
   URL: blog.example.com
   Title: Some Article Title
   Desc: First 150 characters of description or content...

2. 20240116-Another-Article.md
   URL: news.example.com
   Title: Another Article
   Desc: Description preview here...
```

**Output with --include-stats:**

```markdown
## Articles

1. 20240115-Some-Article.md
   URL: blog.example.com | 1,234 words | en
   Title: Some Article Title
   Desc: First 150 characters of description or content...

2. 20240116-Article-Francais.md
   URL: news.example.fr | 856 words | fr
   Title: Un Article en Français
   Desc: Description preview here...
```

**Output (JSON format):**

```json
{
  "generated": "2024-01-17T14:30:00",
  "total": 79,
  "folders": ["AI-Tools", "Science", "Tech", "Misc"],
  "articles": [
    {
      "index": 1,
      "filename": "20240115-Some-Article.md",
      "url": "https://blog.example.com/post",
      "title": "Some Article Title",
      "description": "First 150 characters...",
      "word_count": 1234,
      "language": "en"
    }
  ]
}
```

**Note:** `word_count` and `language` fields are only included with `--include-stats`. Language detection requires the optional `langdetect` dependency.

#### `clipmd stats`

Display folder statistics.

```bash
clipmd stats [OPTIONS]

Options:
  --format FORMAT       Output format: table, json, yaml
  --warnings-only       Only show folders outside thresholds
  --include-special     Include special folders (0-*, etc.)
```

**Output:**

```
Folder Statistics (79 articles in 8 folders)

  45  AI-Tools/        ⚠️  above threshold (45)
  12  Science/
  11  Tech/
   8  Misc/            ⚠️  below threshold (10)
   3  Archive/         ⚠️  below threshold (10)

Warnings: 3 folders outside 10-45 range
```

#### `clipmd duplicates`

Find duplicate articles.

```bash
clipmd duplicates [OPTIONS]

Options:
  --by-url              Find by matching source URL (default)
  --by-hash             Find by content hash
  --by-filename         Find by similar filename
  --output, -o PATH     Output file
  --format FORMAT       Output format: markdown, json
```

**Output:**

```markdown
# Duplicate Articles

## By URL (5 groups)

1. https://example.com/article
   - Folder-A/20240115-Article.md
   - Folder-B/20240116-Article-Copy.md

2. https://blog.example.com/post
   - 20240117-Post.md
   - Archive/Post-Old.md
```

### Preprocessing Commands

These commands perform deterministic transformations.

#### `clipmd preprocess`

Clean and prepare articles.

```bash
clipmd preprocess [OPTIONS] [PATH]

Arguments:
  PATH                  Directory to process (default: config root)

Options:
  --dry-run             Show what would be done
  --no-url-clean        Skip URL cleaning
  --no-filename-clean   Skip filename sanitization
  --no-date-prefix      Skip date prefix addition
  --no-dedupe           Skip duplicate detection
  --no-frontmatter-fix  Skip frontmatter fixing
```

**Frontmatter fixing** (enabled by default):
- Fixes multi-line field values (converts to single line or quoted block)
- Fixes multi-line wikilink fields (e.g., `[[link\ntext]]` → `[[link text]]`)
- Fixes invalid YAML quoting (unescaped colons, quotes in titles)
- Escapes special characters in field values
- Normalizes date formats
- Removes duplicate keys
- Validates YAML structure and reports unfixable issues

**Output:**

```
Preprocessing Summary
=====================
Scanned: 89 files

Frontmatter fixing:
  - Fixed: 7
    - multi-line wikilinks: 3
    - escaped quotes in titles: 2
    - invalid YAML syntax: 2
  - Already valid: 82

URL cleaning:
  - Cleaned: 45
  - Already clean: 44

Filename sanitization:
  - Renamed: 12
  - Already clean: 77

Date prefixes:
  - Added: 8
    - from frontmatter: 5
    - from content: 3 (extracted from article body)
  - Already prefixed: 81

Duplicates found: 3
  - 20240115-Article.md duplicates 20240114-Article.md (same URL)
  [Manually review and resolve]

Ready for categorization: 86 files
```

### Execution Commands

These commands execute decisions (from LLM or human).

#### `clipmd move`

Move files based on a categorization file.

```bash
clipmd move [OPTIONS] CATEGORIZATION_FILE

Arguments:
  CATEGORIZATION_FILE   Path to categorization file

Options:
  --dry-run             Show what would be moved
  --create-folders      Create folders if needed (default: true)
  --no-cache-update     Skip cache update
  --source-dir PATH     Source directory (default: config root)
```

**Input format (categorization.txt):**

```
# Lines starting with # are ignored
# Format: Category - filename.md
# Use TRASH to move to system trash

1. AI-Tools - 20240115-Article-One.md
2. Science - 20240116-Article-Two.md
3. Tech - 20240117-Article-Three.md
4. TRASH - duplicate-article.md
5. NEW-FOLDER - 20240118-New-Topic.md
```

**Output:**

```
Moving files...

Created folders:
  - NEW-FOLDER/

Moved:
  ✓ 20240115-Article-One.md → AI-Tools/
  ✓ 20240116-Article-Two.md → Science/
  ✓ 20240117-Article-Three.md → Tech/
  ✓ duplicate-article.md → Trash
  ✓ 20240118-New-Topic.md → NEW-FOLDER/

Summary: 5 moved, 1 trashed, 1 folder created
Cache updated.
```

#### `clipmd trash`

Move files to system trash.

```bash
clipmd trash [OPTIONS] FILES...

Arguments:
  FILES                 Files to trash (glob patterns supported)

Options:
  --dry-run             Show what would be trashed
  --no-cache-update     Skip cache update (don't mark as removed)
```

## Data Structures

### Cache (`cache.json`)

The cache tracks all articles by URL to enable duplicate detection and history.

```json
{
  "version": 1,
  "updated": "2024-01-17T14:30:00Z",
  "entries": {
    "https://example.com/article-one": {
      "filename": "20240115-Article-One.md",
      "title": "Article One",
      "folder": "AI-Tools",
      "first_seen": "2024-01-15",
      "last_seen": "2024-01-17",
      "removed": false,
      "content_hash": "a1b2c3d4e5f6..."
    },
    "https://example.com/old-article": {
      "filename": "20231201-Old-Article.md",
      "title": "Old Article",
      "folder": null,
      "first_seen": "2023-12-01",
      "last_seen": "2024-01-10",
      "removed": true,
      "removed_at": "2024-01-10T09:15:00Z",
      "content_hash": "b2c3d4e5f6g7..."
    }
  }
}
```

**Fields:**

| Field | Description |
|-------|-------------|
| `filename` | Current filename (with date prefix) |
| `title` | Article title from frontmatter |
| `folder` | Current folder location (null if in root) |
| `first_seen` | Date article was first added |
| `last_seen` | Date article was last seen/updated |
| `removed` | Whether article has been trashed |
| `removed_at` | Timestamp when removed (if applicable) |
| `content_hash` | Hash of content for duplicate detection |

**Cache behavior:**
- Updated automatically by `fetch`, `move`, `trash`, `preprocess`
- Used by `fetch --check-duplicates` to skip known URLs
- Used by `duplicates --by-url` and `duplicates --by-hash`
- `cache clean` removes entries for files that no longer exist
- `cache check URL` queries if a URL is known

### Setup Commands

#### `clipmd init`

Initialize clipmd in a directory.

```bash
clipmd init [OPTIONS]

Options:
  --config PATH         Custom config location
  --minimal             Create minimal config only
  --discover            Run rule discovery after init
```

Creates:
- `config.yaml` (or `.clipmd/config.yaml`)
- `.clipmd/` directory for cache and rules

#### `clipmd validate`

Validate configuration and setup.

```bash
clipmd validate [OPTIONS]

Options:
  --fix                 Attempt to fix issues
```

**Output:**

```
Validating clipmd setup...

✓ Config file found: config.yaml
✓ Config syntax valid
✓ Root path exists: /Users/you/Articles
✓ Cache directory writable
⚠ Domain rules file not found (optional)
✓ 89 markdown files found

Validation passed with 1 warning.
```

## Workflow Examples

### Example 1: Save and Organize Articles (Complete Flow)

```bash
# 1. Fetch articles from URLs
clipmd fetch -f reading-list.txt

# 2. Preprocess (clean, dedupe)
clipmd preprocess

# 3. Extract metadata for categorization
clipmd extract --folders > articles-metadata.txt

# 4. [LLM or human reviews and creates categorization.txt]

# 5. Move to folders
clipmd move categorization.txt

# 6. Done!
clipmd stats
```

### Example 2: Triage New Articles

```bash
# 1. Preprocess (deterministic cleanup)
clipmd preprocess

# 2. Extract metadata for LLM
clipmd extract --folders > articles-metadata.txt

# 3. [LLM reads articles-metadata.txt and generates categorization.txt]

# 4. Execute categorization
clipmd move categorization.txt

# 5. View results
clipmd stats
```

### Example 3: Reorganize Existing Folders

```bash
# 1. Get current statistics
clipmd stats --warnings-only

# 2. Extract metadata from problematic folders
clipmd extract --max-chars 100 "Too-Big-Folder/" > reorganize-metadata.txt

# 3. [LLM reads metadata, suggests new organization]

# 4. Execute reorganization
clipmd move reorganization.txt

# 5. Verify
clipmd stats
```

### Example 4: Find and Remove Duplicates

```bash
# 1. Find duplicates
clipmd duplicates --by-url --by-hash > duplicates.txt

# 2. [Human or LLM reviews, creates removal list]

# 3. Remove duplicates
clipmd trash Folder/duplicate1.md Folder/duplicate2.md

# Or if LLM generated a categorization file with TRASH entries:
clipmd move cleanup.txt
```

### Example 5: Batch Process Before Removal

```bash
# 1. Extract full content for LLM analysis
clipmd extract --max-chars 5000 "To-Process/" --format json > batch.json

# 2. [LLM analyzes, extracts insights, creates summary notes]

# 3. Move originals to trash
clipmd trash "To-Process/*.md"
```

## LLM Integration Guide

### For Claude Code / Aider / Cursor

Create a custom command or prompt that:

1. Runs `clipmd extract` to get article metadata
2. Reads the output
3. Makes categorization decisions
4. Outputs a simple categorization file
5. Runs `clipmd move` to execute

**Example Claude Code command (`.claude/commands/triage.md`):**

```markdown
# Article Triage

Categorize articles from the root folder.

## Step 1: Preprocess
Run: `clipmd preprocess`

## Step 2: Extract metadata
Run: `clipmd extract --folders`
Read the output.

## Step 3: Categorize
For each article needing categorization:
- Assign to an existing folder based on topic
- Or suggest a new folder if none fit
- Mark obvious duplicates as TRASH

Output format (categorization.txt):
```
1. Folder-Name - filename.md
2. Another-Folder - another-file.md
3. TRASH - duplicate.md
```

## Step 4: Execute
Run: `clipmd move categorization.txt`

## Step 5: Report
Run: `clipmd stats`
```

### Token Efficiency

| Scenario | Without clipmd | With clipmd | Savings |
|----------|--------------|------------|---------|
| 100 articles triage | ~200k tokens | ~5k tokens | 97% |
| 50 articles reorganize | ~100k tokens | ~3k tokens | 97% |
| Duplicate detection | ~50k tokens | ~2k tokens | 96% |

## Project Structure

```
clipmd/
├── src/
│   └── clipmd/
│       ├── __init__.py
│       ├── cli.py              # Click CLI entry point
│       ├── config.py           # Configuration loading
│       │
│       ├── commands/           # CLI commands
│       │   ├── fetch.py        # URL fetching
│       │   ├── extract.py      # Metadata extraction
│       │   ├── stats.py        # Folder statistics
│       │   ├── duplicates.py   # Duplicate detection
│       │   ├── preprocess.py   # File preprocessing
│       │   ├── move.py         # File moving
│       │   ├── trash.py        # Trash operations
│       │   ├── init.py         # Vault initialization
│       │   └── validate.py     # Config validation
│       │
│       └── core/               # Business logic
│           ├── cache.py          # URL/content cache
│           ├── dates.py          # Date parsing & extraction from content
│           ├── discovery.py      # File discovery
│           ├── duplicates.py     # Duplicate detection
│           ├── extractor.py      # Metadata extraction
│           ├── fetcher.py        # Web fetching & HTML→Markdown
│           ├── filepath_utils.py # File path operations
│           ├── formatters.py     # Output formatting helpers
│           ├── frontmatter.py    # YAML frontmatter parsing
│           ├── hasher.py         # Content hashing
│           ├── initializer.py    # Vault initialization
│           ├── mover.py          # File moving logic
│           ├── preprocessor.py   # File preprocessing
│           ├── rss.py            # RSS/Atom feed parsing
│           ├── sanitizer.py      # URL/filename cleaning
│           ├── stats.py          # Statistics generation
│           ├── trash.py          # Trash operations
│           ├── url_utils.py      # URL utilities
│           └── validator.py      # Config validation
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   └── integration/
│
├── pyproject.toml
└── README.md
```

## Development

### Stack & Tools

| Tool | Purpose |
|------|---------|
| **Python 3.13+** | Latest Python version |
| **uv** | Package management, virtual environments |
| **ruff** | Linting and formatting (replaces black, isort, flake8) |
| **ty** | Type checking (Astral's type checker) |
| **pytest** | Testing framework |
| **pre-commit** | Git hooks for quality checks |
| **GitHub Actions** | CI/CD pipeline |

### Code Principles

- **Clean Code** - Readable, well-named functions and variables
- **KISS** - Keep it simple, avoid over-engineering
- **YAGNI** - Don't build features until needed
- **DRY** - Extract common logic, but not prematurely
- **Static Typing** - Full type hints, strict type checking

### Implementation Workflow

Development follows a phase-by-phase approach with atomic commits:

**Branch Strategy:**
```bash
# Create feature branch from main
git checkout -b feat/phase-1-core-setup

# Work on implementation...

# When phase complete, merge or create PR
```

**Atomic Commits:**

Each commit must be self-contained and pass all quality checks:

1. **Code compiles/runs** - No syntax errors, imports resolve
2. **Tests pass** - All existing + new tests for the phase
3. **Linting passes** - `ruff check` clean
4. **Formatting correct** - `ruff format` applied
5. **Type checking passes** - `ty check` clean

**Phase Implementation Pattern:**

```bash
# 1. Implement phase code
# 2. Write/update tests
# 3. Run quality checks
make check  # runs: lint, typecheck, test-cov

# 4. Commit with descriptive message
git add -A
git commit -m "feat(core): add frontmatter parsing

- Add frontmatter.py with YAML parsing
- Add field mapping from config
- Add unit tests for edge cases
- 95% coverage for new code"
```

**Implementation Status (Phase 1 Complete):**

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Project setup | ✓ Complete - pyproject.toml, CLI skeleton, config loading |
| 2 | Core utilities | ✓ Complete - frontmatter, dates, sanitizer, hasher |
| 3 | Cache system | ✓ Complete - cache.py, URL tracking, content hashing |
| 4 | Preprocessing | ✓ Complete - preprocess command, URL/filename cleaning |
| 5 | Extraction | ✓ Complete - extract command, metadata output formats |
| 6 | Execution | ✓ Complete - move, trash commands, folder operations |
| 7 | Fetch | ✓ Complete - fetch command, HTML→Markdown, RSS support |
| 8 | Analysis | ✓ Complete - stats, duplicates commands |
| 9 | Setup | ✓ Complete - init, validate commands |

**Phase 2+ Features:**
- Domain rules system (discover-rules, --apply-rules)
- Report command with recommendations
- URLs extraction command
- Cache management commands
- Content cleaning implementation
- Advanced preprocess options (--auto-remove-dupes)

**Commit Message Format:**

```
type(scope): short description

- Bullet points for details
- What was added/changed/fixed
- Test coverage notes if relevant
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

### Error Handling

Custom exception hierarchy with Rich-formatted output:

```python
# src/clipmd/exceptions.py
class ClipmdError(Exception):
    """Base exception for all clipmd errors."""
    exit_code: int = 1

class ConfigError(ClipmdError):
    """Configuration file errors."""

class FetchError(ClipmdError):
    """URL fetching errors."""

class ParseError(ClipmdError):
    """Frontmatter/content parsing errors."""

class CacheError(ClipmdError):
    """Cache read/write errors."""

class ValidationError(ClipmdError):
    """Input validation errors."""

class PartialSuccessError(ClipmdError):
    """Some operations succeeded, some failed."""
    exit_code: int = 2
```

**Error output** (using Rich):

```python
from rich.console import Console

console = Console(stderr=True)

def handle_error(e: ClipmdError) -> None:
    console.print(f"[red]Error:[/red] {e}")
    if verbose:
        console.print_exception()
    sys.exit(e.exit_code)
```

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Error (operation failed) |
| `2` | Partial success (some items failed, some succeeded) |

```bash
clipmd fetch -f urls.txt
echo $?  # 0 = all succeeded, 1 = all failed, 2 = some failed
```

### Logging Strategy

- **User output**: Rich console (progress bars, tables, colored status)
- **Debug info**: Python `logging` module, enabled with `--verbose`

```python
import logging
from rich.console import Console
from rich.logging import RichHandler

# User-facing output
console = Console()

# Debug logging (only with --verbose)
def setup_logging(verbosity: int) -> None:
    level = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}.get(verbosity, logging.DEBUG)
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=Console(stderr=True), show_time=False)],
    )

logger = logging.getLogger("clipmd")
```

### Async Fetching

Use `httpx` async for parallel URL fetching:

```python
import asyncio
import httpx

async def fetch_urls(urls: list[str], max_concurrent: int = 5) -> list[FetchResult]:
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_one(client: httpx.AsyncClient, url: str) -> FetchResult:
        async with semaphore:
            try:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                return FetchResult(url=url, content=response.text, success=True)
            except httpx.HTTPError as e:
                return FetchResult(url=url, error=str(e), success=False)

    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = [fetch_one(client, url) for url in urls]
        return await asyncio.gather(*tasks)
```

### Configuration with Pydantic

Use Pydantic v2 for config validation:

```python
# src/clipmd/config.py
from pathlib import Path
from pydantic import BaseModel, Field

class PathsConfig(BaseModel):
    root: Path = Path(".")
    cache: Path = Path(".clipmd/cache.json")
    rules: Path = Path(".clipmd/domain-rules.yaml")

class FetchConfig(BaseModel):
    timeout: int = 30
    max_concurrent: int = 5
    user_agent: str = "clipmd/0.1"
    readability: bool = True

class Config(BaseModel):
    version: int = 1
    paths: PathsConfig = Field(default_factory=PathsConfig)
    fetch: FetchConfig = Field(default_factory=FetchConfig)
    # ... other sections

def load_config(path: Path | None = None) -> Config:
    """Load config from file or return defaults."""
    if path is None:
        path = Path("config.yaml")

    if not path.exists():
        return Config()

    import yaml
    with path.open() as f:
        data = yaml.safe_load(f)

    return Config.model_validate(data)
```

### Security

**URL validation:**

```python
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}

def validate_url(url: str) -> str:
    """Validate and normalize URL."""
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValidationError(f"Invalid URL scheme: {parsed.scheme}")

    if not parsed.netloc:
        raise ValidationError(f"Invalid URL: missing domain")

    return url
```

**Path traversal prevention:**

```python
from pathlib import Path

def safe_filename(filename: str, base_dir: Path) -> Path:
    """Ensure filename doesn't escape base directory."""
    # Remove any path components
    safe_name = Path(filename).name

    # Resolve and check it's within base_dir
    full_path = (base_dir / safe_name).resolve()

    if not full_path.is_relative_to(base_dir.resolve()):
        raise ValidationError(f"Invalid filename: {filename}")

    return full_path
```

### Docstrings

Use Google style docstrings:

```python
def extract_metadata(
    path: Path,
    max_chars: int = 150,
    include_stats: bool = False,
) -> ArticleMetadata:
    """Extract metadata from a markdown article.

    Parses YAML frontmatter and extracts key fields for LLM consumption.

    Args:
        path: Path to the markdown file.
        max_chars: Maximum characters for description preview.
        include_stats: Include word count and language detection.

    Returns:
        ArticleMetadata object with extracted fields.

    Raises:
        ParseError: If frontmatter is invalid or file unreadable.
    """
```

### Versioning

**Semantic Versioning** (MAJOR.MINOR.PATCH):

- MAJOR: Breaking changes to CLI or config format
- MINOR: New features, backward compatible
- PATCH: Bug fixes

**CHANGELOG.md** (Keep a Changelog format):

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2024-01-20

### Added
- Initial release
- `fetch` command with RSS support
- `extract` command for LLM-optimized metadata
- `preprocess` command for cleaning articles
- `move` command for organizing files
- Domain rules discovery
- URL cache for duplicate detection
```

### Test Strategy

| Test Type | Coverage | Purpose |
|-----------|----------|---------|
| **Unit tests** | 90%+ | Core logic (frontmatter, rules, cache, sanitizer, etc.) |
| **CLI tests** | Commands only | Test CLI interface, not business logic |
| **Integration tests** | Key workflows | End-to-end for critical paths only |

```
tests/
├── unit/
│   ├── test_frontmatter.py    # Frontmatter parsing
│   ├── test_rules.py          # Domain rules matching
│   ├── test_cache.py          # Cache operations
│   ├── test_sanitizer.py      # URL/filename cleaning
│   ├── test_cleaner.py        # Content cleaning
│   ├── test_fetcher.py        # Web fetching (mocked)
│   ├── test_dates.py          # Date parsing & content extraction
│   └── test_hasher.py         # Content hashing
├── cli/
│   ├── test_fetch_cmd.py      # fetch command interface
│   ├── test_extract_cmd.py    # extract command interface
│   ├── test_move_cmd.py       # move command interface
│   └── ...
├── integration/
│   ├── test_fetch_workflow.py # Fetch → preprocess → extract
│   └── test_triage_workflow.py # Full triage flow
├── fixtures/
│   └── sample-vault/
└── conftest.py
```

### Test Fixtures

The `tests/fixtures/sample-vault/` directory contains sample articles for testing:

| File | Purpose |
|------|---------|
| `20240115-Sample-Article.md` | Valid article with proper frontmatter |
| `20240116-Article-With-Issues.md` | Frontmatter with quotes, colons, non-standard dates |
| `no-date-prefix-article.md` | Missing date prefix (needs renaming) |
| `20240117-No-Frontmatter-Date.md` | Date only in body text (extraction test) |
| `20240115-Duplicate-Article.md` | Duplicate URL (same as Sample-Article) |
| `20240118-Wikilink-Issue.md` | Multi-line wikilink in title (YAML break) |
| `AI-Tools/20240110-Claude-API-Guide.md` | Categorized article (domain rules test) |
| `Science/20240112-Space-Discovery.md` | Categorized article (domain rules test) |
| `config.yaml` | Test configuration |
| `.clipmd/cache.json` | Pre-populated cache for testing |
| `.clipmd/domain-rules.yaml` | Sample domain rules |

### Makefile

```makefile
.PHONY: install dev lint format typecheck test test-cov clean build publish

# Development
install:
	uv sync

dev:
	uv sync --all-extras

# Quality
lint:
	uv run ruff check src tests

format:
	uv run ruff format src tests

typecheck:
	uv run ty check src

# Testing
test:
	uv run pytest

test-cov:
	uv run pytest --cov=clipmd --cov-report=term-missing --cov-fail-under=90

# Build & Publish
clean:
	rm -rf dist build *.egg-info

build: clean
	uv build

publish: build
	uv publish

# All checks (used by CI)
check: lint typecheck test-cov
```

### Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: local
    hooks:
      - id: typecheck
        name: typecheck
        entry: uv run ty check src
        language: system
        types: [python]
        pass_filenames: false
```

### GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.13"]

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}

      - name: Install dependencies
        run: uv sync --all-extras

      - name: Lint
        run: uv run ruff check src tests

      - name: Type check
        run: uv run ty check src

      - name: Test with coverage
        run: uv run pytest --cov=clipmd --cov-report=xml --cov-fail-under=90

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: coverage.xml

  publish:
    needs: test
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/v')

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Build
        run: uv build

      - name: Publish to PyPI
        run: uv publish
        env:
          UV_PUBLISH_TOKEN: ${{ secrets.PYPI_TOKEN }}
```

## Dependencies

```toml
# pyproject.toml
[project]
name = "clipmd"
version = "0.1.0"
description = "Clip, organize, and manage markdown articles - LLM workflow assistant"
readme = "README.md"
license = "MIT"
requires-python = ">=3.13"
authors = [{ name = "Your Name", email = "you@example.com" }]
keywords = ["markdown", "articles", "web-clipper", "organizer", "llm"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.13",
    "Topic :: Text Processing :: Markup :: Markdown",
    "Typing :: Typed",
]

dependencies = [
    "click>=8.1",
    "pyyaml>=6.0",
    "pydantic>=2.10",
    "send2trash>=1.8",
    "python-dateutil>=2.9",
    "rich>=13.9",
    # Fetch dependencies
    "httpx>=0.28",
    "beautifulsoup4>=4.12",
    "trafilatura>=2.0",
    "markdownify>=0.14",
    "feedparser>=6.0",
]

[project.optional-dependencies]
lang = [
    "langdetect>=1.0",
]
dev = [
    "pytest>=8.3",
    "pytest-cov>=6.0",
    "ruff>=0.9",
    "ty>=0.0.1a6",
    "pre-commit>=4.0",
]
all = [
    "clipmd[lang,dev]",
]

[project.scripts]
clipmd = "clipmd.cli:main"

[project.urls]
Homepage = "https://github.com/yourusername/clipmd"
Repository = "https://github.com/yourusername/clipmd"
Issues = "https://github.com/yourusername/clipmd/issues"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ARG",    # flake8-unused-arguments
    "SIM",    # flake8-simplify
]
ignore = ["E501"]  # line length handled by formatter

[tool.ruff.lint.isort]
known-first-party = ["clipmd"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"

[tool.coverage.run]
source = ["src/clipmd"]
branch = true

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```

## Future Enhancements

Features considered for future versions:

### Tags Management

Full tag support for organizing articles:

```bash
# List all tags with counts
clipmd tags

# Filter by tags in extract
clipmd extract --tag "ai"              # Articles with 'ai' tag
clipmd extract --tag "ai,coding"       # Articles with ANY of these
clipmd extract --no-tags               # Articles without tags

# Bulk tag operations
clipmd tags add "ai" Article1.md Article2.md
clipmd tags remove "draft" "Folder/*.md"
clipmd tags rename "ml" "machine-learning"

# Tag statistics
clipmd stats --by-tags
```

### Other Potential Features

| Feature | Description |
|---------|-------------|
| **Import from services** | Pocket, Instapaper, Raindrop.io, browser bookmarks |
| **Watch mode** | Auto-process new files as they appear in a folder |
| **Export formats** | Export to EPUB, PDF, or single HTML |
| **Similarity detection** | `duplicates --by-similarity` for fuzzy matching |
| **Obsidian integration** | Update wikilinks when moving/renaming files |
| **Undo/history** | Revert recent operations |

## Success Metrics

| Metric | Target |
|--------|--------|
| Token reduction for triage | >95% |
| Commands needed for workflow | Single pipeline |
| Edge cases handled by tool | All file operations |
| Configuration options | All opinionated choices |
| Test coverage | >80% |
