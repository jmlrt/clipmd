# TODO

Known issues, planned features, and improvements for `clipmd`.

---

## Bug Fixes

### preprocess: error output lacks actionable guidance

**Priority**: Medium

When `clipmd preprocess` reports frontmatter validation errors, the output lists
the affected files but provides no guidance on how to fix them.

**Proposed fix**: Add `--fix-errors` flag or interactive mode to attempt
auto-repair of remaining common frontmatter issues beyond the current automatic
fixes (multiline wikilinks, single-line wikilinks, unclosed quotes, unquoted
colons).

---

### move: `--source-dir` required for subdirectory workflows

**Priority**: High

When articles are stored in a subdirectory (e.g. `Inbox/`) rather than at
the vault root, `clipmd move` defaults `source_dir` to `config.paths.root`
and reports "File not found" for every entry. Users must remember to pass
`--source-dir Inbox`.

**Proposed fixes**:
1. Auto-detect source directory from file paths in the categorization file
2. Emit a helpful error message suggesting `--source-dir` when files are not
   found at the configured root

---

### preprocess: date prefixes added to non-article files

**Priority**: Medium

`clipmd preprocess` adds date prefixes to files without frontmatter (e.g.
`README.md`, `CLAUDE.md`) when they share the same directory as articles.

**Proposed fix**: Skip date-prefixing for files that have no YAML frontmatter,
or add an `--exclude` glob pattern option.

---

### extract: documentation files appear in output

**Priority**: Medium

`clipmd extract` includes documentation files (e.g. `README.md`, `CLAUDE.md`)
in its "Needs Categorization" list, polluting the LLM prompt.

**Proposed fix**: Auto-exclude files without frontmatter from extract output,
or add an `--exclude` glob pattern option.

---

### duplicates: cross-folder duplicates not actionable

**Priority**: Medium

`clipmd duplicates` detects duplicates between folders but only removes
duplicates within the same directory scope. Cross-folder duplicates are
reported but cannot be resolved automatically.

**Proposed fix**: Add `--scope all` flag to enable cross-folder duplicate
resolution with user confirmation.

---

### fetch: truncated tracking URLs not automatically recovered

**Priority**: Medium

When `clipmd fetch` reports an HTTP 400 error on a truncated tracking URL
(ending in `/L0/https` or `/CL0/https`), the actual destination URL is still
URL-encoded in the path and recoverable. Currently the user must extract and
re-fetch manually.

**Proposed fix**: After a fetch failure, detect known tracking URL patterns
and auto-retry the decoded destination URL:

```
✗ https://tracker.example.com/L0/https: HTTP 400
  ↳ Detected truncated tracking URL — retrying destination...
  ✓ https://www.example.com/article (recovered)
```

---

### fetch: JavaScript-gated pages saved as empty stubs

**Priority**: Low

`clipmd fetch` on JavaScript-gated pages (e.g. `x.com`) fetches the
JS-disabled stub and saves it as a valid-looking `.md` file with
`title: Untitled` and no content.

**Proposed fix**: Detect stub content (heuristic: body contains
"JavaScript is disabled" or content under ~200 chars) and either:
1. Skip saving with a clear error message
2. Save with `status: requires-manual-content` frontmatter and a warning

---

### fetch: RSS feed failure aborts all remaining feeds

**Priority**: Medium

When one RSS feed fails (network error, invalid URL, malformed XML),
`clipmd fetch --rss` exits immediately and does not process remaining feeds.

**Proposed fix**: Make RSS feed failures non-blocking — process all feeds,
collect errors, and report at the end:

```
✗ https://broken-feed.example.com/rss: Connection timeout
✓ https://example.com/atom/everything/ — 10 saved

Summary: 1 feed failed, 1 feed succeeded
```

---

## Features

### preprocess: auto-remove duplicates flag

**Priority**: Medium

Add `--auto-remove-dupes` flag to `clipmd preprocess` to automatically trash
older duplicates detected during preprocessing instead of just reporting them.

**Behavior**:
- Keep the newest version (by date prefix or file modification time)
- Update cache to mark URLs as removed
- Report actions taken in summary
- Require `--yes` to skip confirmation prompt

---

### fetch: auto-detect RSS feeds in URL files

**Priority**: Medium

When `clipmd fetch --file` processes a URL list, some entries may be
RSS/Atom feed URLs. Currently they are fetched as HTML articles, resulting
in garbled output or errors.

**Proposed behavior**:
1. Detect feed URLs by content-type (`application/rss+xml`,
   `application/atom+xml`) or common path patterns (`/rss`, `/rss.xml`,
   `/atom`, `/feed`, `/feed.xml`)
2. Treat detected feeds as `--rss` sources and fetch their articles
3. Offer to add the feed to `fetch.rss_feeds` in `config.yaml`:

```
ℹ️  https://example.com/rss.xml looks like an RSS feed (10 articles fetched)
   Add to default RSS feeds in config? [y/N]:
```

---

### fetch: custom frontmatter template

**Priority**: Low

Add `--template PATH` flag to `clipmd fetch` to allow custom frontmatter
structure when saving articles.

**Template file format (`my-template.yaml`)**:

```yaml
title: "{title}"
url: "{url}"
date_saved: "{clipped}"
tags: []
status: unread
```

**Available variables**: `{title}`, `{url}`, `{author}`, `{published}`,
`{clipped}`, `{description}`, `{domain}`

---

### stats/report: report command

**Priority**: Low

Add a `clipmd report` command that generates a structured summary with folder
recommendations.

```bash
clipmd report [--output PATH] [--format markdown|json]
```

**Example output**:

```markdown
# Articles Report

## Statistics
- Total articles: 243
- Folders: 8

## Folder Details
| Folder    | Count | Status       |
|-----------|-------|--------------|
| AI-Tools  | 45    | ⚠️ At max   |
| Science   | 32    | OK           |
| Misc      | 8     | ⚠️ Below min |

## Recommendations
- Consider splitting AI-Tools/ (45 articles, above threshold)
- Consider merging Misc/ (8 articles) into another folder
```

---

### domain rules system

**Priority**: Low (Phase 2+)

Automatic pre-categorization of articles based on domain → category rules.

**Components**:
- YAML-based rules file (`.clipmd/domain-rules.yaml`)
- `extract --apply-rules` flag to pre-categorize before LLM prompt
- `discover-rules` command to suggest rules from existing vault structure

**`discover-rules` behavior**:
- Scan categorized articles, extract source domains
- Identify domains that consistently appear in the same folder
- Suggest high-confidence mappings; output in YAML format
- Support `--min-articles`, `--min-confidence`, `--merge`, `--dry-run`

---

### cache management commands

**Priority**: Low (Phase 2+)

Subcommands to inspect and maintain the URL cache.

```bash
clipmd cache show     # Display cache statistics
clipmd cache check URL
clipmd cache clean    # Remove entries for deleted files
clipmd cache export [--output PATH]
clipmd cache import FILE
clipmd cache clear
```

---

### URLs export command

**Priority**: Low (Phase 2+)

Export all article URLs from the vault.

```bash
clipmd urls [--output PATH] [--format markdown|json|csv|plain]
            [--include-removed] [--by-folder]
```

---

## Refactoring

### Consolidate formatting functions

**Priority**: Medium

13+ `format_*` functions are scattered across 7 modules
(`preprocessor.py`, `extractor.py`, `stats.py`, `mover.py`,
`duplicates.py`). `fetcher.py` already has its formatters in
`core/formatters.py`.

**Proposed**: Move all output formatting into `core/formatters.py` to
ensure consistent styling and easier testing (~400 lines consolidated).

---

### Extract cache operation helpers

**Priority**: Medium

Cache update logic is duplicated in `mover.py`
(`_update_cache_after_moves`) and `trash.py`
(`_update_cache_after_trash`). `fetcher.py` already delegates to
`cache.update_cache_after_fetch()`.

**Proposed**: Add `mark_file_as_trashed()` and `update_file_location()`
helpers to `core/cache.py` (~100 lines of duplication removed).

---

### Move config template out of `initializer.py`

**Priority**: Medium

`initializer.py` contains a 181-line `get_full_config()` function that
returns a static YAML string — data masquerading as code.

**Proposed**: Extract to `src/clipmd/config-template.yaml` and load from
file, reducing `initializer.py` from ~270 to ~80 lines.

---

### Move `find_duplicates()` to `duplicates.py`

**Priority**: Low

`preprocessor.py` contains a `find_duplicates()` function (43 lines) that
belongs in `core/duplicates.py`.

---

### Extract shared validator config loading

**Priority**: Low

Five functions in `validator.py` independently load config with the same
pattern. Extract a `_get_or_load_config()` helper to remove ~30 lines of
duplication.

---

### Create `core/path_utils.py`

**Priority**: Low

Small filesystem utility functions are scattered across modules
(`trash.py` has `expand_glob_patterns()`; `discovery.py` has file
filtering helpers). Consolidate into a dedicated `core/path_utils.py`
module.
