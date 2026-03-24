---
name: 63-dashboard-publisher
description: Dong goi va cong bo ket qua phan tich len dashboard, HTML summary, artifact bundle, hoac kenh chia se noi bo. Use when can bien output cua pipeline thanh trang tong hop de doc nhanh va theo doi hang ngay.
---

# Dashboard Publisher

## Muc tieu

Dua ket qua phan tich vao mot format de theo doi lap lai moi ngay.

## Thuc hien

- Lay payload tu `70-market-synthesis` hoac `71-chief-analysis-writer`.
- Tao dashboard blocks: headline, market regime, top picks, risks, next actions.
- Dam bao output phu hop voi `artifacts/`, `reports/`, HTML summary.

## Dau ra

- Dashboard-ready payload.
- HTML/Markdown summary.
- Goi output san sang cho `62-professional-pdf`.
