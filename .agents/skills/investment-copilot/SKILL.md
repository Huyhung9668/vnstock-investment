# Investment Copilot Skill

## Scope

Skill nay ho tro van hanh investment copilot theo watchlist hang ngay trong repo nay.

## Runtime files

- `scripts/daily_run.py`
- `scripts/run_trade_plan_v2.py`
- `config/watchlist.yaml`
- `config/runtime.yaml`
- `config/sources.yaml`

## Outputs

- `reports/market_overview.md`
- `reports/trade_plan_<symbol>.md`
- `reports/deep_dive_<symbol>.md`
- HTML companion trong `reports/`
- manifest JSON trong `reports/manifests/`

## Rules

- Khong hard-code symbol
- Khong fabricate du lieu thieu
- Missing optional data phai duoc ghi ro
- Mot symbol fail khong duoc lam batch dung giua chung
- Notification phai fail-safe

## Modes

### free
- Use only free provider
- Allow degraded output
- Skip expensive enrichment

### enriched
- Try to include financials and news
- Fallback to free neu chua co paid provider thuc su

## Degradation policy

Neu data quality thap:

- van tao report
- danh dau degraded
- dua warning vao manifest va summary

## Observability

Moi run can co:

- summary
- report files
- manifest
- warning ro rang neu co fallback hoac missing data
