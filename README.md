# VNStock Investment

Agent hỗ trợ quét, phân tích và xuất báo cáo cổ phiếu theo batch hằng ngày.

## 1. Tạo môi trường

### Windows PowerShell
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Git Bash:

```bash
python -m venv .venv
source .venv/Scripts/activate
```

## Cai dependencies

```bash
pip install -r requirements.txt
```

## Cau hinh `config/`

Cap nhat cac file sau truoc khi chay batch:

- `config/watchlist.yaml`
  - khai bao danh sach `symbols` can theo doi
- `config/runtime.yaml`
  - khai bao `mode`, `selection`, `output`, `notification`
- `config/sources.yaml`
  - khai bao provider uu tien va provider fallback

## Chay daily batch

```bash
python scripts/daily_run.py
```

Script se:

1. Doc watchlist va runtime config
2. Tai market overview / ranking neu co
3. Tao provider theo config
4. Build `AnalysisPackage` cho tung symbol
5. Render trade plan va deep dive
6. Tong hop `daily_briefing`, `market_synthesis`, `chief_analysis`
7. Export report bundle Markdown/HTML
8. Ghi manifest JSON cho run
9. In runtime summary cuoi job
10. Thu gui Telegram summary neu duoc bat trong config

## Chay Trading Terminal day du

Lenh nay la entry point de phat huy toi da bo skill/pipeline hien co:

```powershell
.\.venv\Scripts\python.exe scripts/run_trading_terminal.py
```

Mac dinh script se:

1. load `.env`
2. chay `universe_scan`
3. build `market_overview`
4. chay `daily_run`
5. tong hop narrative voi `market_synthesis` + `chief_analysis`
6. export `daily_briefing` va `market_analysis_report`

Neu muon bat AI bang OpenAI API:

```powershell
$env:OPENAI_API_KEY="your_openai_api_key"
$env:AI_ANALYSIS_ENABLED="true"
.\.venv\Scripts\python.exe scripts/run_trading_terminal.py --ai-mode api --openai-model gpt-4.1-mini
```

Neu muon dung file bridge:

```powershell
.\.venv\Scripts\python.exe scripts/run_trading_terminal.py --ai-mode file
```

Mot so tuy chon:

- `--skip-scan`: bo qua universe scan, dung lai du lieu da co
- `--skip-overview`: bo qua rebuild market overview
- `--config-dir <path>`: doi thu muc config

## Bat Telegram notification

Trong `config/runtime.yaml`:

```yaml
notification:
  telegram: true
```

Tao file `.env` tu `.env.example` hoac set env trong shell:

```powershell
$env:TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
$env:TELEGRAM_CHAT_ID="your_telegram_chat_id"
```

## Chay AI phan tich bang file bridge de dung Codex tam thoi

Neu chua muon goi API, co the bat che do file bridge:

```powershell
$env:AI_ANALYSIS_ENABLED="true"
$env:AI_ANALYSIS_MODE="file"
$env:AI_ANALYSIS_PROMPT_FILE="artifacts/ai_prompt.json"
$env:AI_ANALYSIS_RESPONSE_FILE="artifacts/ai_response.json"
$env:OPENAI_MODEL="codex-local-bridge"
```

Khi chay `python scripts/daily_run.py`, pipeline se:

1. ghi prompt AI vao `artifacts/ai_prompt.json`
2. doc ket qua JSON tu `artifacts/ai_response.json`

Luot dung tam voi Codex:

1. chay pipeline sau khi da tao `artifacts/ai_response.json`
2. hoac mo `artifacts/ai_prompt.json`, bao Codex viet dung JSON schema vao `artifacts/ai_response.json`, roi chay lai pipeline

Che do nay la semi-manual bridge, khong phai local API server.

Neu `notification.telegram = true` nhung thieu env, job van tiep tuc va chi ghi warning.

Neu request Telegram loi, job van khong crash.

## Doc `reports/` va manifest

Trong `reports/`:

- `trade_plan_<symbol>.md`: ban Markdown de review nhanh

Trong thu muc manifest da cau hinh:

- `manifest_<symbol>_<run_id>.json`: log van hanh cho tung symbol
- file nay chua `files_created`, `warnings`, `errors`, `duration_seconds`, `data_quality_summary`

Trong `artifacts/<run_id>/` co them cac file tong hop:

- `daily_briefing.md`
- `market_analysis_report.md`
- `run_summary.md`
- ban HTML tuong ung cho tung file

## Troubleshooting

- `ModuleNotFoundError`
  - kiem tra da activate `.venv` va da `pip install -r requirements.txt`
- `vnstock` tra du lieu thieu
  - report van co the tao o che do degraded; kiem tra `missing_sections` trong report hoac manifest
- `paid` provider loi
  - chuyen `mode` sang `free` hoac dung provider fallback
- Telegram khong gui duoc
  - kiem tra `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `notification.telegram`
