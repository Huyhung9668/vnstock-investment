# Architecture

## Goal
Build a single main investment assistant that uses Vnstock data to produce clear, repeatable analysis outputs.

## Current shape
- `scripts/main.py` is the entry point.
- `data/` stores raw and processed data.
- `reports/` stores final outputs.
- `docs/` stores project rules and workflow notes.
- `tests/` stores smoke tests for the scaffold.

## Design principles
- Keep one main agent.
- Prefer simple, verifiable steps.
- Separate input data, processing, and reporting.
- Add complexity only after the basic pipeline is stable.
