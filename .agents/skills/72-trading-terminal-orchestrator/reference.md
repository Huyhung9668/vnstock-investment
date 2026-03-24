# Trading Terminal Orchestrator Reference

## Purpose

Skill nay dieu phoi toan bo terminal:

1. environment
2. data prep
3. universe scan
4. market overview
5. symbol analysis
6. trade plan
7. synthesis
8. AI narrative
9. report export
10. notification

## Runtime mapping

| Layer | Main runtime |
|---|---|
| terminal entrypoint | `scripts/run_trading_terminal.py` |
| daily pipeline | `scripts/daily_run.py` |
| skill pipeline | `services/skill_pipeline_service.py` |
| synthesis | `services/market_synthesis_service.py` |
| final writer | `services/chief_analysis_writer_service.py` |
| export | `services/report_export_service.py` |

## Core artifacts

- `artifacts/<run_id>/daily_briefing.md`
- `artifacts/<run_id>/market_analysis_report.md`
- `artifacts/<run_id>/run_summary.md`
- `artifacts/<run_id>/manifest.json`

## AI modes

- `api`: goi OpenAI API
- `file`: dung file bridge
- `off`: bo qua AI overlay

## Operational rule

- Chay cac stage co du lieu truoc.
- Danh dau stage missing/proxy/ready ro rang.
- AI chi duoc viet dua tren payload da tong hop.
