# Investment Copilot Examples

## 1. Free Mode

### Input

`config/runtime.yaml`

```yaml
mode: free
```

`config/sources.yaml`

```yaml
primary: free
fallback_order:
  - free
```

`config/watchlist.yaml`

```yaml
symbols:
  - FPT
```

### Expected Behavior

- `scripts/daily_run.py` loads one symbol from config
- free provider is used
- analysis package is built from required company and price data
- markdown report is written under `reports/`
- html companion is written if enabled
- manifest is written under `reports/manifests/`
- final summary is printed

### Expected Notes

- optional sections may still be missing
- missing optional sections must appear in warnings or `missing_sections`
- report should still be generated if required data exists

---

## 2. Paid Enrich Mode

### Input

`config/runtime.yaml`

```yaml
mode: paid_with_free_fallback
```

`config/sources.yaml`

```yaml
primary: paid
fallback_order:
  - free
```

### Situation

- paid mode is preferred
- paid provider may not be available in the current repo

### Expected Behavior

- runtime tries paid first
- if paid provider resolution fails, runtime falls back to free
- batch should continue
- summary should show that fallback was used

### Expected Notes

- report contract must stay the same after fallback
- no field names should change because the provider changed
- if paid is unavailable, this is an operational fallback case, not a reason to invent richer data

---

## 3. Degraded Mode

### Input

One symbol where:

- company data exists
- price data exists
- `breadth_context` is missing
- optional financial or news data may be missing

### Expected Behavior

- report is still generated
- `missing_sections` is populated
- data quality is reduced
- daily run logs degraded reasons explicitly
- manifest includes warnings and data quality summary

### Expected Notes

- degraded mode is valid output
- unavailable sections must be shown as unavailable
- conclusion stays neutral and confirmation-oriented

---

## 4. Single Deep Dive

### Input

Command:

```bash
python scripts/run_trade_plan_v2.py --symbol FPT
```

### Expected Behavior

- symbol is normalized to uppercase
- one analysis package is built
- one markdown trade plan is generated
- file is saved under `reports/trade_plan_fpt.md`

### Expected Notes

- useful for debugging one symbol outside daily batch
- this is the simplest deep-dive workflow in the repo

---

## 5. Daily Run With Multiple Symbols

### Input

`config/watchlist.yaml`

```yaml
symbols:
  - FPT
  - MWG
  - HPG
  - VCB
```

### Expected Behavior

- symbols are loaded from config, not hard-coded
- pipeline runs symbol by symbol
- one symbol failure does not stop the rest
- runtime summary includes:
  - total
  - success
  - failed
  - warnings
  - duration
  - source used
  - fallback used

### Expected Notes

- this is the main operational path for the repo
- manifest and report outputs should match actual files created

---

## 6. Missing News Or Financial Data

### Situation

- provider returns required blocks
- `financial_summary` or `news_summary` is unavailable

### Expected Behavior

- related report sections still exist
- section content shows unavailable status
- warnings stay explicit
- no fabricated commentary is added

### Expected Notes

- missing optional data is normal and supported
- exporter and manifest should still complete
