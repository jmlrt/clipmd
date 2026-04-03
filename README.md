# clipmd

> Clip, organize, and manage markdown articles - LLM workflow assistant.

A CLI tool for saving, organizing, and managing markdown articles with YAML frontmatter. Designed to assist LLM-based workflows by preprocessing files and executing file operations reliably.

**Key Features:**
- 📥 **Fetch** web content and convert to markdown with frontmatter
- 🧹 **Preprocess** articles (clean URLs, sanitize filenames, fix frontmatter)
- 📊 **Extract** metadata in LLM-optimized format (95%+ token reduction)
- 🤖 **Auto-categorize** known sources using domain rules (reduces LLM tokens)
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

### Automated Triage

Run a complete unattended workflow in one command: fetch RSS + INBOX.md → preprocess → apply domain rules → organize into folders → report stats.

```bash
# Full automated workflow (requires config with domain rules)
clipmd triage

# Dry run preview
clipmd triage --dry-run

# Skip domain rules (move everything to staging)
clipmd triage --no-domain-rules

# Custom staging folder
clipmd triage --staging "inbox"
```

**When to use:**
- Scheduled cron jobs for RSS feeds
- Batch processing new articles with known domain rules
- Combining fetch + preprocess + move in one step

**Configuration:**
Add to `config.yaml`:
```yaml
triage:
  rss_sources:
    - "https://example.com/feed.xml"
    - "https://another.com/rss"
  inbox_file: "INBOX.md"           # Optional: source file with URLs
  staging_folder: "0-To-Categorize" # Folder for unmatched articles

domain_rules:
  github.com: Dev-Tools
  arxiv.org: Science
```

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

**Domain Rules (Automatic Categorization):**

Pre-categorize articles from known sources by adding to `config.yaml`:

```yaml
domain_rules:
  github.com: Dev-Tools
  arxiv.org: Science
  news.ycombinator.com: Tech
```

When domain rules are configured, `extract` automatically suggests folders for matching articles:

```markdown
# Articles Metadata
# Total: 79 articles

## Existing Folders
AI-Tools, Science, Tech, Misc

## Articles (79 articles)

1. 20240115-GitHub-Repo.md → Dev-Tools
   URL: github.com
   Title: GitHub Repository Article

2. 20240116-ArXiv-Paper.md → Science
   URL: arxiv.org
   Title: ArXiv Research Paper

3. 20240117-Unknown-Source.md
   URL: example.com
   Title: Unknown Source (LLM must categorize)
```

This reduces LLM token usage by pre-categorizing familiar sources — the LLM only needs to categorize articles from unfamiliar domains.

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

Configuration is stored at: `~/.config/clipmd/config.yaml` (XDG-compliant)

### Minimal Setup

Create the file once and clipmd uses it for all operations:
```bash
mkdir -p ~/.config/clipmd
cat > ~/.config/clipmd/config.yaml << 'EOF'
version: 1
vault: $HOME/Documents/Articles
cache: $HOME/.cache/clipmd/cache.json
EOF
```

Environment variables like `$HOME` and `$XDG_CACHE_HOME` are expanded automatically.

### Full Configuration

Copy [`example-config.yaml`](example-config.yaml) and customize for your needs. It includes all available options with detailed comments.

See [SPEC.md](SPEC.md) for complete configuration reference.

## Example Workflow

### Triage New Articles (Manual)

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

### Automated Triage (RSS/INBOX)

When configured with RSS sources and domain rules, run the entire workflow automatically:

```bash
# One command handles: fetch → preprocess → apply domain rules → organize → stats
clipmd triage

# Or on a schedule (cron)
# 0 9 * * * /usr/local/bin/clipmd triage
```

**Prerequisites:**
1. Configure RSS sources and domain rules in `config.yaml`
2. Create `INBOX.md` in vault root (optional, for manual URLs)

**Configuration example:**
```yaml
triage:
  rss_sources:
    - "https://example.com/feed.xml"
  inbox_file: "INBOX.md"
  staging_folder: "0-To-Categorize"

domain_rules:
  github.com: Dev-Tools
  arxiv.org: Science
```

**Workflow:**
- ✅ Fetches RSS articles automatically
- ✅ Processes INBOX.md URLs (clears file on success)
- ✅ Preprocesses all articles
- ✅ Applies domain rules to matching articles
- ✅ Moves unmatched to staging folder for later LLM categorization
- ✅ Generates final stats

Articles matching domain rules are organized automatically. Unmatched articles go to staging for LLM review (same as manual workflow step 4-6).

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
