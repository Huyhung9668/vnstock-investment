# Daily Run Runbook

## Goal

Run the watchlist pipeline safely, generate reports, write manifests, and end with a usable batch summary.

## Preconditions

- dependencies are installed
- config files exist:
  - `config/watchlist.yaml`
  - `config/runtime.yaml`
  - `config/sources.yaml`
- output directories are writable

## Run Command

```bash
python scripts/daily_run.py
```

## What The Script Does

1. Load config files.
2. Read symbols from `config/watchlist.yaml`.
3. Resolve runtime mode from `config/runtime.yaml`.
4. Resolve provider order from `config/sources.yaml`.
5. For each symbol:
   - build analysis package
   - render trade plan
   - export markdown
   - export html companion if enabled
   - write manifest
6. Print final summary.
7. Try Telegram notification at the end if env is present.

## Healthy Run

A healthy run usually means:

- `failed=0`
- expected symbols were attempted
- report files exist in `reports/`
- manifest files exist in `reports/manifests/`
- warnings are understood, not silent

## If One Symbol Fails

- do not stop the whole batch
- inspect the per-symbol logs
- check whether fallback was used
- rerun one symbol separately if needed

## Quick Checks After Run

- open `reports/`
- open `reports/manifests/`
- confirm newest files match the current run
- read the printed summary
- if degraded warnings exist, confirm the missing sections are expected
