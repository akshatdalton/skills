# Special Keys (GATE_WINDOWS)

Defined in `www/config/config.py`. Beyond individual group/domain IDs, gates can contain these keys:

| Key | Meaning |
|-----|---------|
| `*` | Default/fallback for all unmatched groups |
| `efdemo` | Demo instances (eightfolddemo-*.com) |
| `sandbox` | Sandbox environment |
| `admin` | Internal admin users |
| `unittest` | Test environment |
| `demo` | Users with email starting 'demo@' |
| `efemployer` | Employer portal users |
| `readonly` | Read-only users |
| `exchanges` | Talent exchange users |
| `monthly_release` / `monthly_release_sandbox` | **Deprecated** — monthly cadence no longer exists. These keys are inert (no groups return `"monthly"` from `get_release_cadence()`). Treat as dead config if encountered. |
| `quarterly_release` / `quarterly_release_sandbox` | Quarterly release cadence (prod / sandbox) — the only active release cadence |
| `aii_standalone` | Standalone AII instances |
| `forward_to` | Redirects lookup to another gate's config |

Other patterns: `override::{email}` (per-user override), `{group_id}::anonymous`.

## How to determine if a group matches a special key

### String-based (no lookup needed)

- `efdemo` → group ID starts with `eightfolddemo-` (but NOT `eightfolddemo-ga-*`, `eightfolddemo-gaparent-*`, or `eightfolddemo-gademo-*` — those are gademo and match `sandbox` instead)
- `efemployer` → group ID starts with `eightfoldemployer-`
- `demo` → user email starts with `demo@`
- `directsourcepro` → group ID starts with `directsourcepro`

### Requires config/DB lookup

- **`sandbox`** → group ID contains `-sandbox.` or `-sbx.com`, OR appears in the sandbox list within `group_id_linkage_config`. Gademo groups (`eightfolddemo-ga-*`, `eightfolddemo-gaparent-*`, `eightfolddemo-gademo-*`) also match. To check ambiguous cases:
  ```
  config_name: "group_id_linkage_config"
  partition: "__default__"
  ```
  Look at `sandbox_suffixes` and `prod_to_associated_group_map` → each entry's `sandbox` array.

- **`exchanges`** → check `talent_exchange_config` partitioned by group ID. If `mode` contains `"exchange"`, `"hiring"`, or `"outplacement"`, the group is an ETX user.
  ```
  config_name: "talent_exchange_config"
  partition: "somegroup.com"
  ```

- **`aii_standalone`** → determined by whether `aii_standalone_gate` is enabled for the group (gate-checks-gate pattern).

- **`readonly`** → per-user property, not per-group. Stored as `read_only` in the `recruiter_data_json` column of the `user_login` table. Queryable via DB explorer on `prod_slave`:
  ```sql
  SELECT id, email, recruiter_data_json FROM user_login
  WHERE group_id = 'somegroup.com' AND recruiter_data_json LIKE '%read_only%'
  ```
  Rarely relevant for group-level gate checks since any group could have individual read-only users.
