# API Rate Limit Playbook

## Problem

Pipeline gap rate limit khi quet universe, goi API AI, hoac lay du lieu tu provider.

## Symptoms

- request bi tu choi
- response cham bat thuong
- log co chu `rate limit`, `429`, `quota`, `retry later`

## Actions

1. Giam `top_n`, `batch_size`, hoac chuyen `selection.mode` sang `watchlist`.
2. Tang `batch_sleep_seconds`, `request_delay_seconds` trong `config/universe.yaml` hoac `config/runtime.yaml`.
3. Dung `--skip-scan` de tai su dung du lieu da co neu phan universe scan la nut that.
4. Neu la AI overlay, tam chuyen sang `--ai-mode off` hoac `--ai-mode file`.
5. Neu can chay deu hang ngay, nang cap API tier hoac tach lich scan va lich phan tich.

## Never

- khong spam retry khong gioi han
- khong gia lap du lieu AI neu response khong ve
- khong cho toan bo batch crash neu co the fallback
