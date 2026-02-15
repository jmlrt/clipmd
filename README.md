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

```bash
# Initialize in your articles directory
cd ~/Documents/Articles
clipmd init

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

# Auto-remove duplicates
clipmd preprocess --auto-remove-dupes

# Dry run
clipmd preprocess --dry-run
```

**What it does:**
- Fixes invalid YAML frontmatter
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
```

**Input format (categorization.txt):**
```
# Format: Category - filename.md
# Use TRASH to delete

1. AI-Tools - 20240115-Article-One.md
2. Science - 20240116-Article-Two.md
3. TRASH - duplicate-article.md
```

### Statistics

```bash
# View folder statistics
clipmd stats

# Only show warnings
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

Configuration is searched in this order:
1. `./config.yaml` (current directory)
2. `./.clipmd/config.yaml` (project directory)
3. `~/.config/clipmd/config.yaml` (user-wide)

### Minimal Config

```yaml
version: 1
paths:
  root: "."
```

### Example Config

```yaml
version: 1

paths:
  root: "."
  cache: ".clipmd/cache.json"

frontmatter:
  source_url:
    - source
    - url
    - original_url
  title:
    - title
    - name

dates:
  output_format: "%Y%m%d"
  extract_from_content: true

url_cleaning:
  remove_params:
    - utm_source
    - utm_medium
    - fbclid
    - gclid

filenames:
  replacements:
    " ": "-"
    "_": "-"
  max_length: 100
  collapse_dashes: true

folders:
  warn_below: 10
  warn_above: 45
```

See [SPEC.md](SPEC.md) for full configuration reference.

## Example Workflow

### Triage New Articles

```bash
# 1. Fetch articles
clipmd fetch -f reading-list.txt

# 2. Preprocess (clean, dedupe)
clipmd preprocess --auto-remove-dupes

# 3. Extract metadata for LLM
clipmd extract --folders > articles-metadata.txt

# 4. [LLM reads articles-metadata.txt and generates categorization.txt]
# Example LLM prompt:
# "Categorize these articles into the existing folders.
#  Output format: 'N. FolderName - filename.md'"

# 5. Execute categorization
clipmd move categorization.txt

# 6. View results
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
