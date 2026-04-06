---
name: check-gate
description: >
  Check whether a feature gate is enabled for a group/domain. Trigger when user
  asks about gate status, feature flags, rollout, or "is X enabled for Y".
---

# Check Gate Enablement Status

## 1. Resolve gate name

If vague, grep the codebase for `keyword.*gate`. Gates end in `_gate`.

## 2. Check gate for a specific group

```bash
python -c "
from user import user_login
from config import config
user = user_login.get_import_user(group_id='GROUP_ID')
print(config.enabled_for('GATE_NAME', user))
"
```

This resolves the full lookup chain — special keys, release cadence, sandbox
detection, deferrals — and returns a definitive boolean.

## 3. Full config view

To see the raw config with all keys and overrides:
```bash
python scripts/config/get_config.py --config_name GATE_NAME
```

Values: `1` = enabled, `0` = disabled, decimal = partial rollout.

## 4. Other gate scripts

```bash
# Search which configs reference a gate
python scripts/one-off/check_gate_usage.py --gate GATE_NAME

# Diff all gates between two groups
python scripts/one-off/diff_group_gates.py --group-a GROUP_A --group-b GROUP_B
```

## 5. MCP fallback

If scripts fail, see [reference/mcp-fallback.md](reference/mcp-fallback.md).
