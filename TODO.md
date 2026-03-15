# TODO

Known issues, planned features, and improvements for `clipmd`.

---

## Bug Fixes

### duplicates: cross-folder duplicates not actionable

**Priority**: Low (reorganization workflow only)

`clipmd duplicates` detects duplicates between folders but only removes
duplicates within the same directory scope. Cross-folder duplicates are
reported but cannot be resolved automatically.

**Note**: Not applicable to standard triage workflow. The `preprocess --auto-remove-dupes`
flag already handles root-level duplicates. This affects vault reorganization/cleanup.

**Proposed fix**: Add `--scope all` flag to enable cross-folder duplicate
resolution with user confirmation.

---

### fetch: Cache doesn't prevent re-fetch of manually removed files

**Priority**: CRITICAL (causes data duplication despite working cache)

When a user manually removes a file from disk, the cache correctly marks it as
`removed: true` with a timestamp. However, when the same URL is fetched again,
clipmd ignores the "removed" status and re-fetches the article, creating a
new file.

**Observed behavior** (2026-03-15):
- URL in cache: `removed: true, removed_at: 2026-03-15T07:22:09`
- Same URL in next fetch: Not skipped, fetched and recreated
- Result: File brought back to life with new clipped date

**Root cause**: `clipmd fetch` checks URL cache but doesn't consult the
`removed` flag. It only checks if the file exists on disk, not if it was
intentionally deleted.

**Impact**: Users can't prevent re-fetch of articles they've deliberately
removed. The only way to stop re-fetching is to clean up INBOX.md (which is
broken due to --clear-after bug).

**Proposed fix**:
When `fetch` encounters a URL in cache with `removed: true`:
1. Skip the fetch (don't recreate the file)
2. Report: "Skipping (already removed): <URL>"
3. Optional: Allow `--force-refetch` flag to override if needed

---

### fetch: Log warning for JavaScript-gated pages

**Priority**: Low

`clipmd fetch` on JavaScript-gated pages (e.g. `x.com`) fetches the
JS-disabled stub and saves it as a valid-looking `.md` file with
`title: Untitled` and no content. User doesn't know they need to add content manually.

**Proposed fix**: Detect stub content (heuristic: content under ~200 chars after extraction)
and log a warning: `"Saved but may require manual content: <filename>"`. File is still saved,
but user is flagged to verify content manually.

---

### extract: skip files without frontmatter

**Priority**: CRITICAL (needed for unattended triage workflow)

`clipmd extract` includes all `.md` files in its "Needs Categorization" list, including
documentation files like `README.md`, `CLAUDE.md`, and other non-article files. This
pollutes the LLM prompt with non-article content.

**Impact on unattended workflow**: Without filtering, the LLM has to process and skip
documentation files, wasting tokens and adding cognitive noise to categorization decisions.

**Proposed fix**: One of:

1. **Option A**: Add `--exclude GLOB` flag (preferred for flexibility):
   ```bash
   clipmd extract ./Clippings/ --exclude '*.md' --exclude 'README*' --exclude '.*'
   ```

2. **Option B**: Auto-detect based on frontmatter (simple but requires parsing first):
   - Skip files that fail to parse or have no frontmatter
   - Report skipped files in verbose/debug output

**Recommendation**: Option A (glob patterns) is more explicit and faster.

---

### fetch: `--clear-after` aborts entire operation on partial failures

**Priority**: HIGH (confirmed data duplication in production)

When `clipmd fetch --file INBOX.md --clear-after` encounters ANY fetch
failure (e.g., one URL fails to save out of 30), the entire clear
operation is aborted to prevent data loss. This leaves all URLs in the
file, even though most fetched successfully, requiring manual cleanup.

**Current behavior** (conservative, safe):
- If ANY URL fails to fetch → abort clear → preserve entire file for retry
- Result: User must manually clear or re-add only failed URL(s)

**Observed issue**:
- 29 of 30 URLs saved successfully
- 1 failed (Obsidian iOS help page)
- All 30 remained in INBOX.md after fetch completed

**Proposed fix** (Option A): Improve `--clear-after` to handle partial failures gracefully:

1. Clear all successfully-fetched URLs from the file
2. Preserve failed URLs with `[KO]` prefix to flag them for investigation
3. This ensures users can see at a glance which URLs need attention

**Example behavior**:

```
# INBOX.md before clipping triage
https://url-ok-1
https://url-ok-2
https://url-failing-1
https://url-ok-3
https://url-failing-2

# INBOX.md after clipping triage (with --clear-after)
[KO] https://url-failing-1
[KO] https://url-failing-2
```

**Benefits**:
- Balances safety with usability
- Failed URLs are clearly visible and flagged for retry
- No manual cleanup needed; users can immediately see next steps
- Fetch summary in stdout also reports which URLs failed

**Implementation note**:
- Must maintain atomicity: either fully process the file or preserve all
- `[KO]` prefix allows easy grep/filtering: `grep "^\[KO\]" INBOX.md`
- Requires careful testing to ensure no partial failures from crashes

---

## Features

### extract: `--format json` and move: `--from-json`

**Priority**: CRITICAL (essential for unattended triage workflow)

**Needed for**: Full automation of triage workflow without manual filename parsing

The unattended triage round-trip requires robust I/O between clipmd and LLM:

1. **extract** produces article metadata (currently text format with truncated filenames)
2. **LLM categorizes** articles and produces categorization decisions
3. **move** processes decisions and reorganizes files

**Current limitation**: Text format requires filename matching and parsing, which is
fragile when filenames are truncated or have special characters.

**Proposed solution**: Add JSON I/O mode for schema-constrained round-trip:

```bash
# Extract to JSON with full filenames
clipmd extract /path/to/Clippings/ --format json > articles.json

# Claude reads articles.json, outputs categorization.json:
# [{"file": "exact-full-filename.md", "folder": "Dev-Tools"}, ...]

# Move from JSON (exact filename matching, no parsing)
clipmd move --from-json /path/categorization.json
```

**Benefits for unattended workflow**:
- Full filenames preserved (no truncation in LLM prompt)
- Schema-constrained output (LLM can't produce malformed decisions)
- Eliminates fragile text parsing in move command
- Enables fully automated workflows without manual intervention

**Implementation note**: The existing plain-text format remains the default;
`--format json` is opt-in. Both formats coexist for backward compatibility.

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

### Filename sanitization: transliterate accented characters to base letters

**Priority**: Medium (affects filename consistency and cache matching)

**Issue**: When filenames contain accented characters (é, è, ê, ë, ç, ö, etc.),
the current sanitization produces inconsistent results. The cache may store one
version of the filename while the filesystem has another, causing:
- Cache lookup failures (can't match files by name)
- User confusion when looking for files
- Filename truncation as a workaround

**Current behavior**:
- `Inspiré` → `Inspir` (truncated, diacritics stripped)
- `Pétrole` → `P-trole` (diacritics garbled)
- `Yaël` → `Ya-l` (inconsistent)

**Proposed behavior**:
- `Inspiré` → `Inspire` (transliterate é → e)
- `Pétrole` → `Petrole` (transliterate é → e)
- `Yaël` → `Yael` (transliterate ë → e)
- `Cést` → `Cest` (transliterate é → e)
- `Français` → `Francais` (transliterate ç → c)

**Implementation**:
Use Unicode NFKD decomposition or `unidecode` library to convert accented
characters to their base equivalents:
```python
import unicodedata
def remove_accents(text):
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )
```

**Benefits**:
- Consistent filenames across fetch and cache
- Better file discoverability
- Fixes cache lookup issues when matching by URL
- More readable filenames for users
- Prevents filename truncation

**Related**: Fixes cache matching issue discovered 2026-03-15 where accented
filenames in cache didn't match on-disk files due to inconsistent sanitization.
