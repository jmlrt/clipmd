# CLAUDE.md

Project-specific guidance for the **clipmd** CLI tool.

For general Python development patterns, see the **python-development** skill in Claude Code.

---

# clipmd

CLI tool for saving, organizing, and managing markdown articles with YAML frontmatter.

**See `SPEC.md` for full specification (source of truth).**

## Quick Reference

```bash
# Development setup
make dev            # Install all dependencies (including dev extras)
make install        # Install dependencies without extras

# Quality checks (must pass before commit)
make check          # Run lint, typecheck, tests with coverage
make lint           # Run ruff linter
make format         # Format code with ruff
make typecheck      # Run ty type checker

# Testing
uv run pytest tests/unit                # Run only unit tests
uv run pytest tests/cli                 # Run only CLI tests
uv run pytest tests/integration         # Run only integration tests
uv run pytest tests/unit/test_config.py # Run specific test file
uv run pytest -k test_function_name     # Run specific test by name
uv run pytest --cov                     # Run with coverage report
make test                               # Run all tests
make test-cov                           # Run with coverage (89% minimum)

# Running the CLI
uv run clipmd --help           # Show help
uv run clipmd init             # Initialize new vault
uv run clipmd --config ./test-config.yaml extract  # Use specific config
```

## Implementation Approach

- Work on feature branch
- Phase-by-phase implementation (see spec for 9 phases)
- Atomic commits: each commit must pass `make check`

## Architecture Overview

**Separation of Concerns:**
- `cli.py` - Click CLI application entry point, global options, command registration
- `context.py` - Context object holding config, verbosity, vault path (passed via Click context)
- `config.py` - Pydantic-based configuration loading and validation (XDG-compliant paths)
- `commands/` - Thin CLI wrappers (50-150 lines): parse args → call core → display output
- `core/` - Pure business logic: no Click dependencies, returns dataclass results
- `exceptions.py` - Custom exception hierarchy with exit codes

**Key clipmd Decisions:**
- **Config as parameter**: Core functions take `Config` as a parameter, not from global context
- **Async fetching**: `core/fetcher.py` uses `httpx` async with semaphore for concurrent URL fetching (see [Async Fetching Architecture](#async-fetching-architecture) below)
- **Result dataclasses**: Core functions return typed dataclasses, commands format them for display
- **TYPE_CHECKING imports**: Core modules import `Config` under `TYPE_CHECKING` to avoid circular imports

## Key Paths

| Path | Purpose |
|------|---------|
| `SPEC.md` | Full specification (source of truth) |
| `CHANGELOG.md` | Project changelog (Keep a Changelog format) |
| `src/clipmd/cli.py` | CLI entry point, global options |
| `src/clipmd/context.py` | Context object (config, verbosity) |
| `src/clipmd/config.py` | Pydantic config models and loading |
| `src/clipmd/commands/` | CLI command modules (thin wrappers) |
| `src/clipmd/core/` | Business logic (pure functions) |
| `src/clipmd/exceptions.py` | Custom exceptions with exit codes |
| `tests/unit/` | Unit tests for core modules |
| `tests/cli/` | CLI command tests |
| `tests/integration/` | End-to-end workflow tests |
| `tests/fixtures/sample-vault/` | Test data and config |

## Configuration

**Config Location (XDG-compliant search order):**
1. `./config.yaml` (project root)
2. `./.clipmd/config.yaml` (project .clipmd directory)
3. `~/.config/clipmd/config.yaml` (user-wide config)
4. `--config PATH` flag overrides all

**Validation:**
- Config uses Pydantic v2 models for validation (`config.py`)
- Invalid config raises `ConfigError` with helpful messages
- Missing config falls back to sensible defaults
- All paths in config are resolved relative to vault root

## Error Handling

**Exception Hierarchy** (see `exceptions.py`):
- `ClipmdError` - Base exception (exit code 1)
  - `ConfigError` - Configuration errors
  - `FetchError` - URL fetching errors
  - `ParseError` - Frontmatter/content parsing errors
  - `CacheError` - Cache read/write errors
  - `ValidationError` - Input validation errors
  - `PartialSuccessError` - Some operations succeeded, some failed (exit code 2)

**Exit Codes:**
- `0` - Success
- `1` - Error (operation failed)
- `2` - Partial success (some items succeeded, some failed)

**Pattern**: Core functions return Result dataclasses with `success: bool` and optional `error: str | None`. Commands check results and raise `SystemExit(1)` on failure, or print Rich-formatted errors and exit.

## Development Practices

### When Fixing Bugs in Similar Commands

**clipmd-specific practice**: When fixing a bug or inconsistency in one CLI command, proactively check ALL similar commands for the same issue before considering the task done. Do not wait for the user to ask twice.

### Library Selection Principle

Prefer well-maintained, actively-developed libraries from PyPI over custom implementations:

- **Example**: Adopted `python-frontmatter` (20M+ downloads/month) to replace custom regex parsing
- **Evaluation**: Does it handle our specific requirements? (normalization, truncation, etc.)
- **Trade-off**: `python-slugify` NOT used because it doesn't support NFD normalization needed for sanitizer

### Testing Strategy

- `tests/unit/` - Test core business logic (frontmatter, config, sanitizer, etc.)
- `tests/cli/` - Test CLI interfaces (argument parsing, output formatting)
- `tests/integration/` - Test complete workflows (fetch → preprocess → extract → move)
- Target coverage: ≥89%

### Architecture Reference

For generic architectural patterns, see the **python-development** skill in Claude Code:

All clipmd commands follow these patterns with core logic in `core/` modules and thin CLI wrappers (50-150 lines) in `commands/`.

## TODO.md and NOTES.md

### TODO.md (committed)

`TODO.md` tracks open issues, planned features, and refactoring opportunities
for the **public repo**. Keep it generic and impersonal — no session dates,
vault-specific folder names, file counts, or personal workarounds.

**Structure:**

```markdown
## Bug Fixes        ← open issues with user-visible impact
## Features         ← planned commands, flags, or behaviors
## Refactoring      ← internal code quality improvements
```

**Each entry format:**

```markdown
### <command>: <short description>

**Priority**: Critical | High | Medium | Low

<One or two sentences describing the problem.>

**Proposed fix**: <what to implement, with example output if helpful>
```

**Rules:**
- Remove entries once the fix is merged to `main`
- No "✅ FIXED" markers — just delete resolved entries
- No personal observations ("I saw 188 files…"), workarounds, or session notes
- Use generic folder names in examples (`Inbox/`, `Articles/`), not vault-specific ones

### NOTES.md (local only, gitignored)

`NOTES.md` is the personal counterpart to `TODO.md`. It is listed in
`.gitignore` and never committed.

**What belongs in NOTES.md:**
- Session observations with specific file counts and vault folder names
- Workaround scripts used before a fix landed
- Investigation notes and reproduction steps for tricky issues
- Personal triage workflow goals and ideal command sequences
- Documentation update plans for personal workflow docs (e.g. clipping-triage.md)
- Refactoring roadmap with timeline estimates and phase completion notes

## Git Workflow

When staging and committing changes, ensure ONLY changes from the current task are included. Review staged files against the current session scope before committing.

### Addressing PR Review Comments

When asked to address PR review comments (from Copilot, human reviewers, etc.), follow this workflow to avoid excessive GitHub API calls:

1. **Fetch all comments once**: Use `gh api` to retrieve all PR comments (including outdated/resolved ones) and save to a temporary file
   ```bash
   gh api repos/:owner/:repo/pulls/{PR_NUMBER}/comments --paginate > pr-comments-review.json
   ```

2. **Create human-readable summary**: Extract relevant fields into a readable format
   ```bash
   cat pr-comments-review.json | jq -r '.[] | select(.in_reply_to_id == null) | "---\nID: \(.id)\nFile: \(.path)\nLine: \(.line // .original_line // "N/A")\nUser: \(.user.login)\nCreated: \(.created_at)\n\n\(.body)\n"' > pr-comments-summary.txt
   ```

3. **Work from the file**: Review each comment systematically, checking current code state against the issues raised

4. **Track progress**: Create an analysis file to track which issues are fixed, no longer applicable (due to refactoring), or still need work

5. **Clean up**: Remove temporary files when all issues are addressed
   ```bash
   rm pr-comments-review.json pr-comments-summary.txt pr-comments-analysis.md
   ```

**Rationale**: This approach minimizes API calls, provides a stable reference while working, and creates a clear audit trail of what was addressed.

### Changelog Maintenance

**IMPORTANT**: Update `CHANGELOG.md` for all user-facing changes:

**When to update:**
- New features (commands, options, functionality)
- Bug fixes that affect behavior
- Breaking changes to CLI or config format
- Dependency updates (major versions)
- Deprecations or removals

**When NOT to update:**
- Internal refactoring (no behavior change)
- Test-only changes
- Documentation updates (unless major)
- Code formatting/linting

**How to update:**
1. Add entry under `[Unreleased]` section
2. Use Keep a Changelog categories: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`
3. Write user-facing descriptions (not technical implementation details)
4. Group related changes together

**Example:**
```markdown
## [Unreleased]

### Added
- `extract` command now supports `--include-tags` option for tag filtering

### Fixed
- `fetch` command no longer crashes on malformed HTML meta tags
```

**On release:**
- Move `[Unreleased]` entries to new version section with date
- Update version links at bottom of file
- Bump version in `pyproject.toml` following Semantic Versioning

## Async Fetching Architecture

The `core/fetcher.py` module uses async/await with `httpx` for concurrent URL fetching:

**Key Functions:**
- `fetch_url()` - Async function to fetch single URL with timeout and retries
- `fetch_urls()` - Async orchestrator using `asyncio.Semaphore` to limit concurrency
- `fetch_rss_feed()` - Async RSS/Atom feed parser
- `orchestrate_fetch()` - Main entry point coordinating all fetch operations

**Concurrency Control:**
- `max_concurrent` setting controls semaphore limit (default: 5)
- Uses `asyncio.gather()` for parallel execution
- Each fetch operation is independent (failures don't block others)

**Important Behaviors:**
1. Meta-refresh redirects are handled automatically
2. Tracking URL parameters are cleaned (utm_*, fbclid, etc.)
3. Never overwrites existing files (appends suffix like `-2.md`, `-3.md`)
4. Content extraction uses trafilatura for readability mode
