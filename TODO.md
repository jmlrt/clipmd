# TODO

Known issues, planned features, and improvements for `clipmd`.

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

## Bug Fixes

### fetch: Log warning for JavaScript-gated pages

**Priority**: Low

`clipmd fetch` on JavaScript-gated pages (e.g. `x.com`) fetches the
JS-disabled stub and saves it as a valid-looking `.md` file with
`title: Untitled` and no content. User doesn't know they need to add content manually.

**Proposed fix**: Detect stub content (heuristic: content under ~200 chars after extraction)
and log a warning: `"Saved but may require manual content: <filename>"`. File is still saved,
but user is flagged to verify content manually.

---

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
