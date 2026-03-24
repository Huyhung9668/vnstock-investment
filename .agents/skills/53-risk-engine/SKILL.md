---
name: 53-risk-engine
description: Danh gia rui ro giao dich va rui ro he thong truoc khi bien insight thanh hanh dong. Use when can tinh scenario risk, event risk, liquidity risk, portfolio risk, stop invalidation quality, va can dat muc uu tien phong thu.
---

# Risk Engine

## Muc tieu

Bien rui ro thanh mot lop quyet dinh ro rang truoc execution.

## Thuc hien

- Tong hop market risk, event risk, symbol risk, liquidity risk.
- Danh gia chat luong invalidation va khong gian stop.
- Gan risk tier cho tung setup va toan danh muc.

## Dau ra

- Risk tier: low, medium, high, avoid.
- Dieu kien giam size, hoan lenh, hoac dung quan sat.
- Input cho `52-order-engine`, `61-portfolio-auditor`, `70-market-synthesis`.
