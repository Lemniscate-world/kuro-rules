#!/bin/bash
# pre-commit-milestone-check.sh
# Git pre-commit hook to verify milestone tasks exist before commit
# Install: cp scripts/pre-commit-milestone-check.sh .git/hooks/pre-commit
# OR: cp scripts/pre-commit-milestone-check.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit

set -e

echo "🔍 Checking milestone tasks..."

# Get current progress from ROADMAP.md if exists
if [ -f "ROADMAP.md" ]; then
    # Extract progress percentage (look for patterns like "Progress: 25%" or "25%" in milestone context)
    PROGRESS=$(grep -E "Progress:|%" ROADMAP.md | head -1 | grep -oE "[0-9]+" | head -1)
    
    if [ -n "$PROGRESS" ]; then
        echo "📊 Current progress: ${PROGRESS}%"
        
        # Determine milestone
        if [ "$PROGRESS" -ge 10 ] && [ "$PROGRESS" -lt 25 ]; then
            MILESTONE=10
        elif [ "$PROGRESS" -ge 25 ] && [ "$PROGRESS" -lt 50 ]; then
            MILESTONE=25
        elif [ "$PROGRESS" -ge 50 ] && [ "$PROGRESS" -lt 75 ]; then
            MILESTONE=50
        elif [ "$PROGRESS" -ge 75 ] && [ "$PROGRESS" -lt 90 ]; then
            MILESTONE=75
        elif [ "$PROGRESS" -ge 90 ] && [ "$PROGRESS" -lt 95 ]; then
            MILESTONE=90
        elif [ "$PROGRESS" -ge 95 ]; then
            MILESTONE=95
        fi
        
        if [ -n "$MILESTONE" ]; then
            echo "🎯 Milestone: ${MILESTONE}%"
            
            # Check if milestone tasks file exists
            if [ -f "infrastructure_planning/milestone_${MILESTONE}_tasks.md" ]; then
                echo "✅ Milestone tasks file exists: milestone_${MILESTONE}_tasks.md"
            else
                echo "❌ ERROR: Milestone tasks file NOT FOUND: infrastructure_planning/milestone_${MILESTONE}_tasks.md"
                echo "❌ COMMIT BLOCKED: Generate milestone tasks before committing (R26, R29)"
                echo ""
                echo "To fix: Create infrastructure_planning/milestone_${MILESTONE}_tasks.md with 5 tasks"
                echo "        Then create issues in Linear or GitHub with DevOps/MLOps/Security labels"
                exit 1
            fi
        fi
    fi
else
    echo "⚠️  ROADMAP.md not found - cannot determine milestone"
fi

echo "✅ Milestone check passed"
exit 0