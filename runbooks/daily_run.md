# Daily Run Playbook

## Goal
Run analysis for all symbols in watchlist

## Steps
1. Load config/watchlist.yaml
2. For each symbol:
   - run trade plan
   - capture result
3. Continue even if one symbol fails
4. Build summary
5. Send notification (if enabled)

## Expected Output
- Reports for each symbol
- Summary with success/failed count
