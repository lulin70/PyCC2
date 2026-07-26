#!/bin/bash
# check_doc_consistency.sh — Verify all docs reference the current VERSION
# Usage: ./scripts/check_doc_consistency.sh
# Exit 0 if all docs are consistent, exit 1 otherwise.
# Created: 2026-07-13 (root cause fix for PRD/DESIGN lagging at v0.4.7)
# Enhanced: 2026-07-25 (P3-1: PROJECT_STATUS.md key fields existence + date format check)

set -euo pipefail

VERSION=$(cat VERSION)
ERRORS=0

# Documents that MUST reference the current version
# Wave B-rev P0-4 (2026-07-20): 追加 v0.9.0 视觉打磨 3 项文档
# v0.9.1 (2026-07-24): 追加 INSTALL 三语文档 (D13-N8 修复)
REQUIRED_DOCS=(
    "docs/PRD.md"
    "docs/DESIGN.md"
    "docs/ROADMAP.md"
    "docs/PROJECT_STATUS.md"
    "docs/TECH_DEBT.md"
    "docs/TEST_PLAN.md"
    "README.md"
    "README_zh.md"
    "README_ja.md"
    "docs/VISUAL_POLISH_PLAN.md"
    "docs/ROADMAP_v0.9.0.md"
    "docs/VISUAL_OPTIMIZATION_UNIFIED.md"
    "INSTALL.md"
    "INSTALL_zh.md"
    "INSTALL_ja.md"
)

echo "Checking document version consistency (VERSION=${VERSION})..."

for doc in "${REQUIRED_DOCS[@]}"; do
    if [ ! -f "$doc" ]; then
        echo "WARN: $doc does not exist (skipped)"
        continue
    fi
    if ! grep -qE "v?${VERSION}" "$doc"; then
        echo "ERROR: $doc does not reference version ${VERSION}"
        ERRORS=$((ERRORS+1))
    else
        echo "OK: $doc references version ${VERSION}"
    fi
done

# Also check Python version constants
if ! grep -q "\"${VERSION}\"" src/pycc2/__init__.py 2>/dev/null; then
    echo "ERROR: src/pycc2/__init__.py __version__ does not match ${VERSION}"
    ERRORS=$((ERRORS+1))
else
    echo "OK: src/pycc2/__init__.py __version__ matches ${VERSION}"
fi

if ! grep -q "version = \"${VERSION}\"" pyproject.toml 2>/dev/null; then
    echo "ERROR: pyproject.toml version does not match ${VERSION}"
    ERRORS=$((ERRORS+1))
else
    echo "OK: pyproject.toml version matches ${VERSION}"
fi

# P3-1 Enhancement (2026-07-25): PROJECT_STATUS.md key fields existence + date format check
# Root cause: PROJECT_STATUS.md L14 test count lagged 528 (v0.7.6 6291 → v0.9.0 6819) across
# 2 versions undetected. Version-only check cannot catch numeric lag.
# Solution: verify key fields exist + date format valid (no numeric value comparison
# to avoid false positives when numbers legitimately change).
PROJECT_STATUS="docs/PROJECT_STATUS.md"
if [ -f "$PROJECT_STATUS" ]; then
    # Check 1: "最后更新" date exists and matches YYYY-MM-DD format
    if ! grep -qE "^> \*\*最后更新\*\*: [0-9]{4}-[0-9]{2}-[0-9]{2}" "$PROJECT_STATUS"; then
        echo "ERROR: $PROJECT_STATUS missing or malformed '最后更新' date (expected YYYY-MM-DD)"
        ERRORS=$((ERRORS+1))
    else
        echo "OK: $PROJECT_STATUS has valid '最后更新' date"
    fi
    # Check 2: "测试用例数" row exists (ensures field not deleted)
    if ! grep -q "测试用例数" "$PROJECT_STATUS"; then
        echo "ERROR: $PROJECT_STATUS missing '测试用例数' row"
        ERRORS=$((ERRORS+1))
    else
        echo "OK: $PROJECT_STATUS has '测试用例数' row"
    fi
    # Check 3: "实际覆盖率" row exists (ensures field not deleted)
    if ! grep -q "实际覆盖率" "$PROJECT_STATUS"; then
        echo "ERROR: $PROJECT_STATUS missing '实际覆盖率' row"
        ERRORS=$((ERRORS+1))
    else
        echo "OK: $PROJECT_STATUS has '实际覆盖率' row"
    fi
else
    echo "WARN: $PROJECT_STATUS does not exist (skipped)"
fi

echo ""
if [ "$ERRORS" -gt 0 ]; then
    echo "FAILED: $ERRORS document(s) inconsistent with VERSION=${VERSION}"
    exit 1
else
    echo "SUCCESS: All documents consistent with VERSION=${VERSION}"
    exit 0
fi
