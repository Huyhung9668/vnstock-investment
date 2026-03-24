---
name: 14-vnstock-data-fetcher
description: Lay du lieu gia, ho so doanh nghiep, tai chinh, breadth va dataset can thiet tu he sinh thai vnstock. Use when can fetch raw market data, normalize output, luu cache, hoac chuan bi input cho scanner, profiler va report pipeline.
---

# VNStock Data Fetcher

## Muc tieu

Dong vai tro "muscle" lay du lieu cho trading terminal.

## Thuc hien

- Doc config source truoc khi goi du lieu.
- Uu tien dung script trong `scripts/` de lay va luu du lieu co cau truc.
- Chuan hoa ten cot, symbol, timezone, date range.
- Neu source fail thi tra ve loi ro rang de skill khac co the fallback.

## Tai nguyen

- Khi can workflow chi tiet, doc `references/data-fetching.md`.
- Khi can chay script mau, dung `scripts/fetch_price_window.py`.

## Dau ra

- Raw dataset hoac normalized dataset.
- Metadata ve source, thoi gian fetch, warning.
