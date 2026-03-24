# Investment Copilot Reference

## 1. Purpose

This is the operational reference for the current repo. It maps:

- config inputs
- provider resolution
- normalized analysis contract
- report sections
- manifest outputs
- failure modes

Primary runtime files:

- `scripts/run_trade_plan_v2.py`
- `scripts/daily_run.py`

Primary output locations:

- `reports/`
- `reports/manifests/`

---

## 2. Config Mapping

| File | Current Role | Main Fields |
|---|---|---|
| `config/watchlist.yaml` | Daily symbol list | `symbols` |
| `config/runtime.yaml` | Runtime mode and behavior flags | `mode`, `output`, `features`, `notification`, `data_quality`, `allowed_modes` |
| `config/sources.yaml` | Provider priority and fallback | `primary`, `fallback_order`, `providers` |

### `config/watchlist.yaml`

Expected shape:

```yaml
symbols:
  - FPT
  - MWG
  - HPG
```

Used by:

- `scripts/daily_run.py`

### `config/runtime.yaml`

Current repo shape:

```yaml
mode: free

output:
  reports_dir: reports
  manifests_dir: reports/manifests

features:
  export_markdown: true
  export_html: true
  write_manifest: true
  enable_market_overview: true
  enable_deep_dive: true
  enable_trade_plan: true

notification:
  enabled: false
  channels:
    - telegram

data_quality:
  warning_threshold: medium
  fail_threshold: low

allowed_modes:
  - free
  - paid
  - paid_with_free_fallback
```

Used by:

- `scripts/daily_run.py`

### `config/sources.yaml`

Current repo shape:

```yaml
primary: free

fallback_order:
  - free

providers:
  free:
    enabled: true
    label: FreeTradePlanningProvider
  paid:
    enabled: false
    label: PaidTradePlanningProvider
```

Used by:

- `scripts/daily_run.py`
- `providers/factory.py`

---

## 3. Provider Mapping

| Provider | Repo Status | Notes |
|---|---|---|
| `free` | Implemented | `providers/free_provider.py` |
| `paid` | Planned path only | `providers/factory.py` can try to resolve it, but concrete paid provider may be absent |

### Current Resolution Rules

- `mode: free` -> use free provider only
- `mode: paid` -> try paid provider
- `mode: paid_with_free_fallback` -> try paid first, then free

Actual fallback order is built from:

- `config/runtime.yaml`
- `config/sources.yaml`

If `providers.factory` cannot build a provider, the script can still fall back to direct provider resolution for known providers.

---

## 4. Normalized Analysis Contract

Structured analysis used by the report layer is expected to include:

| Field | Required | Notes |
|---|---:|---|
| `symbol` | Yes | Uppercase symbol |
| `company` | Yes | Required company block |
| `price_summary` | Yes | Required price block |
| `financial_summary` | No | Optional, may be `None` |
| `news_summary` | No | Optional, may be `None` |
| `signals` | Yes | Can be empty dict |
| `risks` | Yes | Can be empty dict |
| `breadth_context` | No | Optional, may be `None` |
| `data_quality` | Yes | Section quality and provider health |
| `missing_sections` | Yes | Explicit list of missing optional sections |
| `provider_metadata` | Yes | Includes provider name |
| `generated_at` | Yes | Timezone-aware datetime |

Operating rule:

- if optional data is unavailable, it must be explicit
- do not silently remove the fact that the data is missing

---

## 5. Report Section Mapping

| Report Section | Current Source |
|---|---|
| `# Trade Plan: {symbol}` | `symbol`, `provider_metadata`, `generated_at` |
| `## Tom tat du lieu dau vao` | `company`, `price_summary`, optional-section state |
| `## Price overview` | `price_summary` |
| `## Technical / trend` | `signals`, `price_summary`, `breadth_context` |
| `## Financial snapshot` | `financial_summary` |
| `## News / catalysts` | `news_summary` |
| `## Danh gia chat luong du lieu` | `data_quality`, `missing_sections` |
| `## Scenario 1: Tich cuc` | derived from analysis package |
| `## Scenario 2: Trung tinh` | derived from analysis package |
| `## Scenario 3: Tieu cuc` | derived from analysis package |
| `## Canh bao thieu du lieu` | `missing_sections`, empty optional state |
| `## Ket luan trung lap` | derived from analysis package |
| `## Data coverage / Data quality` | exporter-added summary |

Rules for missing optional data:

- section must still exist
- section should show unavailable status
- report must remain valid and snapshot-testable

---

## 6. Manifest Mapping

Manifest model:

- `models/report_manifest.py`

Manifest service:

- `services/manifest_service.py`

Main fields:

| Field | Meaning |
|---|---|
| `run_id` | Unique run ID |
| `run_date` | Timezone-aware run timestamp |
| `symbols` | Symbols included |
| `mode` | Runtime mode |
| `source_used` | Provider used |
| `files_created` | Actual files written |
| `warnings` | Non-fatal issues |
| `errors` | Fatal or explicit failures |
| `duration_seconds` | Total duration |
| `data_quality_summary` | Export-ready quality summary, including degraded hints when present |

Per-symbol manifests are written by current `scripts/daily_run.py`.

---

## 7. Runtime Summary Mapping

Current daily run summary includes:

| Field | Meaning |
|---|---|
| `total` | Number of attempted symbols |
| `success` | Successful symbols |
| `failed` | Failed symbols |
| `warnings` | Total warning count |
| `duration` | Total run duration |
| `source_used` | Unique provider names used |
| `fallback_used` | Whether fallback happened |
| `files_created` | Actual report and manifest files created |

---

## 8. Failure Modes

| Failure Mode | Expected Behavior |
|---|---|
| empty payload for required block | fail that symbol explicitly |
| missing optional block | continue, mark missing section |
| invalid raw payload | fail required block or mark optional unavailable |
| timeout | fail one symbol or degrade optional block |
| missing financials | warning + degraded output |
| missing news | warning + degraded output |
| missing breadth context | degraded mode, still export report |
| notifier missing env | warning only, no batch crash |
| notifier send failure | warning only, no batch crash |
| manifest write error | explicit error, do not hide it |

---

## 9. Working Rules

- Keep field names stable.
- Keep missing optional data explicit.
- Do not invent unavailable market, financial, or news facts.
- Do not stop the whole daily batch because one symbol fails.
- Keep reports, manifests, and runtime summary aligned.
