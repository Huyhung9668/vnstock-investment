# Investment Copilot Reference

## Runtime map

| Item | Path | Purpose |
|---|---|---|
| Watchlist | `config/watchlist.yaml` | Danh sach symbol cho batch run |
| Runtime config | `config/runtime.yaml` | Bat/tat HTML, manifest, mode |
| Source config | `config/sources.yaml` | Chon provider chinh, fallback va notifier |
| Daily batch | `scripts/daily_run.py` | Orchestrate market overview, deep dive, trade plan |
| Single symbol run | `scripts/run_trade_plan_v2.py` | Tao trade plan cho 1 symbol |
| Reports | `reports/` | Markdown va HTML output |
| Manifests | `reports/manifests/` | JSON log van hanh |

## Config schema

### `config/watchlist.yaml`

```yaml
symbols:
  - FPT
  - MWG
  - HPG
```

### `config/runtime.yaml`

```yaml
mode: free
export_html: true
write_manifest: true
```

### `config/sources.yaml`

```yaml
providers:
  primary: free
  fallback_order:
    - free

telegram:
  enabled: false
  token: ""
  chat_id: ""
```

## Minimum data contract

Moi payload can co cac thanh phan toi thieu:

- `source`
- `timestamp`
- `symbol` hoac `scope`

Optional data thieu phai duoc the hien ro, khong duoc am tham bo di.

## Report map

| Output | Source |
|---|---|
| Market overview | `scripts/daily_run.py` batch context |
| Deep dive | `scripts/daily_run.py` + symbol context |
| Trade plan | `services/analysis_builder.py` + `services/trade_plan_service.py` |
| Data quality | `services/report_exporter.py` |
| Manifest | `services/manifest_service.py` |

## Failure modes

| Failure | Expected handling |
|---|---|
| Provider unsupported | warning + fallback provider |
| Empty payload | explicit error cho section required |
| Missing financial/news | van render report, mark unavailable |
| Notification missing token | skip an toan, khong fail batch |
| Symbol fail | continue symbol tiep theo, tang `failed_count` |

## Summary fields

Runtime summary cuoi job gom:

- `total_symbols`
- `success_count`
- `failed_count`
- `warning_count`
- `degraded_count`
- `files_created`
