# Architecture

## Goal

Build a single main investment assistant that uses Vnstock data to produce clear, repeatable analysis outputs without requiring a cloud AI API.

## Current shape

- `scripts/run_trading_terminal.py` là entry point local-first cho toàn bộ terminal flow.
- `scripts/run_stock_agent.py` là runner theo layer để debug hoặc chạy từng phần.
- `data/` lưu raw data và derived data.
- `services/` chứa các skill-stage có thể tái sử dụng.
- `reports/` và `artifacts/` chứa output cuối cùng.
- `docs/` lưu quy tắc vận hành, flow và data contracts.

## Design principles

- Giữ một agent chính, không chia nhỏ thành nhiều agent con.
- Tách rõ data fetching, analysis skills, action planning và reporting.
- Ưu tiên local-first: `local` hoặc `file bridge` là lựa chọn mặc định cho AI overlay.
- Mỗi skill nên có một trách nhiệm rõ ràng và trả về payload dùng lại được.
- Narrative phải có ngữ cảnh: giải thích chuyện gì đang xảy ra, tại sao quan trọng, và cần làm gì tiếp theo.

## Expanded modular skills

- `34-sector-leadership-note`: đọc nhóm dẫn dắt và độ bền luân chuyển ngành.
- `35-shock-cycle-reader`: diễn giải pha sốc tin, panic, rũ bỏ, tích lũy lại.
- `36-foreign-flow-lens`: kiểm tra khối ngoại và dòng tiền lớn có ủng hộ xu hướng hay không.
- `44-long-candidate-selector`: lọc mặc định theo hướng LONG, loại bớt mã suy yếu.
- `54-entry-scaling-playbook`: biến insight thành kế hoạch giải ngân nhiều nhịp.
- `73-telegram-market-brief`: gói báo cáo thành bản tin Telegram tiếng Việt tự nhiên.

## Suggested terminal flow

- `14-vnstock-data-fetcher` lấy dữ liệu giá và thanh khoản.
- `20-news-crawler` và `30-macro-news` dựng bối cảnh vĩ mô.
- `31-market-radar`, `33-flow-of-funds`, `34-sector-leadership-note`, `36-foreign-flow-lens` xác nhận trạng thái thị trường.
- `40-stock-scanner` và `44-long-candidate-selector` chọn top 5 mặc định theo hướng mua lên.
- `41-technical-profiler`, `43-chart-pattern-lab`, `54-entry-scaling-playbook` tạo vùng mua và kế hoạch giải ngân.
- `70-market-synthesis`, `71-chief-analysis-writer`, `73-telegram-market-brief` viết bài cuối và gửi Telegram.
