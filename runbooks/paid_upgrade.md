# Paid Upgrade Playbook

## When to upgrade
- missing financial data frequently
- need news sentiment
- data quality below threshold

## Action
- switch provider to paid
- enable enriched mode

## Config change
config/sources.yaml:
  providers:
    primary: paid
