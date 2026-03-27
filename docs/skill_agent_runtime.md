# Skill Agent Runtime

## Mục tiêu

Biến hệ thống từ pipeline Python cố định thành một runtime theo kiểu agent skill-based:

- có `registry` cho từng skill,
- có `planner` chọn chuỗi skill theo objective,
- có `runtime context` giữ output từng bước,
- và có `script` riêng để chạy agent theo mục tiêu.

## Các thành phần mới

- `services/agent_skill_runtime.py`: data structures cho skill, metadata, context, step result.
- `services/agent_skill_loader_service.py`: đọc metadata từ `.agents/skills/*/SKILL.md`.
- `services/agent_planner_service.py`: planner chọn plan từ objective.
- `services/agent_skill_registry_service.py`: registry + handlers + runner.
- `scripts/run_skill_agent.py`: entry point chạy agent runtime.

## Luồng hoạt động

1. Nhận `objective`.
2. Planner chọn chain skill.
3. Registry map từng skill sang handler Python.
4. Runtime chạy từng skill và lưu output vào shared context.
5. Xuất artifact `agent_skill_runtime.json` vào thư mục run.

## Ví dụ chạy

```powershell
python scripts/run_skill_agent.py --config-dir config/test50 --objective "Phân tích VNINDEX, tin tức, top 5 LONG và kế hoạch entry" --send-telegram
```

## Ý nghĩa kiến trúc

Điểm khác với pipeline cũ là flow không còn chỉ là `script -> service -> report` cố định, mà đã có:

- lớp lập kế hoạch theo mục tiêu,
- lớp registry ánh xạ capability,
- lớp runtime context dùng lại output giữa các skill,
- và artifact riêng để trace từng skill đã chạy.
