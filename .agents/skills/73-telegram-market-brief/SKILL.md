---
name: 73-telegram-market-brief
description: Dong goi bai nhan dinh thi truong thanh brief Telegram ngan gon, tieng Viet tu nhien, de doc tren dien thoai va co the tach thanh nhieu tin nhan neu dai. Use when can can gui ket qua cuoi cung len Telegram ma van giu du boi canh thi truong, top 5 ma, va ke hoach hanh dong.
---

# Telegram Market Brief

## Muc tieu

Viet lai payload tong hop thanh thong diep Telegram mach lac, de doc nhanh, khong vo nghia, khong lap lai telemetry, va khong bi vo dinh dang.

## Cau truc uu tien

- Mo dau: trang thai thi truong va posture hanh dong.
- Lop boi canh: vi mo, dong tien, nhom dan dat, khoi ngoai.
- Top 5 co phieu: moi ma 1-2 cau, co ly do va vung mua.
- Ke hoach hanh dong: giai ngan theo nhip, khong duoi gia, dieu kien vo hieu.
- Ket bai: diem can theo doi o phien toi.

## Nguyen tac viet

- Uu tien tieng Viet day du dau, van phong, de hieu.
- Tranh tu kho doc nhu telemetry, field name, hay raw label ky thuat.
- Neu ban tin dai, chu dong tach thanh 2-3 tin nhan hop ly.
- Luon xep thong tin tu thi truong chung den co phieu cu the.

## Dau ra

- Telegram brief san sang gui.
- Phien ban 1 chunk hoac multi-chunk tuy do dai.
- Output cuoi cho `notifiers/telegram.py` va `63-dashboard-publisher`.
