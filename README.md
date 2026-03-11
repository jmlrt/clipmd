# clipmd

> Clip, organize, and manage markdown articles - LLM workflow assistant.

A CLI tool for saving, organizing, and managing markdown articles with YAML frontmatter. Designed to assist LLM-based workflows by preprocessing files and executing file operations reliably.

**Key Features:**
- 📥 **Fetch** web content and convert to markdown with frontmatter
- 🧹 **Preprocess** articles (clean URLs, sanitize filenames, fix frontmatter)
- 📊 **Extract** metadata in LLM-optimized format (95%+ token reduction)
- 🗂️ **Move** files based on simple categorization lists
- 🔍 **Detect** duplicates by URL or content hash
- 📈 **Statistics** and folder health monitoring

## Installation

```bash
pip install clipmd
# or with uv
uv add clipmd

# With language detection support
pip install clipmd[lang]
```

## Quick Start

**1. Create config file** (`~/.config/clipmd/config.yaml`):
```yaml
version: 1
vault: $HOME/Documents/Articles
cache: $HOME/.cache/clipmd/cache.json
domain_rules:
  github.com: Dev-Tools
  arxiv.org: Science
```

**2. Use clipmd:**
```bash
# Fetch articles from URLs
clipmd fetch "https://example.com/article"
clipmd fetch -f urls.txt  # Or from file

# Preprocess files (clean URLs, sanitize filenames, fix frontmatter)
clipmd preprocess

# Extract metadata for LLM categorization
clipmd extract --folders > articles-metadata.txt

# [LLM or human creates categorization.txt]

# Execute categorization
clipmd move categorization.txt

# View results
clipmd stats
```

## Core Workflow

clipmd is designed for LLM-assisted workflows:

```
┌─────────────────────────────────────┐
│  LLM/Human (Orchestrator)           │
│  - Reads clipmd output              │
│  - Makes categorization decisions   │
│  - Generates simple action lists    │
└─────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  clipmd (Executor)                  │
│  - Fetches and converts content     │
│  - Extracts metadata (minimal)      │
│  - Executes file operations         │
│  - Handles edge cases reliably      │
└─────────────────────────────────────┘
```

## Commands

### Fetch & Capture

```bash
# Fetch single URL
clipmd fetch "https://example.com/article"

# Fetch multiple URLs
clipmd fetch -f urls.txt

# Dry run (preview without saving)
clipmd fetch --dry-run "https://example.com/article"
```

### Preprocess

```bash
# Clean and prepare articles
clipmd preprocess

# Dry run
clipmd preprocess --dry-run

# Find and manage duplicates
clipmd duplicates --by-url
```

**What it does:**
- Fixes invalid YAML frontmatter:
  - Strips Obsidian wikilink syntax (`[[Name]]`, `[[Page|Alias]]`) from field values
  - Repairs unclosed quote strings (e.g. `source: "https://example.com` → adds closing `"`)
  - Fixes multi-line wikilinks and unquoted colons
- Cleans tracking parameters from URLs
- Sanitizes filenames
- Adds date prefixes (from frontmatter or content)
- Detects duplicates

### Extract Metadata

```bash
# Extract for LLM (markdown format)
clipmd extract > metadata.txt

# With existing folders list
clipmd extract --folders > metadata.txt

# Include word count and language
clipmd extract --include-stats > metadata.txt

# JSON output
clipmd extract --format json > metadata.json
```

**Output example:**
```markdown
# Articles Metadata
# Total: 79 articles

## Existing Folders
AI-Tools, Science, Tech, Misc

## Needs Categorization (79 articles)

1. 20240115-Some-Article.md
   URL: blog.example.com
   Title: Some Article Title
   Desc: First 150 characters of description...

2. 20240116-Another-Article.md
   URL: news.example.com
   Title: Another Article
   Desc: Description preview...
```

### Move Files

```bash
# Move based on categorization file
clipmd move categorization.txt

# Dry run
clipmd move --dry-run categorization.txt

# Specify source directory (when articles are in a subdirectory)
clipmd move --source-dir Inbox categorization.txt
```

**Input format (categorization.txt):**
```
# Format: Category - filename.md
# Use TRASH to delete

1. AI-Tools - 20240115-Article-One.md
2. Science - 20240116-Article-Two.md
3. TRASH - duplicate-article.md
```

**Smart checks:**
- If a new folder name closely resembles an existing one (e.g. `Sceince` vs `Science`),
  prompts to confirm before creating it — preventing silent categorization mistakes
- If files are not found at the vault root, hints at the subdirectory to pass as `--source-dir`

### Statistics

```bash
# View folder statistics for vault root
clipmd stats

# Scope to a subdirectory
clipmd stats Inbox/

# Only show folders outside configured thresholds
clipmd stats --warnings-only

# JSON output
clipmd stats --format json
```

### Other Commands

```bash
# Find duplicates
clipmd duplicates --by-url
clipmd duplicates --by-hash

# Move files to trash
clipmd trash file1.md file2.md

# Validate configuration
clipmd validate
```

## Configuration

### Setup

Configuration is stored at: `~/.config/clipmd/config.yaml` (XDG-compliant)

Create the file once and clipmd uses it for all operations:
```bash
mkdir -p ~/.config/clipmd
cat > ~/.config/clipmd/config.yaml << 'EOF'
version: 1

# Required: paths to vault and cache
vault: $HOME/Documents/Articles
cache: $HOME/.cache/clipmd/cache.json

# Optional: domain-based auto-categorization
domain_rules:
  github.com: Dev-Tools
  arxiv.org: Science
EOF
```

Environment variables like `$HOME` and `$XDG_CACHE_HOME` are expanded automatically.

### Complete Configuration Reference

```yaml
version: 1

# =============================================================================
# REQUIRED PATHS
# =============================================================================

# Path to your articles vault (can use $HOME and other env vars)
vault: $HOME/Documents/Articles

# Path to cache file (tracks URLs and content hashes for deduplication)
cache: $HOME/.cache/clipmd/cache.json

# =============================================================================
# AUTO-CATEGORIZATION
# =============================================================================

# Domain to folder mappings (skips LLM categorization for known sources)
domain_rules:
  github.com: Dev-Tools
  arxiv.org: Science
  example.com: News

# =============================================================================
# FOLDER MANAGEMENT
# =============================================================================

# Patterns for folders to exclude from statistics/reorganization
special_folders:
  exclude_patterns:
    - "0-*"        # Folders starting with "0-"
    - ".*"         # Hidden folders
    - "_*"         # Folders starting with "_"

  # Files to always ignore
  ignore_files:
    - "README.md"
    - "CLAUDE.md"

# Warning thresholds for folder health checks
folders:
  warn_below: 10    # Warn if folder has fewer articles
  warn_above: 45    # Warn if folder has more articles

# =============================================================================
# FRONTMATTER FIELD MAPPING
# =============================================================================

# Map semantic fields to your actual field names
# Tool tries each name in order until one is found
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
  # Formats to try when parsing dates (in order)
  input_formats:
    - "%Y-%m-%d"           # 2024-01-17
    - "%Y-%m-%dT%H:%M:%S"  # 2024-01-17T14:30:00
    - "%d/%m/%Y"           # 17/01/2024
    - "%B %d, %Y"          # January 17, 2024
    - "%d %B %Y"           # 17 January 2024
    - "%Y/%m/%d"           # 2024/01/17

  # Format for date prefixes in filenames
  output_format: "%Y%m%d"  # 20240117

  # Field priority for extracting dates (first found is used)
  prefix_priority:
    - published
    - clipped
    - created

  # Try to extract dates from article body if frontmatter is empty
  extract_from_content: true

  # Regex patterns for content date extraction
  content_patterns:
    - r"(?P<day>\d{1,2})(?:st|nd|rd|th)?\s+(?P<month>\w+)\s+(?P<year>\d{4})"
    - r"(?P<month>\w+)\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?,?\s+(?P<year>\d{4})"
    - r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"

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

  # URL unwrap patterns (optional, for link redirects)
  unwrap_patterns: []

# =============================================================================
# FILENAME SANITIZATION
# =============================================================================

filenames:
  # Character replacements for sanitization
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

  # Unicode normalization (NFC, NFD, NFKC, NFKD, or null)
  unicode_normalize: "NFC"

  # Convert filenames to lowercase
  lowercase: false

  # Maximum filename length (including extension)
  max_length: 100

  # Collapse multiple consecutive dashes
  collapse_dashes: true

# =============================================================================
# CACHE TRACKING
# =============================================================================

cache_config:
  # Track URLs to detect duplicates by source
  track_urls: true

  # Track content hash to detect duplicates by content
  track_content_hash: true

  # Truncate hash to N characters (null for full hash)
  hash_length: 16

# =============================================================================
# FETCH SETTINGS
# =============================================================================

fetch:
  # HTTP request settings
  timeout: 30
  user_agent: "clipmd/0.1"

  # Concurrency control for parallel fetching
  max_concurrent: 5

  # Retry settings
  max_retries: 3
  retry_delay: 1

  # Content extraction
  extract_metadata: true
  include_images: false

  # Use readability mode (extract main content only)
  readability: true

  # Frontmatter template for fetched articles
  frontmatter_template: |
    title: "{title}"
    source: "{url}"
    author: "{author}"
    published: "{published}"
    clipped: "{clipped}"
    description: "{description}"

  # Filename template for fetched articles
  filename_template: "{date}-{title}"

  # Default values for missing metadata
  defaults:
    author: ""
    published: ""
    description: ""
```

See [SPEC.md](SPEC.md) for detailed specification.

## Example Workflow

### Triage New Articles

```bash
# 1. Fetch articles
clipmd fetch -f reading-list.txt

# 2. Preprocess (clean URLs, sanitize filenames, fix frontmatter)
clipmd preprocess

# 3. Find duplicates (optional)
clipmd duplicates --by-url

# 4. Extract metadata for LLM
clipmd extract --folders > articles-metadata.txt

# 5. [LLM reads articles-metadata.txt and generates categorization.txt]
# Example LLM prompt:
# "Categorize these articles into the existing folders.
#  Output format: 'N. FolderName - filename.md'"

# 6. Execute categorization
clipmd move categorization.txt

# 7. View results
clipmd stats
```

### Reorganize Existing Folders

```bash
# Check which folders need attention
clipmd stats --warnings-only

# Extract metadata from problematic folder
clipmd extract "Too-Big-Folder/" --max-chars 100 > reorganize.txt

# [LLM suggests better organization]

# Execute
clipmd move reorganization.txt

# Verify
clipmd stats
```

## LLM Integration

clipmd minimizes token usage for LLM workflows:

| Scenario | Without clipmd | With clipmd | Savings |
|----------|---------------|-------------|---------|
| 100 articles triage | ~200k tokens | ~5k tokens | **97%** |
| 50 articles reorganize | ~100k tokens | ~3k tokens | **97%** |
| Duplicate detection | ~50k tokens | ~2k tokens | **96%** |

## Development

```bash
# Install dependencies
make dev

# Run checks (lint, typecheck, tests)
make check

# Run tests with coverage
make test-cov

# Format code
make format
```

### Requirements

- Python 3.13+
- uv (recommended) or pip

## Documentation

- **Full Specification:** [SPEC.md](SPEC.md)
- **Developer Guide:** [CLAUDE.md](CLAUDE.md)

## License

MIT
