#!/usr/bin/env python3
"""
Validate PR body against template before submission.

Usage:
    python scripts/validate_pr_body.py pr-body.txt
"""

import re
import sys
from pathlib import Path


def load_template(repo_root: Path) -> str:
    """Load the PR template from the repository."""
    template_path = repo_root / ".github" / "PULL_REQUEST_TEMPLATE.md"
    if not template_path.exists():
        print(f"❌ Template not found: {template_path}")
        sys.exit(1)
    return template_path.read_text()


def extract_checklist_items(text: str) -> list[str]:
    """Extract all checkbox items from markdown text."""
    # Match lines like "  - [ ] Text" or "    - [ ] Text"
    pattern = r"^\s*-\s+\[\s*[xX\s]\s*\]\s+(.+)$"
    items = []
    for line in text.split("\n"):
        match = re.match(pattern, line)
        if match:
            items.append(match.group(1).strip())
    return items


def validate_pr_body(pr_body: str, template: str) -> tuple[bool, list[str]]:
    """
    Validate PR body against template.
    
    Returns:
        (is_valid, errors)
    """
    errors = []
    
    # Extract checklist items from both
    template_items = extract_checklist_items(template)
    pr_items = extract_checklist_items(pr_body)
    
    # Check for missing items
    template_items_text = [item.lower() for item in template_items]
    pr_items_text = [item.lower() for item in pr_items]
    
    missing_items = []
    for template_item in template_items:
        # Normalize for comparison
        normalized = template_item.lower()
        if normalized not in pr_items_text:
            # Check if it's a modified version (e.g., filled blank)
            # Items with _____ can be filled
            if "_____" not in template_item and normalized not in pr_items_text:
                missing_items.append(template_item)
    
    if missing_items:
        errors.append("Missing or modified checklist items:")
        for item in missing_items[:5]:  # Show first 5
            errors.append(f"  - {item[:80]}...")
    
    # Check for blank fields
    blank_pattern = r":\s+_+\s*$"
    for line in pr_body.split("\n"):
        if re.search(blank_pattern, line):
            errors.append(f"Blank field found: {line.strip()[:80]}")
    
    # Check for required sections
    required_sections = [
        "## SUMMARY:",
        "## JIRA TASK:",
        "## GATE/CONFIG:",
        "## CHECKLIST:",
        "## TEST PLAN:",
    ]
    
    for section in required_sections:
        if section not in pr_body:
            errors.append(f"Missing required section: {section}")
    
    # Check for HTML entities (warning only)
    if "&#" in pr_body or "&lt;" in pr_body or "&gt;" in pr_body:
        errors.append("⚠️  WARNING: HTML entities detected (&#39;, &amp;, etc.) - did you copy from MCP response?")
    
    return len(errors) == 0, errors


def main():
    if len(sys.argv) != 2:
        print("Usage: python validate_pr_body.py pr-body.txt")
        sys.exit(1)
    
    pr_body_path = Path(sys.argv[1])
    if not pr_body_path.exists():
        print(f"❌ PR body file not found: {pr_body_path}")
        sys.exit(1)
    
    # Find repository root (assumes script is in repo)
    repo_root = Path.cwd()
    while repo_root != repo_root.parent:
        if (repo_root / ".git").exists():
            break
        repo_root = repo_root.parent
    else:
        print("❌ Not in a git repository")
        sys.exit(1)
    
    # Load files
    pr_body = pr_body_path.read_text()
    template = load_template(repo_root)
    
    # Validate
    is_valid, errors = validate_pr_body(pr_body, template)
    
    if is_valid:
        print("✅ PR body validation passed!")
        print("\nRecommendations:")
        print("  - Verify summary is concise (2-3 sentences)")
        print("  - Test plan should be minimal (command only, or UI steps)")
        print("  - All blanks (_____ ) filled with values or N/A")
        sys.exit(0)
    else:
        print("❌ PR body validation failed!\n")
        print("Errors found:")
        for error in errors:
            print(error)
        print("\n💡 Tips:")
        print("  - Copy checklist items exactly from .github/PULL_REQUEST_TEMPLATE.md")
        print("  - Fill all _____ blanks with values or 'N/A'")
        print("  - Never delete checklist items, only check/uncheck them")
        sys.exit(1)


if __name__ == "__main__":
    main()
