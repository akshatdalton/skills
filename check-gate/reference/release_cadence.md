# Release Cadence Resolution

The only active release cadence is **quarterly**. Monthly cadence is deprecated — no production groups have `release_cadence: "monthly"`, so `monthly_release` / `monthly_release_sandbox` keys in gates are inert. If you see them, they can be ignored.

`quarterly_release` and `quarterly_release_sandbox` keys sit between explicit group matches and the `*` default in the lookup chain. Only consult this when the gate has these keys and the group isn't explicitly listed.

## 1. Determine the group's cadence

```
config_name: "release_preferences_config"
partition: "somegroup.com"
```

The `release_cadence` field will be `"quarterly"` or absent (falls back to the `__default__` partition, which is also `"quarterly"`).

Sandbox groups use `quarterly_release_sandbox`.

## 2. Check for deferral

In the same `release_preferences_config` result, look for a `feature_deferrals` array. Each entry has:
- `gate_name` — the gate being deferred
- `defer_until` — Unix timestamp, or `-1` for indefinite deferral

A gate is **deferred** (cadence keys skipped) if:
- `defer_until == -1` (permanent opt-out), OR
- `defer_until` is in the future

When deferred, lookup skips cadence keys and falls through to `sandbox` → `*` → `False`.
