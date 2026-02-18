# Clipmd & Clipping-Triage Improvements

Issues and improvements identified during 2026-01-19 triage session.

**Goal**: Predictable process with only `clipmd` commands + basic shell (`ls`, `mv`), minimal token usage, no errors.

---

## Critical: Frontmatter Fixing Gaps

### Issue 1: Wikilinks in author field not fixed ✅ FIXED
**Observed**: 188 files had `author: - "[[Name]]"` format that breaks YAML parsing.
**Workaround**: Custom Python script to convert to `author: - "Name"`.
**Fix**: `clipmd preprocess` now auto-strips `[[Name]]` and `[[Page|Alias]]` syntax from any frontmatter field value via `fix_wikilinks()` in `core/frontmatter.py`.

### Issue 2: Unclosed quotes in URLs not fixed ✅ FIXED
**Observed**: 62 files had `source: "https://example.com` (missing closing quote).
**Workaround**: Custom Python script to add closing quotes.
**Fix**: `clipmd preprocess` now auto-repairs unclosed quotes via `fix_unclosed_quotes()` in `core/frontmatter.py`.

### Issue 3: Preprocess reports errors but continues
**Observed**: 63 frontmatter errors reported, but no clear guidance on how to fix them.
**Fix**: Add `--fix-errors` flag or interactive mode to attempt auto-repair of common issues.

---

## High: clipmd move Path Handling

### Issue 4: Confusing source directory behavior
**Observed**:
- Categorization with just filename → "File not found"
- Categorization with `Clippings/filename` → tries to move to `Folder/Clippings/filename`
- Required undocumented `--source-dir Clippings` flag

**Fix options**:
1. Auto-detect source directory from file paths in categorization file
2. Default `--source-dir` to `Clippings/` when running triage workflow
3. Better error message explaining the issue

**Command doc update**: Document `--source-dir` flag usage clearly.

**2026-02-18 update**: `clipmd move` worked without `--source-dir` using plain filenames in categorization.txt. May be resolved in current version — verify and close if confirmed.

**2026-02-18 verification**: Not resolved — `--source-dir` is still required when articles are in a subdirectory (e.g. `Clippings/`). The 2026-02-18 session likely had files at vault root (config.paths.root), so `source_dir` defaulted correctly. When files are in `Clippings/`, `--source-dir Clippings` is still needed. Issue remains open.

---

## High: clipmd stats Scope

### Issue 5: stats doesn't show Clippings subfolders ✅ FIXED
**Observed**: `clipmd stats` showed root-level directories (Personal-Tech, Inbox, etc.) not Clippings subfolders.
**Workaround**: Custom Python script to count files per Clippings subfolder.
**Fix**: `clipmd stats` now accepts an optional positional `PATH` argument to scope statistics to any subdirectory:
```bash
clipmd stats Clippings/  # Show Clippings subfolder stats
clipmd stats             # Show configured root stats
```

---

## Medium: Documentation File Handling

### Issue 6: Date prefixes added to README.md/CLAUDE.md
**Observed**: `clipmd preprocess` added date prefixes to documentation files.
**Workaround**: Manual `mv` to restore original names.
**Fix**: Exclude `README.md`, `CLAUDE.md`, and files without frontmatter from date prefixing.

### Issue 7: Extract includes documentation files
**Observed**: `clipmd extract` output included CLAUDE.md and README.md in "Needs Categorization".
**Fix**: Auto-exclude documentation files from extract output, or add `--exclude` pattern flag.

---

## Medium: Duplicate Handling

### Issue 8: Cross-folder duplicates not actionable
**Observed**: Duplicates reported between Clippings/ and Tech-Skills/ folders, but no automatic handling.
**Current**: Only removes duplicates within same scope (Clippings root).
**Fix**: Add `--scope all` to handle cross-folder duplicates with user confirmation.

---

## Low: Token/Efficiency Improvements

### Issue 9: Double preprocess run needed
**Observed**: After manual frontmatter fixes, had to re-run preprocess.
**Fix**: If `clipmd preprocess` could fix all frontmatter issues, single run would suffice.

### Issue 10: Manual Python scripts for stats
**Observed**: Used 15+ line Python script just to get folder counts.
**Fix**: `clipmd stats Clippings/` should handle this natively.

---

## Command Documentation Updates

### clipping-triage.md updates needed:

1. **Stage 1**: Add note about checking for frontmatter errors and how to handle them
2. **Stage 2**: Document that extract may include documentation files to skip
3. **Stage 3**: Document `--source-dir Clippings` requirement:
   ```bash
   clipmd move --source-dir Clippings categorization.txt
   ```
4. **Stage 4**: Explain that `clipmd stats` may not show Clippings subfolders correctly

### Add troubleshooting section:
```markdown
# Troubleshooting

**Frontmatter errors in preprocess output**:
- Common causes: wikilinks in fields, unclosed quotes
- Check specific files, fix manually, re-run preprocess

**"File not found" during move**:
- Use `--source-dir Clippings` flag
- Ensure categorization file has filenames only (no paths)

**Stats showing wrong folders**:
- clipmd stats may show root directories
- Use Python script or `ls` to count Clippings subfolders
```

---

---

## Phase 2+ Deferred Features

The following features were documented in the spec but deferred to Phase 2+ to keep Phase 1 focused on core triage workflow.

---

## Feature: Domain Rules System

**Status**: Removed from Phase 1 to keep scope focused. Can be implemented in Phase 2+ if needed.

**Concept**: Automatic pre-categorization of articles based on domain → category rules, with tools to discover and manage these rules.

### Planned Functionality

#### Domain Rules Infrastructure
- YAML-based rules file (`.clipmd/domain-rules.yaml`) mapping domains to categories
- Extract command `--apply-rules` flag to pre-categorize articles based on domain
- Config field `paths.rules` pointing to rules file location
- Validator check for rules file existence (optional)
- Output format showing "Pre-Assigned by Domain Rules" vs "Needs Categorization"

#### discover-rules Command
- Scan all categorized articles in vault
- Extract domain names from article sources/URLs
- Analyze which domains consistently appear in which folders
- Suggest high-confidence domain → category mappings
- Support `--min-articles` (minimum sample size) and `--min-confidence` thresholds
- Output rules in YAML format
- Support `--merge` to combine with existing rules
- Support `--dry-run` for preview before saving

### Why Phase 2+
- Phase 1 focus: Core triage workflow (preprocess → extract → move → stats)
- Domain rules are an optimization/enhancement, not required for initial use
- Manual categorization works well for initial use cases
- Allows more time to gather real-world usage patterns before designing rules format
- Can be added later without breaking existing functionality

### Implementation Notes (when implemented)
- Add `paths.rules` field to `PathsConfig` in `config.py`
- Core rules logic in `src/clipmd/core/rules.py`
- Discovery command in `src/clipmd/commands/discover.py`
- Add `--apply-rules` flag to extract command
- Add `category` and `rule_match` fields to `ArticleMetadata`
- Split `ExtractionResult.articles` into `pre_assigned` and `needs_categorization`
- Add `validate_rules_file()` to validator
- Update format_markdown/json/yaml to show pre-assigned vs needs categorization sections

---

## Feature: Report Command

**Status**: Deferred to Phase 2+

**Purpose**: Generate detailed reports with folder recommendations and domain coverage analysis.

### Planned Functionality

```bash
clipmd report [OPTIONS]

Options:
  --output, -o PATH     Output file (default: stdout)
  --format FORMAT       Output format: markdown, json
```

**Example Output (Markdown):**

```markdown
# Articles Report
Generated: 2024-01-17

## Statistics
- Total articles: 243
- Folders: 8
- Average per folder: 30

## Folder Details
| Folder | Count | Status |
|--------|-------|--------|
| AI-Tools | 45 | ⚠️ At max |
| Science | 32 | OK |
| Tech | 28 | OK |
| Misc | 8 | ⚠️ Below min |

## Recommendations
- Consider splitting AI-Tools/ (45 articles, above threshold)
- Consider merging Misc/ (8 articles) into another folder
- 5 folders within recommended range (10-45 articles)

## Domain Coverage (if domain rules enabled)
- 15 domains with rules (covering 89 articles)
- 42 domains without rules
- Top domains needing rules: medium.com (12), github.com (8)
```

### Implementation Notes

- Core logic in `src/clipmd/core/reporter.py`
- Command in `src/clipmd/commands/report.py`
- Leverage existing `stats.py` and `discovery.py` modules
- Output format similar to extract (markdown, json, yaml)
- Include folder recommendations based on thresholds
- Optional domain coverage section (requires domain rules)

---

## Feature: URLs Command

**Status**: Deferred to Phase 2+

**Purpose**: Extract and export all article URLs from vault.

### Planned Functionality

```bash
clipmd urls [OPTIONS]

Options:
  --output, -o PATH     Output file (default: stdout)
  --format FORMAT       Output format: markdown, json, csv, plain
  --include-removed     Include URLs marked as removed in cache
  --by-folder           Group URLs by folder
```

**Example Output (Plain):**

```
https://example.com/article-one
https://blog.example.com/post-two
https://news.example.com/story-three
```

**Example Output (JSON):**

```json
{
  "total": 234,
  "active": 198,
  "removed": 36,
  "urls": [
    {
      "url": "https://example.com/article-one",
      "filename": "20240115-Article-One.md",
      "folder": "AI-Tools",
      "removed": false
    }
  ]
}
```

**Example Output (CSV):**

```csv
url,filename,folder,removed
https://example.com/article-one,20240115-Article-One.md,AI-Tools,false
https://blog.example.com/post,20240116-Post.md,Science,false
```

### Implementation Notes

- Core logic in `src/clipmd/core/urls.py`
- Command in `src/clipmd/commands/urls.py`
- Read URLs from cache (fast) or scan files (slower but complete)
- Support filtering by folder
- Support including/excluding removed URLs
- Multiple output formats for different use cases

---

## Feature: Cache Management Commands

**Status**: Deferred to Phase 2+

**Purpose**: Inspect, maintain, and manage the URL/content cache.

### Planned Functionality

```bash
clipmd cache COMMAND [OPTIONS]

Commands:
  show                  Display cache statistics
  check URL             Check if URL exists in cache
  clean                 Remove entries for deleted files
  export                Export cache to JSON
  import FILE           Import cache from JSON
  clear                 Clear entire cache (with confirmation)
```

**Example: cache show**

```bash
clipmd cache show

Cache Statistics
================
Total entries: 234
  - Active: 198
  - Removed: 36

By folder:
  - AI-Tools: 45
  - Science: 32
  - Tech: 28
  - (removed): 36
  ...

Cache file: .clipmd/cache.json
Last updated: 2024-01-17T14:30:00
Size: 45.2 KB
```

**Example: cache check**

```bash
clipmd cache check "https://example.com/article"

✓ URL found in cache
  Filename: 20240115-Article.md
  Folder: AI-Tools
  First seen: 2024-01-15
  Last seen: 2024-01-17
  Status: Active
```

**Example: cache clean**

```bash
clipmd cache clean

Scanning for deleted files...
Found 12 entries for files that no longer exist.

Would remove:
  - https://old-article.com (file deleted)
  - https://another-old.com (file deleted)
  ...

Proceed? [y/N]: y

Removed 12 stale entries.
Cache updated.
```

**Example: cache export/import**

```bash
# Export cache for backup or migration
clipmd cache export --output backup-cache.json

# Import cache (merges with existing)
clipmd cache import backup-cache.json

# Clear cache (with confirmation)
clipmd cache clear
WARNING: This will delete all cache entries.
Type 'clear cache' to confirm: clear cache
Cache cleared.
```

### Implementation Notes

- Commands in `src/clipmd/commands/cache.py`
- Core logic already exists in `src/clipmd/core/cache.py`
- Add subcommands for show, check, clean, export, import, clear
- Use Click command groups for subcommands
- Require confirmation for destructive operations (clear)
- Export/import useful for migration or backup

---

## Feature: Content Cleaning Implementation

**Status**: Config exists, logic not implemented

**Purpose**: Remove unwanted patterns from article content (CTAs, social footers, etc.).

### Current State

Config structure exists in `config.py`:

```python
class ContentCleaningPatternConfig(BaseModel):
    name: str
    pattern: str
    flags: str = "im"

class ContentCleaningConfig(BaseModel):
    enabled: bool = False
    patterns: list[ContentCleaningPatternConfig] = Field(default_factory=list)
```

Users can already configure patterns in `config.yaml`:

```yaml
content_cleaning:
  enabled: false
  patterns:
    - name: "newsletter_cta"
      pattern: "^.*subscribe to (our|the) newsletter.*$"
      flags: "im"
```

### What's Missing

1. **Core module**: `src/clipmd/core/cleaner.py` - Apply regex patterns to content
2. **Integration**: Wire cleaner into `preprocessor.py` workflow
3. **Command flag**: Add `--no-content-clean` to preprocess command
4. **Stats tracking**: Track cleaned lines/sections in PreprocessStats

### Implementation Plan

When implementing:

1. Create `src/clipmd/core/cleaner.py`:
   ```python
   def clean_content(
       content: str,
       patterns: list[ContentCleaningPatternConfig]
   ) -> tuple[str, int]:
       """Apply cleaning patterns to content.

       Returns:
           Tuple of (cleaned_content, num_changes)
       """
   ```

2. Update `preprocessor.py` to call cleaner when enabled

3. Add stats to `PreprocessStats`:
   ```python
   content_cleaned: int = 0
   content_sections_removed: int = 0
   ```

4. Update preprocess command to report cleaning stats

5. Write tests for pattern matching edge cases

---

## Feature: Auto-Remove Duplicates Flag

**Status**: Deferred to Phase 2+

**Purpose**: Automatically move duplicate files to trash during preprocessing.

### Planned Functionality

```bash
clipmd preprocess --auto-remove-dupes
```

**Behavior:**

- Detect duplicates during preprocessing (already implemented)
- Instead of just reporting, automatically trash older duplicates
- Keep the newest version (by date prefix or file modification time)
- Update cache to mark URLs as removed
- Report actions taken in summary

**Example Output:**

```
Preprocessing Summary
=====================
Scanned: 89 files

Duplicates found and removed: 3
  ✓ Trashed: 20240115-Article.md (duplicate of 20240116-Article.md)
  ✓ Trashed: 20240114-Old-Post.md (duplicate of 20240115-Post.md)
  ✓ Trashed: duplicate-file.md (duplicate of original-file.md)

URL cleaning: ...
Filename sanitization: ...
```

### Implementation Notes

- Add `--auto-remove-dupes` flag to preprocess command
- During duplicate detection, if flag is set:
  1. Determine which file to keep (newest by date or mtime)
  2. Call trash.py to move duplicate to trash
  3. Update cache to mark URL as removed
  4. Track in stats (duplicates_removed count)
- Add confirmation prompt unless `--yes` flag is also provided
- Update preprocess summary formatter to show removed duplicates

---

## Feature: Custom Frontmatter Template Flag

**Status**: Deferred to Phase 2+

**Purpose**: Allow custom frontmatter templates when fetching URLs.

### Planned Functionality

```bash
clipmd fetch --template my-template.yaml "https://example.com/article"
```

**Template File Format (my-template.yaml):**

```yaml
title: "{title}"
url: "{url}"
date_saved: "{clipped}"
tags: []
status: unread
custom_field: "Custom value"
```

**Available Variables:**

- `{title}` - Extracted article title
- `{url}` - Source URL (cleaned)
- `{author}` - Extracted author
- `{published}` - Extracted publish date
- `{clipped}` - Current date/time
- `{description}` - Extracted description
- `{domain}` - Domain name from URL

### Implementation Notes

- Add `--template PATH` flag to fetch command
- Core logic in `fetcher.py`:
  ```python
  def apply_template(
      template: str,
      metadata: FetchedMetadata
  ) -> str:
      """Apply custom template with variable substitution."""
  ```
- Load template file, validate it's valid YAML
- Substitute variables using extracted metadata
- Fall back to config template if custom template fails
- Use same frontmatter serialization as default flow

---

---

## Issues from 2026-02-18 Session

### Issue 11: `fetch --file` truncates tracking URLs with embedded `<>` (HIGH) ✅ FIXED

**Observed**: Newsletter tracking URLs (La Quotidienne via `sgdbs6pn.r.eu-west-1.awstrack.me`, TLDR via `tracking.tldrnewsletter.com`) embed a second `https://` inside the tracking path. Email auto-linking wraps the inner domain with `<>`, producing:
```
<https://tracker.com/L0/https>:%2F%2F<www.example.com>%2Fpath
```
`clipmd fetch --file` parses angle-bracket links and stops at the first `>`, sending only `https://tracker.com/L0/https` to the fetcher → HTTP 400.

**Workaround**: Strip all `<>` with `tr -d '<>'` before passing URLs to clipmd (done in clipping-triage.md).

**Fix**: In `fetch --file` URL parsing, when stripping angle-bracket link syntax (`<url>`), strip **all** `<>` characters from the extracted URL string — not just the first `<` and last `>`.

---

### Issue 12: `fetch` should auto-recover recoverable tracking URL failures (MEDIUM)

**Observed**: When `fetch` reports `✗ HTTP 400` on a truncated tracking URL ending in `/L0/https` or `/CL0/https`, the destination URL is still recoverable by URL-decoding the path. Currently, recovery requires a manual Python script and separate `clipmd fetch` invocation.

**Workaround**: Manual Python script to extract destination + refetch (documented in clipping-triage.md).

**Fix**: After a fetch failure, if the failed URL matches a known tracking URL pattern (`/L0/` or `/CL0/` with URL-encoded destination), auto-extract the destination URL, retry the fetch, and report the recovery in output:
```
✗ https://tracker.com/L0/https: HTTP 400
  ↳ Detected truncated tracking URL — retrying destination...
  ✓ https://www.actual-article.com/path (recovered)
```

---

### Issue 13: `fetch` saves JS-disabled stub for x.com / Twitter URLs (LOW)

**Observed**: `clipmd fetch "https://x.com/user/status/..."` fetches the page but gets only the JavaScript-disabled stub ("Please enable JavaScript..."). The result is saved as a valid-looking `.md` file with `title: Untitled` and no content.

**Fix**: Detect stub content (heuristic: body contains "JavaScript is disabled" or "enable JavaScript", content under ~200 chars) and either:
1. Skip saving with a clear `✗ x.com: JavaScript-gated page, manual paste required` message
2. Or save with a `status: requires-manual-content` frontmatter field and a clear warning in output

---

### Issue 14: `move` silently creates new folder for typos in categorization.txt (HIGH) ✅ FIXED

**Observed**: When `categorization.txt` contains a typo like `Lifr-Tips` (instead of `Life-Tips`), `clipmd move` creates a new `Lifr-Tips/` folder and moves the article there silently. The article is misplaced with no warning.

**Fix**: Before creating a new folder, check if any existing folder name has a Levenshtein distance ≤ 2 from the new name. If so, warn and prompt for confirmation:
```
⚠️  About to create new folder: Lifr-Tips/
   Similar existing folder found: Life-Tips/
   Did you mean Life-Tips/? [Y/n/create-anyway]:
```

---

### Issue 15: RSS feed failure aborts remaining feeds (MEDIUM)

**Observed**: If one RSS feed fails (network error, invalid feed URL, malformed XML), `clipmd fetch --rss` exits immediately without processing subsequent feeds configured in the same session.

**Fix**: RSS feed failures should be non-blocking. Process all configured feeds, collect errors, and report at the end:
```
✗ https://broken-feed.com/rss.xml: Connection timeout
✓ https://simonwillison.net/atom/everything/ — 10 saved

Summary: 1 feed failed, 1 feed succeeded
```

---

### Feature: Auto-detect RSS feeds in Inbox files (MEDIUM)

**Context**: When `clipmd fetch --file` processes an Inbox daily note, it currently treats every URL as an article to fetch. Some URLs may be RSS/Atom feed URLs (e.g. `https://example.com/rss.xml`, `https://blog.example.com/atom/`).

**Desired behavior**:
1. During `fetch --file`, detect URLs that are RSS/Atom feeds (by content-type `application/rss+xml` / `application/atom+xml`, or common path heuristics like `/rss`, `/rss.xml`, `/atom`, `/feed`, `/feed.xml`)
2. Instead of trying to save the feed XML as an article, treat it as a feed and fetch its articles (same as `--rss`)
3. After processing, propose adding the feed to the default RSS list in `config.yaml`:
```
ℹ️  https://example.com/rss.xml looks like an RSS feed (10 articles fetched)
   Add to default RSS feeds in config? [y/N]:
```

**Additional benefit**: Prevents the current failure mode where feed XML gets saved as a garbled `.md` article.

**Implementation notes**:
- HEAD request first to check content-type before downloading
- Fallback: try parsing as RSS/Atom if content-type is ambiguous
- Config update: append to `fetch.rss_feeds` list in `config.yaml`
- Should work for both `fetch --file` and bare `fetch <url>`

---

## Proposed clipmd Enhancements Summary

| Priority | Enhancement | Effort | Session |
|----------|-------------|--------|---------|
| Critical | Fix wikilinks in frontmatter | Medium | 2026-01-19 |
| Critical | Fix unclosed quotes in frontmatter | Low | 2026-01-19 |
| High | Auto-detect source-dir in move | Medium | 2026-01-19 |
| High | Add path argument to stats | Low | 2026-01-19 |
| High | `fetch --file` strips embedded `<>` from tracking URLs | Low | 2026-02-18 |
| High | `move` warns on folder name typos (fuzzy match) | Medium | 2026-02-18 |
| Medium | Exclude documentation files | Low | 2026-01-19 |
| Medium | Better error messages | Low | 2026-01-19 |
| Medium | `fetch` auto-recovers truncated tracking URLs | Medium | 2026-02-18 |
| Medium | RSS feed failures non-blocking | Low | 2026-02-18 |
| Low | Cross-folder duplicate handling | High | 2026-01-19 |
| Low | `fetch` detects JS-gated pages (x.com) | Low | 2026-02-18 |
| Medium | `fetch --file` auto-detects RSS feeds, proposes adding to config | Medium | 2026-02-18 |

---

## Ideal Workflow (After Fixes)

```bash
# Stage 1: Preprocess (handles ALL frontmatter issues)
clipmd preprocess --auto-remove-dupes

# Stage 2: Extract & Categorize
clipmd extract --apply-rules --folders > metadata.txt
# Claude categorizes, writes categorization.txt

# Stage 3: Move (auto-detects source from file paths)
clipmd move categorization.txt

# Stage 4: Report (scoped to Clippings)
clipmd stats Clippings/
```

No Python scripts, no manual fixes, no path confusion.

---

## Core Module Refactoring Opportunities

**Status**: Identified during Phase 1 (fetcher.py refactoring, completed 2026-02-14)

**Context**: After successfully refactoring fetcher.py from 986→561 lines by extracting 4 new modules (filepath_utils, url_utils, rss, formatters), additional refactoring opportunities were identified across other core modules.

---

### High Priority: Consolidate Formatting Functions (~400 lines)

**Issue**: 13+ format_* functions scattered across 7 different modules, leading to:
- Inconsistent output styling
- Duplicated formatting logic
- Difficult to maintain consistent CLI output

**Affected Modules**:
- `preprocessor.py`: `format_preprocess_summary()`
- `extractor.py`: `format_markdown()`, `format_json()`, `format_yaml_output()`
- `stats.py`: `format_stats_table()`, `format_stats_json()`, `format_stats_yaml()`
- `mover.py`: `format_move_results()`
- `duplicates.py`: `format_duplicates_markdown()`, `format_duplicates_json()`
- `fetcher.py`: ✅ Already moved to formatters.py

**Solution**: Expand `formatters.py` to include all output formatting functions
- Create command-specific formatters (e.g., `format_preprocess_output()`, `format_stats_output()`)
- Share common formatting utilities (tables, JSON, YAML serialization)
- Enable consistent styling across all commands

**Impact**: ~400 lines consolidated, easier testing, consistent output

---

### High Priority: Extract Cache Operation Helpers (~100 lines)

**Issue**: Cache update logic duplicated in 3 modules with similar patterns:
- `mover.py`: `_update_cache_after_moves()` (48 lines)
- `trash.py`: `_update_cache_after_trash()` (23 lines)
- `fetcher.py`: ✅ Already moved to cache.py (`update_cache_after_fetch()`)

**Solution**: Add helper functions to `cache.py`:
```python
def mark_file_as_trashed(path: Path, config: Config) -> None
    """Mark file as removed in cache."""

def update_file_location(old_path: Path, new_folder: str, config: Config) -> None
    """Update file location in cache after move."""

def record_fetched_article(path: Path, url: str, config: Config) -> None
    """Record newly fetched article in cache."""
```

**Impact**: ~100 lines of duplicated logic consolidated

---

### Medium Priority: Extract Initializer Config Template

**Issue**: `initializer.py` has 181-line `get_full_config()` function returning static string (pure data masquerading as code)

**Current State** (initializer.py):
```python
def get_full_config() -> str:
    """Return full example config YAML."""
    return '''version: 1
paths:
  root: .
  ...
# (175 more lines of YAML string)
'''
```

**Solution**: Create `src/clipmd/config-template.yaml` and load from file:
```python
def get_full_config() -> str:
    """Load config template from file."""
    template_path = Path(__file__).parent.parent / "config-template.yaml"
    return template_path.read_text()
```

**Impact**: Reduces initializer.py from 269→~80 lines, separates data from code, easier to edit template

---

### Medium Priority: Move find_duplicates() to duplicates.py

**Issue**: `preprocessor.py` has `find_duplicates()` (43 lines) that belongs in duplicates.py

**Current**: Function is in preprocessor because it's called during preprocessing
**Better**: Move to duplicates module and import it in preprocessor

**Solution**:
1. Move `find_duplicates()` to `duplicates.py` as `find_duplicates_in_batch()`
2. Import in preprocessor: `from clipmd.core.duplicates import find_duplicates_in_batch`

**Impact**: Improves module cohesion, duplicates.py becomes single source for duplicate detection

---

### Low Priority: Consolidate Validation Config Loading (~30 lines)

**Issue**: `validator.py` has 5 functions that each independently load config with same pattern

**Functions with duplicated loading**:
- `validate_paths()`
- `validate_cache()`
- `validate_frontmatter_fields()`
- `validate_filename_config()`
- `validate_url_cleaning()`

**Solution**: Extract helper function:
```python
def _get_or_load_config(config_path: Path | None = None) -> Config:
    """Load config or return default."""
    if config_path:
        return load_config(config_path)
    return load_config(find_config())
```

**Impact**: Removes ~30 lines of duplication, simplifies validator functions

---

### Low Priority: Create path_utils.py for Filesystem Utilities

**Issue**: Small utility functions scattered across modules:
- `trash.py`: `expand_glob_patterns()` (42 lines) - Generic path glob expansion
- `discovery.py`: File filtering helpers

**Solution**: Create `core/path_utils.py` for filesystem utilities:
- `expand_glob_patterns()` - Expand glob patterns to file paths
- `get_relative_path()` - Get relative path from root
- `ensure_directory_exists()` - Create directory if missing

**Impact**: Improves code organization, reusable utilities

---

## Module Health Summary

Analysis of all 14 core modules (excluding fetcher.py which was refactored):

| Module | Lines | Refactor Priority | Issues |
|--------|-------|-------------------|--------|
| **initializer.py** | 269 | High | 181-line static YAML string |
| **preprocessor.py** | 385 | High | format_preprocess_summary(), find_duplicates() misplaced |
| **validator.py** | 309 | High | 5 functions with duplicated config loading |
| **extractor.py** | 373 | Medium | 3 format_* functions should move to formatters.py |
| **mover.py** | 406 | Medium | format_move_results() + _update_cache_after_moves() |
| **stats.py** | 203 | Medium | 3 format_* functions should move to formatters.py |
| **duplicates.py** | 207 | Medium | 2 format_* functions + missing find_duplicates() |
| **sanitizer.py** | 172 | Low | ✅ Well-structured (enhanced in Phase 1) |
| **dates.py** | 279 | Low | Complex but focused, no immediate issues |
| **trash.py** | 167 | Low | expand_glob_patterns() should move to path_utils |
| **frontmatter.py** | 339 | Low | ✅ Well-structured (enhanced in Phase 1) |
| **cache.py** | 404 | Low | ✅ Well-structured (enhanced in Phase 1) |
| **discovery.py** | 110 | Very Low | ✅ Well-designed, focused module |
| **hasher.py** | 36 | Very Low | ✅ Perfect as-is |

**Total analyzed**: 3,660 lines across 14 modules (excluding fetcher.py)

---

## Refactoring Implementation Roadmap

### ✅ Phase 1: Fetcher.py Refactoring (COMPLETE - 2026-02-14)
**Result**: 986 → 561 lines, created 4 new modules, enhanced 3 existing modules
**Impact**: Proven clean architecture pattern for CLI tools

### Phase 2: High-Priority Cross-Module Cleanup (FUTURE)
**Estimated Timeline**: 3-4 hours
1. Consolidate all formatting functions into formatters.py (~400 lines)
2. Extract cache operation helpers to cache.py (~100 lines)
3. Extract initializer config template to YAML (181 lines → ~80 lines)
4. Move find_duplicates() to duplicates.py (43 lines)

**Estimated Impact**: ~600 lines consolidated or relocated

### Phase 3: Medium-Priority Optimizations (FUTURE)
**Estimated Timeline**: 2-3 hours
1. Consolidate validator config loading patterns (~30 lines)
2. Create path_utils.py for scattered helpers (~50 lines)
3. Refactor large complex functions (internal to modules)

**Estimated Impact**: Improved maintainability, reduced duplication

---

## Decision Rationale

**Why Phase 1 focused on fetcher.py first**:
1. **Size**: At 986 lines, it was 2.7x larger than next biggest module
2. **Urgency**: Served 9+ responsibilities (highest SRP violation)
3. **Impact**: Created reusable modules that Phase 2 can leverage
4. **Foundation**: formatters.py established pattern for Phase 2

**Why defer Phase 2+**:
- Phase 1 proves the refactoring pattern works
- Each phase is independent and can be done incrementally
- No blocking issues - current code is functional
- Can evaluate priorities based on actual development needs
