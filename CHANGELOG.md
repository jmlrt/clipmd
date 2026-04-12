# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `triage` command: Fully unattended article organization workflow
  - Orchestrates fetch → preprocess → apply domain rules → move to staging in one command
  - Fetches RSS sources and INBOX.md, automatically organizes articles by domain rules
  - Unmapped articles moved to staging folder for optional LLM categorization
  - Supports `--dry-run`, `--no-domain-rules`, `--staging` options
  - Ideal for cron scheduling
- `move --from-json`: Accept JSON categorization file for schema-constrained round-trip with `extract --format json`
- Domain rules system for automatic article pre-categorization
  - Configure in `config.yaml` with `domain_rules: {domain: folder}` mapping
  - `extract` command automatically applies rules and displays suggestions with → notation
  - Reduces LLM token usage by skipping categorization for known sources
- `stats` command now accepts an optional `PATH` argument to scope statistics to a subdirectory (e.g., `clipmd stats Clippings/`)
- `preprocess --auto-remove-dupes` flag to automatically trash duplicate files detected during preprocessing (no confirmation prompt)
- `fetch --file --clear-after` flag to reset the URL file to empty after all URLs are successfully fetched
- `move --skip-missing` flag to skip missing source files with a warning instead of halting on error

### Fixed

- `triage` command no longer re-fetches articles whose source URL redirects to a different domain (e.g. blog migration): both the pre-redirect and final URL are now cached after a successful fetch
- `triage` command now shows the full list of move errors instead of truncating at 5
- `triage` command no longer re-fetches articles that were previously organized into subdirectories but had no cache entry (e.g. articles organized before caching was implemented)
- `triage` command no longer leaves stale source files in vault root after a blocked move — the source is now trashed automatically since the organized destination is the canonical version
- `fetch` command no longer re-fetches manually removed URLs (always skips URLs marked as removed in cache)
- `fetch --clear-after` now clears the URL file after successful fetches and handles partial failures gracefully:
  - On full success: clears URL file entirely
  - On partial failure: retains failed URLs with `[KO]` suffix and actual error messages (e.g., `url # [KO] - Failed to save`)
- `extract` command now skips files without frontmatter (e.g., README.md, CLAUDE.md) and reports them in verbose mode
- Filename sanitization now transliterates accented characters to ASCII equivalents (é→e, ç→c, ë→e, etc.)
- `fetch` command no longer truncates long article titles in generated filenames
- `extract` command no longer wraps long filenames at terminal width (outputs raw text for LLM processing)
- `move` command now resolves destination folders to vault root when `--source-dir` is a relative path (fixes nested folder creation)
- `fetch --rss` no longer re-downloads articles that were previously trashed
- `fetch --rss` now reports RSS feed errors clearly instead of crashing silently
- `fetch` now recovers destination URLs from truncated tracking URLs (patterns like `/L0/https` or `/CL0/https`) after HTTP 400 errors
- `preprocess` error output now includes actionable guidance for fixing YAML frontmatter issues
- `preprocess` now directs users to `clipmd duplicates` command instead of non-existent `--auto-remove-dupes` flag
- `preprocess` now auto-strips Obsidian wikilink syntax (`[[Name]]`, `[[Page|Alias]]`) from frontmatter field values (e.g., `author` field)
- `preprocess` now auto-repairs unclosed quote strings in frontmatter (e.g., `source: "https://example.com` missing closing `"`)
- `fetch --file` now correctly handles tracking URLs with embedded `<>` markers (e.g., newsletter tracking links from La Quotidienne and TLDR)
- `move` command now warns when a new folder name closely resembles an existing folder (Levenshtein distance ≤ 2) and prompts for confirmation before creating it
- `move` command now suggests `--source-dir` when files are not found at the vault root but exist in a subdirectory

## [0.1.0] - 2024-01-20

### Added

#### Core Commands
- `init` command for initializing clipmd in a directory with config scaffolding
- `validate` command for validating configuration and setup
- `fetch` command for fetching web content and converting to markdown with frontmatter
  - RSS/Atom feed support with `--rss` flag and `--rss-limit` option
  - Duplicate detection with `--check-duplicates` (enabled by default)
  - Readability mode for extracting main content
  - Dry run mode with `--dry-run` flag
  - Support for reading URLs from file with `--file` flag
  - Async fetching with configurable concurrency
  - Meta-refresh redirect handling
  - Automatic tracking parameter cleaning
  - Never overwrites existing files (appends suffix `-2.md`, `-3.md`, etc.)
- `preprocess` command for cleaning and preparing articles
  - URL cleaning (tracking parameters, redirect unwrapping)
  - Filename sanitization with configurable replacements
  - Date prefix addition (from frontmatter or content extraction)
  - Frontmatter fixing (multi-line fields, wikilinks, YAML validation)
  - Duplicate detection during preprocessing
- `extract` command for generating LLM-optimized metadata
  - Multiple output formats: markdown, json, yaml
  - Configurable description/content preview length
  - Optional word count and language detection with `--include-stats`
  - Folder list inclusion with `--folders`
- `move` command for executing categorization decisions
  - Automatic folder creation
  - System trash integration for TRASH category
  - Cache updates after moves
  - Dry run mode
- `trash` command for moving files to system trash
  - Glob pattern support
  - Cache updates marking files as removed
- `stats` command for folder statistics
  - Configurable warning thresholds
  - Multiple output formats: table, json, yaml
  - Optional special folder inclusion
- `duplicates` command for finding duplicate articles
  - Detection by URL (default)
  - Detection by content hash
  - Detection by filename similarity
  - Multiple output formats: markdown, json

#### Core Features
- XDG-compliant configuration file search (project root, .clipmd/, ~/.config/clipmd/)
- Pydantic-based configuration validation
- Flexible frontmatter field mapping (supports multiple field name variants)
- Date parsing with multiple input formats
- Date extraction from article content using regex patterns
- URL cache for duplicate detection and history tracking
- Content hashing for duplicate detection
- Rich-formatted console output with progress bars and colored status
- Shell completion support (bash, zsh, fish)
- Global options: `--verbose`, `--quiet`, `--config`, `--no-color`
- Custom exception hierarchy with exit codes (0=success, 1=error, 2=partial success)

#### Development Infrastructure
- Python 3.13+ support
- UV package management
- Ruff linting and formatting
- Ty type checking
- Pre-commit hooks
- Pytest test suite with >89% coverage
- Comprehensive unit, CLI, and integration tests
- GitHub Actions CI/CD pipeline
- Makefile for common development tasks

#### Documentation
- Complete specification in SPEC.md
- Development guide with architecture patterns
- Claude Code integration examples
- LLM workflow examples

### Dependencies
- click>=8.1 (CLI framework)
- pyyaml>=6.0 (config file parsing)
- pydantic>=2.10 (config validation)
- send2trash>=1.8 (system trash integration)
- python-dateutil>=2.9 (date parsing)
- python-frontmatter>=1.1.0 (frontmatter parsing)
- rich>=13.9 (terminal formatting)
- httpx>=0.28 (async HTTP client)
- beautifulsoup4>=4.12 (HTML parsing)
- trafilatura>=2.0 (content extraction)
- markdownify>=0.14 (HTML to markdown conversion)
- feedparser>=6.0 (RSS/Atom feed parsing)

### Optional Dependencies
- langdetect>=1.0 (language detection for `--include-stats`)

[Unreleased]: https://github.com/jmlrt/clipmd/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/jmlrt/clipmd/releases/tag/v0.1.0
