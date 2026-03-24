---
name: 10-vnstock-env-setup
description: Setup va kiem tra moi truong chay cho repo vnstock. Use when can xac minh Python, venv, dependencies, bien moi truong, config dau vao, duong dan output, hoac can chuan bi workspace truoc khi chay pipeline.
---

# VNStock Env Setup

## Muc tieu

Dam bao moi truong chay san sang truoc khi pipeline lay du lieu va phan tich.

## Thuc hien

- Kiem tra `.venv`, `requirements.txt`, `pyproject.toml`.
- Kiem tra `.env`, `.env.example`, cac bien nhu `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
- Kiem tra su ton tai cua `config/`, `data/`, `artifacts/`, `reports/`, `manifests/`.
- Dung `scripts/env_check.py` hoac `scripts/main.py` khi can smoke check nhanh.

## Dau ra

- Danh sach loi cau hinh.
- Danh sach thieu dependencies hay env.
- Xac nhan workspace san sang cho batch run.
