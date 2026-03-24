# Daily Run Runbook

## Muc tieu

Batch run hang ngay doc watchlist, tao market overview, deep dive, trade plan, xuat report Markdown/HTML, ghi manifest va gui thong bao neu notifier duoc bat.

## File lien quan

- `config/watchlist.yaml`
- `config/runtime.yaml`
- `config/sources.yaml`
- `scripts/daily_run.py`
- `reports/`
- `reports/manifests/`

## Chay local

```bash
python scripts/daily_run.py
```

## Truoc khi chay

- Kiem tra `config/watchlist.yaml` co `symbols`
- Kiem tra `config/runtime.yaml` co `mode`, `export_html`, `write_manifest`
- Kiem tra `config/sources.yaml` co `providers.primary`, `providers.fallback_order`
- Neu bat Telegram notifier, cung cap `telegram.token` va `telegram.chat_id` hoac env tuong ung

## Luong chay

1. Load config tu `config/`
2. Tao market overview cho ca batch
3. Loop qua `watchlist.symbols`
4. Thu provider chinh va fallback neu can
5. Tao trade plan Markdown cho tung symbol
6. Tao HTML companion tu Markdown
7. Tao deep dive Markdown/HTML cho tung symbol
8. Tong hop runtime summary
9. Gui thong bao neu notifier duoc bat
10. Ghi manifest vao `reports/manifests/`

## Output ky vong

- `reports/market_overview.md`
- `reports/market_overview.html`
- `reports/trade_plan_<symbol>.md`
- `reports/trade_plan_<symbol>.html`
- `reports/deep_dive_<symbol>.md`
- `reports/deep_dive_<symbol>.html`
- `reports/manifests/daily_run_<timestamp>_<run_id>.json`

## Cach doc ket qua

- Markdown la ban doc nhanh
- HTML la ban chia se de doc tren trinh duyet
- Manifest la log van hanh:
  - `files_created`
  - `warnings`
  - `errors`
  - `data_quality_summary`
  - `degraded_mode`

## Tieu chi run khoe

- `failed_count = 0`
- `warning_count` thap hoac bang 0
- `files_created` co report Markdown/HTML va manifest
- `data_quality_summary.degraded_mode = false`

## Khi nao can dung lai

- Config khong hop le
- Khong co symbol hop le trong watchlist
- Tat ca provider deu that bai
- Khong ghi duoc report hoac manifest

## Sau khi chay

- Kiem tra `reports/` co du file moi
- Kiem tra `reports/manifests/` co manifest moi
- Neu co `failed_count > 0`, mo warning trong manifest de xem symbol nao fail
- Neu co degraded mode, uu tien bo sung du lieu cho symbol bi thieu
