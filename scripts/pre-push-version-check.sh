#!/bin/bash
# pre-push-version-check.sh
# Git pre-push hook to verify VERSION file matches git tags
# Install: cp scripts/pre-push-version-check.sh .git/hooks/pre-push
# OR: Copy to .git/hooks/pre-push and chmod +x

set -e

echo "🔍 Checking version consistency..."

# Check VERSION file exists
if [ ! -f "VERSION" ]; then
    echo "❌ ERROR: VERSION file not found at project root"
    echo "❌ PUSH BLOCKED: Create VERSION file before pushing"
    exit 1
fi

# Source VERSION file
source VERSION

# Get current git tag
CURRENT_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "none")

echo "📦 VERSION file: v${MAJOR}.${MINOR}.${PATCH}-kuro (${MILESTONE})"
echo "🏷️  Git tag:      ${CURRENT_TAG}"

# Check if versions match
if [ "$CURRENT_TAG" != "v${MAJOR}.${MINOR}.${PATCH}-kuro" ]; then
    echo ""
    echo "❌ ERROR: VERSION file does not match git tags"
    echo "Expected: v${MAJOR}.${MINOR}.${PATCH}-kuro"
    echo "Found:    ${CURRENT_TAG}"
    echo ""
    echo "❌ PUSH BLOCKED: Update VERSION file or create missing tag'
    echo ""
    echo "To fix:"
    echo "  1. If tag missing: git tag -a v${MAJOR}.${MINOR}.${PATCH}-kuro -m 'milestone ${MILESTONE}'"
    echo "  2. If VERSION outdated: Update VERSION file to match current tag"
    exit 1
fi

# Check if this is pushing tags (allow if tags are being pushed)
if [ "$CURRENT_TAG" != "none" ]; then
    echo "✅ Version check passed - VERSION matches git tags"
else
    echo "⚠️  No tags found - is this your first tag?"
fi

# Check milestone tasks exist for current version
if [ "${MILESTONE}" != "0%" ]; then
    MILESTONE_NUM=$(echo $MILESTONE | tr -d '%')
    if [ -f "infrastructure_planning/milestone_${MILESTONE_NUM}_tasks.md" ]; then
        echo "✅ Milestone tasks file exists for ${MILESTONE}"
    else
        echo "❌ WARNING: Milestone tasks file NOT FOUND for ${MILESTONE}"
        echo "Expected: infrastructure_planning/milestone_${MILESTONE_NUM}_tasks.md"
    fi
fi

echo "✅ Version check passed"
exit 0