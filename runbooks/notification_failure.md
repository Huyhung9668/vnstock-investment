# Notification Failure Playbook

## Problem

Bao cao da chay xong nhung Telegram hoac email khong gui duoc.

## Checks

1. Kiem tra env:
   - `TELEGRAM_ENABLED`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
2. Kiem tra log warning tu notifier.
3. Kiem tra pipeline co van xuat `manifest` va report khong.

## Actions

1. Neu notification khong quan trong, giu batch tiep tuc va doc artifact tren disk.
2. Kiem tra token/chat id va thu gui lai thu cong.
3. Neu chay CI, doi chieu GitHub secrets.
4. Neu chi loi kenh thong bao, khong rerun toan bo scan neu artifact da co.

## Never

- khong de notification failure lam batch fail
- khong ghi de artifact chi vi notifier loi
