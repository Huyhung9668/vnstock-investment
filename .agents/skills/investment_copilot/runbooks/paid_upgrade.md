# Paid Upgrade Runbook

## Goal

Move from free-only operation to paid-first operation without breaking the current report contract.

## When To Upgrade

Consider paid-first mode when:

- free mode often misses financial data
- free mode often misses news data
- too many runs are degraded
- fallback to free is acceptable if paid fails

## Config Changes

Update `config/runtime.yaml`:

```yaml
mode: paid_with_free_fallback
```

Update `config/sources.yaml`:

```yaml
primary: paid
fallback_order:
  - free
```

## Validation

1. Confirm paid provider is actually implemented and importable.
2. Run one symbol first.
3. Confirm report files are still created.
4. Confirm field names and report sections did not change.
5. Confirm fallback to free still works.

## If Paid Fails

- fallback to free if configured
- keep warning explicit
- do not block the whole batch unless no provider path works

## Rollback

Return to:

`config/runtime.yaml`

```yaml
mode: free
```

`config/sources.yaml`

```yaml
primary: free
fallback_order:
  - free
```

## Success Criteria

- paid-first mode resolves correctly
- reports still render with the same contract
- manifests still match files created
- fallback remains safe
