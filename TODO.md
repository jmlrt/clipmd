# TODO

Known issues, planned features, and improvements for `clipmd`.

---

## Bug Fixes

### move: `--source-dir` not auto-detected

**Priority**: Medium

When articles are stored in a subdirectory (e.g. `Inbox/`), `clipmd move`
now hints at the correct `--source-dir` value, but users still need to
re-run with the flag explicitly.

**Proposed fix**: Auto-detect source directory from file paths in the
categorization file so users never need to pass `--source-dir` manually.

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

**Needed for**: Unattended triage workflow (prevents garbage in LLM prompt)

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

## Features

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

### extract: `--format json` and move: `--from-json`

**Priority**: Low

**Needed for**: Unattended triage workflow (eliminates filename-matching fragility)

The current triage round-trip (extract → Claude categorizes → move) uses
free-text formats in both directions:
- `clipmd extract` outputs human-readable text with truncated filenames
- Claude writes a numbered plain-text `categorization.txt`
- `clipmd move` parses that text

This creates a fragile pipeline: filename truncation, formatting edge cases,
and parsing assumptions can all silently produce wrong results.

**Proposed**: Add JSON I/O mode for the extract → categorize → move pipeline:

```bash
# Extract to JSON
clipmd extract /path/to/Clippings/ --format json > articles.json

# Claude reads articles.json, writes categorization.json:
# [{"file": "exact-filename.md", "folder": "Geek"}, ...]

# Move from JSON
clipmd move --from-json /path/categorization.json
```

**Benefits**:
- Filenames are never truncated (JSON string field, no display limit)
- No parsing ambiguity in either direction
- Easy to validate structure before executing move
- Claude output is schema-constrained, reducing categorization errors

**Implementation note**: The existing plain-text format should remain the
default; `--format json` is opt-in to avoid breaking existing workflows.

---

## Configuration Improvements (Deferred from PR #7)

These items were identified during config refactoring (PR #7) but deferred
to avoid scope creep. They require careful handling and comprehensive testing.

### Relative cache path normalization

**Priority**: Medium

**Issue**: `model_post_init()` in `Config` expands environment variables but
does not resolve relative `cache` paths against the `vault` path. This means
a relative path like `cache: .clipmd/cache.json` is resolved against the
current working directory, not the vault root — potentially placing the cache
in the wrong location when running commands outside the vault directory.

**Proposed fix**: After expanding env vars, resolve relative `cache` paths
against `vault` if both are configured. Alternatively, enforce that
`cache` must be absolute and raise `ConfigError` otherwise.

**Recommendation**: Separate PR with integration tests to verify cache
location correctness under different working directories.

### Test fixture isolation

**Priority**: Medium

**Issue**: The `conftest.py` fixture `default_config` writes a config with
relative paths (`cache: .clipmd/cache.json`). Tests that don't call
`monkeypatch.chdir(tmp_path)` may resolve these paths against the repo root
instead of the test directory, causing test order/environment dependencies
and potential cache pollution.

**Proposed fix**: Use absolute paths in fixtures or ensure all test functions
that use the fixture also call `monkeypatch.chdir(tmp_path)`.

**Recommendation**: Refactor fixture in dedicated PR, audit all tests that
depend on it.

### Config loading behavior with missing vault/cache

**Priority**: Low

**Issue**: `load_config()` returns a default `Config()` with `vault=None` and
`cache=None` when the canonical config file is missing. Commands later assert
that these are configured, which now raises clear errors. This is safe but
means the "fail-fast" error message only appears at the command level, not
during config loading.

**Proposed fix**: Consider raising `ConfigError` when the config file is
missing but certain commands require it. Alternatively, add an explicit
"allow_missing=True" mode for commands like `validate` that should work
without a config.

**Recommendation**: Address in config validation enhancement PR after
gathering feedback from user workflows.

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
