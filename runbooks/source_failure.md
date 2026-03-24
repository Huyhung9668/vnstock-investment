# Source Failure Playbook

## Problem
Primary data provider fails

## Action
1. Try fallback providers
2. If still fails:
   - use minimal dataset (price only)
3. Add warning:
   "fallback mode activated"

## Never:
- do NOT crash full pipeline
- do NOT fake data
