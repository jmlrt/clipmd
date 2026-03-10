# Autonomous Workflow Guide

This document defines the automatic workflow patterns used by Claude agents in unattended mode.

## Validation-First Principle

Before any commit or push, agents automatically:

1. **Code Quality Check**
   ```bash
   make check  # Runs: lint, typecheck, tests (89% coverage minimum)
   ```

2. **Test All Scenarios**
   - Unit tests: `make test` passes
   - Integration tests: All workflows tested
   - Coverage: 89% minimum required

3. **Manual Review Gate**
   - Only then: commit + push
   - Each commit includes test proof
   - PR description includes test results

## Autonomous Task Categories

### Category 1: Code Changes (No Approval Needed)
- ✅ Add features or fix bugs
- ✅ Refactor existing code
- ✅ Update tests
- ✅ Improve documentation

**Requirements:**
- All tests pass (`make check`)
- Coverage maintained/improved (≥89%)
- Commits are atomic + well-documented

### Category 2: Risk Assessment (Auto-Validation)
- ⚠️ Delete files or functions
- ⚠️ Refactor critical paths
- ⚠️ Change architecture
- ⚠️ Modify configurations

**Requirements:**
- Tests pass BEFORE making changes
- Tests pass AFTER changes
- Diff reviewed for unintended side effects
- Uses worktree isolation

### Category 3: Manual Review Required (Blocked)
- ❌ Force push to main
- ❌ Delete branches
- ❌ Merge without tests passing
- ❌ Bypass safety checks

**Safeguard:** These are explicitly denied in `.claude/settings.json`

## Worktree Isolation Workflow

For complex changes, agents use isolated worktrees:

```bash
# 1. Start isolated work
Enter worktree: "my-feature"
├─ Changes are isolated from main
├─ Full freedom to experiment
└─ No impact on main branch

# 2. Validate continuously
make check    # Local validation
git diff      # Review changes

# 3. Exit cleanly
Exit worktree: keep changes
└─ If validation passed: merge to main
└─ If validation failed: discard + try again
```

## Validation Checklist (Auto-Run)

Agents automatically verify before pushing:

- [ ] `make check` passes (lint, typecheck, tests)
- [ ] Test coverage ≥89%
- [ ] No new type errors
- [ ] All commits pass tests individually
- [ ] Commit messages are clear and atomic
- [ ] No unintended files staged
- [ ] Branch is up to date with main
- [ ] `.claude/settings.local.json` NOT modified

## Error Recovery

If validation fails:

1. **Lint Errors** → Auto-fix with `make format`
2. **Type Errors** → Read error message, fix, re-validate
3. **Test Failures** → Investigate, fix root cause, re-validate
4. **Coverage Drop** → Add tests for new code paths
5. **Merge Conflicts** → Rebase on main, re-validate

## Trust Escalation Unlocks

### After First Successful PR (→ Trusted Level)
- Can merge own PRs without waiting
- Access to pre-commit hook bypass (with validation)
- Broader git operations allowed

### After 3+ Successful Sessions (→ Autonomous Level)
- No validation warnings
- Full worktree freedom
- CI-like operations without human oversight
- Can work across entire codebase with confidence

## Real-World Example

**Task:** Implement new feature across 5 files

```
Agent autonomous actions:
1. Create feature branch: feat/new-feature
2. Implement changes locally
3. Run: make check (auto-validates)
4. If failing: debug + fix + re-run make check
5. If passing: commit + push to feature branch
6. Tests run in GitHub Actions automatically
7. When merged: trust level increases
```

**Zero approval requests** needed if:
- Changes are focused on one feature
- All tests pass locally
- Code follows project patterns
- No safety guardrails violated

## Preventing Permission Creep

To avoid constant permission requests:

1. **Permission Profiles Are Comprehensive**
   - All common operations covered
   - Wildcards used where safe (e.g., `git:*`)
   - Grouped by task type

2. **Settings Lock**
   - `.claude/settings.local.json` is gitignored
   - Cannot be modified by agent
   - Prevents permission drift
   - Use `.claude/settings.json` (committed) for changes

3. **Deny List is Explicit**
   - Force push explicitly blocked
   - Hard reset explicitly blocked
   - Recursive delete explicitly blocked
   - These prevent accidents, not productivity

## Monitoring Trust Escalation

To check current level and earned permissions:

```bash
# View current trust level
cat .claude/settings.json | jq .trust_escalation.current_level

# View what operations need validation
cat .claude/settings.json | jq .permissions_by_profile.risky-operations
```

## Escalation Timeline

| Session | Merges | Level | New Permissions |
|---------|--------|-------|-----------------|
| 1 | 0 | Basic | Code changes, testing |
| 1-5 | 1 | Trusted | Push to main, risky ops with validation |
| 5+ | 3+ | Autonomous | Full autonomy, no validation warnings |

Manual escalation available: Update `trust_escalation.current_level` in settings.json

---

**Goal:** Enable agents to work autonomously without constant approval requests, while maintaining safety through validation and clear permission boundaries.
