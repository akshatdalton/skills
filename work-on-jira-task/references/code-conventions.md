# Code Conventions — operator_platform (Python)

## Method ordering
constructor → public → private (`_` prefix)

## Structure
- Tightly coupled helpers: `@staticmethod` inside class, not module-level
- Shared enums/types: in base classes, not per-implementation files
- Module-private constants: `_` prefix
- Dataclasses for structured returns over raw dicts
- Keyword args for calls with >1 parameter

## Imports
- `from mock import patch` (not `unittest.mock`)
- `datetime.now(UTC)` (not `datetime.utcnow()`)
- No `from __future__ import absolute_import`
- Grep codebase before inventing. Match existing style: `settings.x` over `os.getenv('X')`

## Documentation
- Module docstrings: skip
- Class docstrings: architecture intent ("Why") only
- Method docstrings: only non-obvious contracts
- Test docstrings: never

## Testing
- Before each test: what breaks without it? No answer → don't write it
- One behavior = one test. Never same check twice
- Collapse redundant cases: mixed-input test proves both sides
- Cover: (1) happy path, (2) no-op/backwards-compat, (3) new data contracts
- Skip: framework behaviour, dataclass construction, wiring-only tests
- Class-level decorators over per-test repetition
