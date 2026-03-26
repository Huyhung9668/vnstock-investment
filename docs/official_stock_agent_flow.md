# Official Stock Agent Flow

## Layer 1 - Ingestion

1. Load runtime, config, secrets, mode
2. Init run context and manifest skeleton
3. Check source health, quota, fallback readiness
4. Run market-wide and universe-wide skills
5. Normalize and validate merged datasets

## Layer 2 - Intelligence

6. Build market overview
7. Build per-symbol profiles for whole universe
8. Score and rank, then choose top candidates
9. Aggregate market-wide and symbol-specific news
10. Deep dive selected symbols
11. Run LLM synthesis on normalized payloads using local, file bridge, or cloud mode

## Layer 3 - Action

12. Generate trade plans
13. Apply risk and portfolio constraints
14. Build order context and quality gates

## Layer 4 - Operations

15. Export reports
16. Write manifest and metrics
17. Send notifications
18. Store artifacts
19. Prepare for daily reruns

## Recommended commands

### One command

```powershell
.\.venv\Scripts\python.exe scripts/run_stock_agent.py --stage all --ai-mode local --openai-model qwen2.5:14b
```

### Step-by-step

```powershell
.\.venv\Scripts\python.exe scripts/run_stock_agent.py --stage ingestion
.\.venv\Scripts\python.exe scripts/run_stock_agent.py --stage intelligence --ai-mode local --openai-model qwen2.5:14b
.\.venv\Scripts\python.exe scripts/run_stock_agent.py --stage action --ai-mode local --openai-model qwen2.5:14b
.\.venv\Scripts\python.exe scripts/run_stock_agent.py --stage operations --ai-mode local --openai-model qwen2.5:14b
```
