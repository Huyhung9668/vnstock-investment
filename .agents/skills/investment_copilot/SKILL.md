# Investment Copilot Skill

## 1. Purpose

This skill supports the current `vnstock-investment` repo for:

- market overview support from shared market context when available
- deep dive analysis for one symbol
- trade plan generation
- daily watchlist run

It must stay aligned with the repo's existing pipeline:

- `providers/`
- `services/`
- `scripts/run_trade_plan_v2.py`
- `scripts/daily_run.py`
- `reports/`
- `reports/manifests/`

---

## 2. Supported Modes

### Single Symbol

Use for one symbol when debugging or reviewing one case:

- build normalized analysis data
- render markdown trade plan
- export report for one symbol

Main entrypoint:

- `scripts/run_trade_plan_v2.py`

### Daily Run

Use for watchlist processing:

- load symbols from `config/watchlist.yaml`
- resolve mode and provider order from config
- run symbol-by-symbol
- continue when one symbol fails
- write reports and manifests
- print final runtime summary

Main entrypoint:

- `scripts/daily_run.py`

### Market Overview

Market overview is a supported output mode at repo level through:

- runtime feature flags in `config/runtime.yaml`
- optional breadth or shared market context in analysis data

If market-wide context is missing, the skill must state that it is unavailable.

### Deep Dive

Deep dive means one-symbol structured analysis using:

- company profile
- price summary
- optional financial summary
- optional news summary
- optional breadth context
- data quality and missing sections

### Trade Plan

Trade plan is the main rendered output and must remain:

- structured
- neutral
- explicit about missing data
- scenario-based instead of absolute recommendation

---

## 3. Expected Data Contract

The skill should assume the normalized analysis package contains at least:

- `symbol`
- `company`
- `price_summary`
- `financial_summary`
- `news_summary`
- `signals`
- `risks`
- `breadth_context`
- `data_quality`
- `missing_sections`
- `provider_metadata`
- `generated_at`

Required for a valid trade-plan path:

- company data
- price summary

Optional but expected when available:

- financial summary
- news summary
- breadth context

Provider payloads and service results must keep stable field names already used by the repo.

---

## 4. Operating Rules

- Do not fabricate missing data.
- If a section is missing, say it is missing or unavailable.
- Missing optional data must not silently disappear from the interpretation.
- One symbol failure must not crash the whole daily batch.
- Warnings and degraded behavior must stay explicit.
- Keep output compatible with current exporter and manifest flow.

Core repo rule:

- if data is missing, report the gap clearly
- do not invent facts to make the report look complete

---

## 5. Degraded Behavior

The skill should still generate output when:

- financial data is missing
- news data is missing
- breadth context is missing

Typical degraded signals in this repo:

- `missing_sections` is not empty
- `data_quality.overall_status` is lower
- daily run logs degraded reasons

Degraded output must:

- still produce report files when possible
- include warnings
- keep required sections visible
- mark unavailable sections explicitly

---

## 6. Config Inputs

The skill should expect these config files:

- `config/watchlist.yaml`
- `config/runtime.yaml`
- `config/sources.yaml`

Use them as follows:

- `watchlist.yaml`: source of symbols for batch runs
- `runtime.yaml`: runtime mode, output dirs, features, notification, data quality thresholds
- `sources.yaml`: primary provider and fallback order

Do not hard-code symbols or runtime mode in scripts that are meant for batch execution.

---

## 7. Output Expectations

Primary outputs in the repo:

- markdown reports in `reports/`
- html companion files in `reports/`
- manifest json files in `reports/manifests/`

The daily run should also produce:

- per-symbol logs
- batch summary

---

## 8. Failure Handling

Common non-fatal cases:

- missing `financial_summary`
- missing `news_summary`
- missing `breadth_context`
- notifier disabled or missing env

Common fatal per-symbol cases:

- missing required price data
- invalid required provider payload
- exporter write failure for that symbol

Whole-batch failure should be avoided unless:

- config is invalid
- startup dependencies are broken
- all provider resolution paths are unusable

See runbooks:

- `runbooks/daily_run.md`
- `runbooks/source_failure.md`
- `runbooks/paid_upgrade.md`
