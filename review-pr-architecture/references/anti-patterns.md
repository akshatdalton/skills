# Common Anti-Patterns Reference

## N×M compound identifier
```python
# ❌ N products × M providers = N×M enum values
class ConnectorName(StrEnum):
    BILLING_GOOGLE = 'billing_google'
    HR_GOOGLE = 'hr_google'

# ✅ N + M values
class ProductName(StrEnum):
    BILLING = 'billing'
class ConnectorType(StrEnum):
    GOOGLE = 'google'
```
Red flag: enum values where removing one segment gives duplicate.

## Test config leaking into production
```python
# ❌
def get_default_db(self): return 'test'
def tablename(self): return 'integrations_test_2'
```

## Hardcoded environment values
```python
# ❌
return 'https://alice.dev.internal.company.com/connectors/oauth'
# ✅
return settings.oauth_redirect_base_url + '/connectors/oauth'
```

## Missing transaction safety
```python
# ❌ Row saved before external call that can fail
integration.save()
tokens = exchange_code_for_token(code)   # failure → partial state

# ✅
tokens = exchange_code_for_token(code)
integration.save()
```

## Unconditional destructive operations
```python
# ❌ No guard on existing data
delete_all_integrations(org_id, connector_type)
create_new_integration()
```

## Unnecessary lazy singleton
```python
# ❌ lru_cache(maxsize=1) on zero-arg = permanent singleton with extra ceremony
@lru_cache(maxsize=1)
def _get_client(): return SomeClient(settings.base_url)

# ✅ Module-level variable
_client = SomeClient(settings.base_url)
```

## Search tips
- **N×M**: enum values where removing one segment gives duplicate
- **Test bleed**: grep `'test'` in return values, `_test` in table names
- **Hardcoded env**: grep `https://`, `.dev.`, `.staging.`, personal usernames
- **Naming lies**: read what name implies, check what code does
- **Future cost**: state cost to fix now vs later
