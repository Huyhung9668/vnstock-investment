# Trading Terminal Orchestrator Examples

## Example 1: Full terminal with OpenAI API

```powershell
.\.venv\Scripts\python.exe scripts/run_trading_terminal.py --ai-mode api --openai-model gpt-4.1-mini
```

Expected:

- universe scan chay
- market overview duoc rebuild
- daily run export report bundle
- AI viet them market narrative

## Example 2: Reuse existing data, only rebuild final reports

```powershell
.\.venv\Scripts\python.exe scripts/run_trading_terminal.py --skip-scan --skip-overview --ai-mode api
```

Expected:

- bo qua scan
- bo qua rebuild market overview
- dung derived data co san de tao lai report tong hop

## Example 3: File bridge mode

```powershell
.\.venv\Scripts\python.exe scripts/run_trading_terminal.py --ai-mode file
```

Expected:

- tao `artifacts/ai_prompt.json`
- doi response file san sang
- pipeline co the chay tiep khi response file hop le
