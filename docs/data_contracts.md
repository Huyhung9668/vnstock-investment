# Data Contracts

## Input data
- Market data from Vnstock.
- Company data from Vnstock.
- Optional user-supplied watchlists or symbols.

## Working data
- Store raw data in a predictable folder structure under `data/`.
- Keep intermediate files easy to trace back to the source.

## Output data
- Write final reports to `reports/`.
- Use stable filenames so results are easy to compare over time.

## Minimum expectations
- Each dataset should have a source, timestamp, and symbol or scope.
- Analysis steps should not overwrite raw inputs.
