# Investment Copilot Runbooks

## Daily run

```bash
python scripts/daily_run.py
```

Kiem tra:

- `reports/`
- `reports/manifests/`
- console summary

## Khi provider loi

- Kiem tra `config/sources.yaml`
- Xem warning fallback trong summary hoac manifest
- Neu provider chinh chua ho tro, de `free` la fallback

## Khi data bi thieu

- Khong duoc bo sung du lieu gia
- Cho phep degraded mode
- Kiem tra `missing_sections` va `data_quality_summary`

## Khi notifier loi

- Kiem tra `telegram.enabled`
- Kiem tra token/chat_id hoac env
- Batch van phai hoan thanh du report va manifest
