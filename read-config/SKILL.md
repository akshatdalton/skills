---
name: read-config
description: >
  Read Eightfold platform configuration values. Use when user asks about config
  settings, partitioned configs, or needs to inspect non-gate configuration.
  Do NOT use for gate checks — use check-gate instead.
---

# Read Configuration

```bash
python scripts/config/get_config.py --config_name CONFIG_NAME
```

If scripts fail, use `mcp__eightfold__config` with `read_config` discriminator.

## Partitioned configs

`--field_name` selects the partition for partitioned configs, or navigates into
a field for flat configs. Pass partition first, then field path:

```bash
# Read partition
python scripts/config/get_config.py --config_name CONFIG_NAME --field_name somegroup.com

# Read field within partition
python scripts/config/get_config.py --config_name CONFIG_NAME --field_name somegroup.com enabled

# List all partitions
python -c "
from config import config
from utils import json_utils
print(json_utils.dumps(config.get_all_partitions_for_config('CONFIG_NAME'), indent=2))
"
```

## Filtering large configs

Pipe through `jq`:
```bash
python scripts/config/get_config.py --config_name CONFIG_NAME | jq '.path.to.field'
```
