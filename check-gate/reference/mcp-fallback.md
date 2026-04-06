# MCP Fallback for Gate Checks

Use when local scripts are unavailable.

Call `mcp__eightfold__config` with `read_config` discriminator. Omit `partition`
to get the full gate config with all keys.

Values: `1` = enabled, `0` = disabled, decimal = partial rollout (by email hash).

Lookup priority: explicit group → release cadence keys → `sandbox` → `*` → False.

See [special_keys.md](special_keys.md) for the full list of special keys and
how to determine if a group matches each one.

See [release_cadence.md](release_cadence.md) for how to resolve cadence and
deferral rules when the gate has `quarterly_release` keys.
