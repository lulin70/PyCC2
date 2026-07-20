#!/bin/bash
# check_doc_consistency.sh — Verify all docs reference the current VERSION
# Usage: ./scripts/check_doc_consistency.sh
# Exit 0 if all docs are consistent, exit 1 otherwise.
# Created: 2026-07-13 (root cause fix for PRD/DESIGN lagging at v0.4.7)

set -euo pipefail

VERSION=$(cat VERSION)
ERRORS=0

# Documents that MUST reference the current version
# Wave B-rev P0-4 (2026-07-20): 追加 v0.9.0 视觉打磨 3 项文档
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

echo ""
if [ "$ERRORS" -gt 0 ]; then
    echo "FAILED: $ERRORS document(s) inconsistent with VERSION=${VERSION}"
    exit 1
else
    echo "SUCCESS: All documents consistent with VERSION=${VERSION}"
    exit 0
fi
