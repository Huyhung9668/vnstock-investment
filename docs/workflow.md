# Workflow

## Phase 1: Environment check
- Verify Python is available.
- Verify expected environment variables can be read.
- Confirm project folders exist.

## Phase 2: Data acquisition
- Fetch market or company data with Vnstock.
- Save raw data into `data/`.

## Phase 3: Analysis
- Transform raw data into structured intermediate data.
- Keep assumptions explicit and easy to review.

## Phase 4: Reporting
- Export the result to `reports/`.
- Prefer markdown first, then HTML or PDF if needed.
