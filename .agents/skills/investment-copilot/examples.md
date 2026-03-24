# Investment Copilot Examples

## Free mode

### Input

```yaml
# config/runtime.yaml
mode: free
export_html: true
write_manifest: true
```

### Expected behavior

- Doc watchlist tu `config/watchlist.yaml`
- Dung free provider
- Tao Markdown va HTML trong `reports/`
- Ghi manifest vao `reports/manifests/`

## Enriched mode with fallback

### Input

```yaml
# config/runtime.yaml
mode: enriched
```

```yaml
# config/sources.yaml
providers:
  primary: paid
  fallback_order:
    - free
```

### Expected behavior

- Thu provider `paid`
- Neu chua ho tro, ghi warning
- Fallback sang `free`
- Batch van tiep tuc

## Degraded mode

### Situation

- Financials hoac news khong co

### Expected behavior

- Report van duoc tao
- Section lien quan hien unavailable
- Manifest co `degraded_mode`

## Partial batch failure

### Situation

- `FPT` thanh cong
- `MWG` fail
- `HPG` thanh cong

### Expected behavior

- Batch khong dung giua chung
- Summary tang `failed_count`
- Manifest luu warning/error ro rang

## Notification disabled

### Input

```yaml
# config/sources.yaml
telegram:
  enabled: false
```

### Expected behavior

- Khong gui Telegram
- Khong fail batch
- Summary va manifest van duoc tao
