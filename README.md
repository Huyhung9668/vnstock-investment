# VNStock Investment

Agent hỗ trợ quét, phân tích và xuất báo cáo cổ phiếu theo batch hằng ngày.

## Tạo môi trường

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Git Bash

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

## Cấu hình `config/`

Cập nhật các file sau trước khi chạy:

- `config/watchlist.yaml`: danh sách `symbols` cần theo dõi
- `config/runtime.yaml`: `mode`, `selection`, `output`, `notification`
- `config/sources.yaml`: provider ưu tiên và thứ tự fallback

## Chạy daily batch

```bash
python scripts/daily_run.py
```

Pipeline sẽ:

1. Đọc watchlist và runtime config
2. Tải market overview hoặc ranking nếu có
3. Tạo provider theo config
4. Build `AnalysisPackage` cho từng symbol
5. Render trade plan và deep dive
6. Tổng hợp `daily_briefing`, `market_synthesis`, `chief_analysis`
7. Export report bundle Markdown/HTML
8. Ghi manifest JSON cho run
9. In runtime summary cuối job
10. Thử gửi Telegram summary nếu được bật

## Chạy Trading Terminal đầy đủ

Entry point khuyến nghị:

```powershell
.\.venv\Scripts\python.exe scripts/run_trading_terminal.py
```

Mặc định repo nên chạy theo local-first. Ví dụ với Ollama:

```powershell
ollama serve
ollama pull qwen2.5:14b
.\.venv\Scripts\python.exe scripts/run_trading_terminal.py --ai-mode local --openai-model qwen2.5:14b
```

Nếu muốn dùng file bridge:

```powershell
.\.venv\Scripts\python.exe scripts/run_trading_terminal.py --ai-mode file
```

Nếu thật sự cần cloud API:

```powershell
$env:OPENAI_API_KEY="your_openai_api_key"
$env:AI_ANALYSIS_ENABLED="true"
.\.venv\Scripts\python.exe scripts/run_trading_terminal.py --ai-mode api --openai-model gpt-4.1-mini
```

Local mode sẽ ưu tiên:

- `LOCAL_LLM_BASE_URL` hoặc `OLLAMA_BASE_URL` hoặc `OPENAI_BASE_URL`
- fallback cuối cùng: `http://localhost:11434/v1`
- `LOCAL_LLM_MODEL` hoặc `OLLAMA_MODEL` hoặc `OPENAI_MODEL`
- fallback cuối cùng: `qwen2.5:14b`

Một số tùy chọn:

- `--skip-scan`: bỏ qua universe scan, dùng lại dữ liệu cũ
- `--skip-overview`: bỏ qua rebuild market overview
- `--config-dir <path>`: đổi thư mục config

## Mô hình skill hiện tại

Pipeline đang đi theo hướng một agent chính, nhiều skill-stage tái sử dụng:

- lấy data và chuẩn hóa provider
- news context
- macro context
- stock scanner
- technical profiler
- chart pattern lab
- order engine
- risk engine
- portfolio auditor
- chief analysis và report export

Mục tiêu là mỗi skill chỉ làm một việc rõ ràng, trả về payload dùng lại được, và diễn giải bằng tiếng Việt dễ hiểu.

## Telegram notification

Trong `config/runtime.yaml`:

```yaml
notification:
  telegram: true
```

Set env:

```powershell
$env:TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
$env:TELEGRAM_CHAT_ID="your_telegram_chat_id"
```

## File bridge cho AI

Nếu chưa muốn gọi API hoặc local server, có thể dùng file bridge:

```powershell
$env:AI_ANALYSIS_ENABLED="true"
$env:AI_ANALYSIS_MODE="file"
$env:AI_ANALYSIS_PROMPT_FILE="artifacts/ai_prompt.json"
$env:AI_ANALYSIS_RESPONSE_FILE="artifacts/ai_response.json"
$env:OPENAI_MODEL="codex-local-bridge"
```

Khi chạy `python scripts/daily_run.py`, pipeline sẽ:

1. Ghi prompt AI vào `artifacts/ai_prompt.json`
2. Đọc kết quả JSON từ `artifacts/ai_response.json`

## Output chính

Trong `reports/`:

- `trade_plan_<symbol>.md`

Trong `artifacts/<run_id>/`:

- `daily_briefing.md`
- `market_analysis_report.md`
- `run_summary.md`
- các file HTML tương ứng

## Troubleshooting

- `ModuleNotFoundError`: kiểm tra đã activate `.venv` và cài `requirements.txt`
- dữ liệu Vnstock thiếu: pipeline vẫn có thể chạy degraded, xem `missing_sections` trong report hoặc manifest
- provider lỗi: chuyển `mode` sang `free` hoặc dùng fallback
- Telegram không gửi được: kiểm tra `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `notification.telegram`
