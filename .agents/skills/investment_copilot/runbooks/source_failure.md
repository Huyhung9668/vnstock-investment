# Source Failure Runbook

## Goal

Keep the pipeline running when possible, and make failures explicit when required data is not usable.

## Timeout

### Symptoms

- one symbol stalls or raises timeout-related exception
- no report for that symbol

### Action

- fail that symbol only if required data was blocked
- continue with the next symbol
- keep the timeout message in warnings or errors

## Empty Payload

### Symptoms

- provider returns empty required data
- normalized block cannot be built

### Action

- if required block is empty, fail that symbol explicitly
- if optional block is empty, mark it unavailable and continue

## Invalid Schema

### Symptoms

- payload shape is not what normalization expects
- required keys cannot be derived safely

### Action

- fail required block explicitly
- do not guess or fabricate values
- keep the failure visible in logs

## Missing Optional Data

### Symptoms

- no financial summary
- no news summary
- no breadth context

### Action

- continue in degraded mode
- make missing sections explicit
- keep report sections visible with unavailable state

## Batch Rule

- never crash the full daily run because one symbol failed
- only fail the whole batch for startup or config problems

## Operator Checklist

1. Check whether the issue affects one symbol or all symbols.
2. Confirm config values are correct.
3. Confirm required company and price blocks are available.
4. Check degraded reasons in daily run logs.
5. Inspect generated manifest and report files.
6. Retry one symbol only if needed.
