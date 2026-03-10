#!/bin/bash
# Autonomous validation script - run before every push
# This ensures code meets all requirements for autonomous pushing

set -e

echo "🔍 Pre-push Validation Checklist"
echo "================================"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FAIL_COUNT=0

# 1. Check git status
echo "✓ Checking git status..."
if git status --porcelain | grep -q .; then
    echo -e "${YELLOW}  ⚠ Working directory has uncommitted changes${NC}"
    git status --short
fi

# 2. Check for local settings file
echo "✓ Checking for settings.local.json..."
if [ -f ".claude/settings.local.json" ]; then
    echo -e "${RED}  ✗ FAIL: .claude/settings.local.json exists (must be gitignored only)${NC}"
    ((FAIL_COUNT++))
else
    echo -e "${GREEN}  ✓ No local settings file (good!)${NC}"
fi

# 3. Run full quality checks
echo "✓ Running make check (lint, typecheck, tests)..."
if make check > /dev/null 2>&1; then
    echo -e "${GREEN}  ✓ All checks passed${NC}"
else
    echo -e "${RED}  ✗ FAIL: make check failed${NC}"
    echo "     Run: make check (for details)"
    ((FAIL_COUNT++))
fi

# 4. Check test coverage
echo "✓ Checking test coverage..."
COVERAGE=$(make test-cov 2>&1 | grep "TOTAL" | awk '{print $(NF-1)}' | sed 's/%//')
if (( $(echo "$COVERAGE >= 89" | bc -l) )); then
    echo -e "${GREEN}  ✓ Coverage: ${COVERAGE}% (≥89% required)${NC}"
else
    echo -e "${RED}  ✗ FAIL: Coverage: ${COVERAGE}% (need ≥89%)${NC}"
    ((FAIL_COUNT++))
fi

# 5. Check for unintended files in staging
echo "✓ Checking staged files..."
STAGED_FILES=$(git diff --cached --name-only)
BANNED_FILES=".env credentials.json .claude/settings.local.json"
HAS_BANNED=0
for file in $BANNED_FILES; do
    if echo "$STAGED_FILES" | grep -q "^$file$"; then
        echo -e "${RED}  ✗ FAIL: Sensitive file staged: $file${NC}"
        ((HAS_BANNED++))
    fi
done
if [ $HAS_BANNED -eq 0 ]; then
    echo -e "${GREEN}  ✓ No sensitive files staged${NC}"
else
    ((FAIL_COUNT++))
fi

# 6. Check commit message format
echo "✓ Checking recent commits..."
LAST_MSG=$(git log -1 --pretty=%B)
if echo "$LAST_MSG" | grep -qE "^(feat|fix|docs|refactor|test|chore|perf)(\(.+\))?:"; then
    echo -e "${GREEN}  ✓ Last commit follows conventional commits${NC}"
else
    echo -e "${YELLOW}  ⚠ Warning: Commit may not follow conventional format${NC}"
fi

# 7. Check branch is up to date
echo "✓ Checking if branch needs rebase..."
if git merge-base --is-ancestor origin/main HEAD 2>/dev/null; then
    echo -e "${GREEN}  ✓ Branch includes all main commits${NC}"
else
    echo -e "${YELLOW}  ⚠ Branch may be behind main (consider: git rebase origin/main)${NC}"
fi

# 8. Check for large files
echo "✓ Checking for large files..."
LARGE_FILES=$(find . -type f -size +10M ! -path "./.git/*" ! -path "./.venv/*" ! -path "./.pytest_cache/*" 2>/dev/null)
if [ -z "$LARGE_FILES" ]; then
    echo -e "${GREEN}  ✓ No large files detected${NC}"
else
    echo -e "${YELLOW}  ⚠ Large files found:${NC}"
    echo "$LARGE_FILES" | sed 's/^/     /'
fi

echo ""
echo "================================"
if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ All checks PASSED${NC}"
    echo ""
    echo "Ready to push! You can now:"
    echo "  git push origin $(git rev-parse --abbrev-ref HEAD)"
    exit 0
else
    echo -e "${RED}✗ $FAIL_COUNT check(s) FAILED${NC}"
    echo ""
    echo "Fix issues before pushing:"
    echo "  1. Read error messages above"
    echo "  2. Make corrections"
    echo "  3. Run: make check"
    echo "  4. Re-run this script"
    exit 1
fi
