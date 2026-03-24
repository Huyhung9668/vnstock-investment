# Official Stock Agent Flow

## Layer 1 - Ingestion

1. Load runtime, config, secrets, mode
2. Init run context and manifest skeleton
3. Check source health, quota, fallback readiness
4. Run all market-wide and universe-wide skills
5. Normalize and validate merged datasets

## Layer 2 - Intelligence

6. Build market overview
7. Build per-symbol profiles for whole universe
8. Score and rank, then choose top 10
9. Aggregate market-wide and symbol-specific news
10. Deep dive top 10
11. Run OpenAI synthesis on normalized payloads

## Layer 3 - Action

12. Generate trade plans
13. Apply risk and portfolio constraints
14. Run quality gates

## Layer 4 - Operations

15. Export reports
16. Write manifest and metrics
17. Send notifications
18. Upload artifacts
19. Schedule daily reruns

## Recommended commands

### One command

```powershell
.\.venv\Scripts\python.exe scripts/run_stock_agent.py --stage all --ai-mode api --openai-model gpt-4.1-mini
```

### Step-by-step

```powershell
.\.venv\Scripts\python.exe scripts/run_stock_agent.py --stage ingestion
.\.venv\Scripts\python.exe scripts/run_stock_agent.py --stage intelligence --ai-mode api --openai-model gpt-4.1-mini
.\.venv\Scripts\python.exe scripts/run_stock_agent.py --stage action --ai-mode api --openai-model gpt-4.1-mini
.\.venv\Scripts\python.exe scripts/run_stock_agent.py --stage operations --ai-mode api --openai-model gpt-4.1-mini
```
