#!/usr/bin/env bash
#
# Extract PR body structure from an existing PR (for reference).
#
# Usage:
#   ./extract_pr_pattern.sh <pr-number>
#
# Example:
#   ./extract_pr_pattern.sh 102400
#
# Output: Shows which checklist items are checked, useful for creating similar PRs

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <pr-number>"
    echo "Example: $0 102400"
    exit 1
fi

PR_NUMBER=$1

echo "Fetching PR #${PR_NUMBER}..."
echo

# Get PR body using gh CLI
PR_BODY=$(gh pr view "${PR_NUMBER}" --json body --jq '.body')

if [ -z "$PR_BODY" ]; then
    echo "❌ Failed to fetch PR body"
    exit 1
fi

echo "=== SUMMARY ==="
echo "$PR_BODY" | sed -n '/## SUMMARY:/,/## JIRA TASK:/p' | head -n -1
echo

echo "=== CHECKED PRODUCT AREAS ==="
echo "$PR_BODY" | grep -E '^\s*-\s+\[x\]\s+(AI Platform|AI Recruiter|CI|DP|Mobile Platform|PCS|TA|TD|TM|WFX|RM)' || echo "(none)"
echo

echo "=== REGRESSION TESTING ==="
echo "$PR_BODY" | grep -A 1 'Regression testing is not required because' | tail -n 1
echo

echo "=== GATE CONTROL (if not gated) ==="
echo "$PR_BODY" | sed -n '/IF the change is not gated/,/- Keep it simple/p' | grep '\[x\]' || echo "(gated or none)"
echo

echo "=== KEEP IT SIMPLE ==="
echo "$PR_BODY" | sed -n '/- Keep it simple/,/- Handle Edge cases/p' | grep '\[x\]' || echo "(none)"
echo

echo "=== TEST PLAN ==="
echo "$PR_BODY" | sed -n '/## TEST PLAN:/,/^$/p'
echo

echo ""
echo "💡 Use this pattern as reference for similar PRs"
