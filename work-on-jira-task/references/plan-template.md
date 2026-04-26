# Implementation Plan Template

```markdown
# [Feature/Fix Name] — Implementation Plan

## What We're Building
[Plain English: what problem, why?]

## Starting Point: What Already Exists
[Infrastructure, patterns, files — with file:line references]

## The Approach
[Core design decision and why — mention alternatives considered]

## Implementation Details

### [Component 1]
[What it does and why]

```python
# Actual approach, not pseudocode
def example(arg):
    # Comments on non-obvious decisions
    return result
```

**Why this way:** [Rationale for non-obvious parts]

## Testing Strategy
**What we're testing:** [our logic — transformations, error handling, edge cases]
**What we're NOT testing:** [framework behaviour, dataclass construction, etc.]

## Files to Create / Modify
- `path/to/file.py` — [what and why]

## Known Limitations
[Deferred work, accepted trade-offs]
```
