# Report Missing Playbook

## Problem

Sau khi chay pipeline, khong thay `daily_briefing`, `market_analysis_report`, hoac mot phan artifact mong doi.

## Checks

1. Kiem tra `artifacts/<run_id>/manifest.json`.
2. Kiem tra `files_created` trong manifest.
3. Kiem tra warning `*_markdown` hoac `*_html` trong log.
4. Kiem tra output dir co ghi duoc hay khong.

## Actions

1. Chay lai voi `python scripts/daily_run.py` de xac nhan pipeline co qua exporter.
2. Neu scan qua nang, chay `scripts/run_trading_terminal.py --skip-scan --skip-overview`.
3. Neu chi thieu narrative AI, kiem tra `AI_ANALYSIS_*` env.
4. Neu thieu mot phan table/report, kiem tra payload co rong hay khong truoc exporter.

## Expected files

- `daily_briefing.md`
- `market_analysis_report.md`
- `run_summary.md`
- `manifest.json`

## Never

- khong ket luan exporter loi khi chua kiem tra `manifest.json`
- khong xoa artifact cu khi chua doi chieu run id
