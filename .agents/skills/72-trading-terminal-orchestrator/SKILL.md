---
name: 72-trading-terminal-orchestrator
description: Dieu phoi toan bo bo skill vnstock de tao mot Trading Terminal ca nhan voi AI. Use when can nhan mot yeu cau phan tich tong hop, can goi nhieu skill dung thu tu, ket hop Prompt va Script, va tra ve dashboard, bai phan tich, trade plan, hoac package bao cao cuoi.
---

# Trading Terminal Orchestrator

## Muc tieu

Dong vai tro dieu phoi cap cao cho toan bo he skill.

## Cach chon chuoi skill

- Setup moi truong: `10-vnstock-env-setup`
- Lay du lieu: `13-source-registry`, `14-vnstock-data-fetcher`, `20-news-crawler`, `21-report-extractor`
- Bao ve chat luong: `22-data-guardian`, `23-event-calendar`
- Boi canh thi truong: `30-macro-news`, `31-market-radar`, `32-futures-radar`, `33-flow-of-funds`, `34-sector-leadership-note`, `35-shock-cycle-reader`, `36-foreign-flow-lens`
- Chon va profile co phieu: `40-stock-scanner`, `41-technical-profiler`, `42-fundamental-profiler`, `43-chart-pattern-lab`, `44-long-candidate-selector`
- Quy hoach hanh dong: `50-account-manager`, `51-market-maker`, `52-order-engine`, `53-risk-engine`
- Thuc thi lenh: `54-entry-scaling-playbook`
- Tong hop va dong goi: `60-market-analyst`, `61-portfolio-auditor`, `70-market-synthesis`, `71-chief-analysis-writer`, `73-telegram-market-brief`, `62-professional-pdf`, `63-dashboard-publisher`

## Nguyen tac dieu phoi

- Khong goi tat ca skill neu bai toan khong can.
- Uu tien sequence ngan nhat nhung du ngu canh.
- Giu output moi buoc o dang tai su dung duoc.
- Neu mot lop du lieu thieu, van tiep tuc theo che do degraded neu bai toan cho phep.

## Dau ra

- Trading terminal workflow ro rang.
- Payload tong hop de dashboard hoac report.
- Bai phan tich cuoi cung co next actions va risk controls.
