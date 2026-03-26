@echo off
setlocal
cd /d "%~dp0"
set HTTP_PROXY=
set HTTPS_PROXY=
set http_proxy=
set https_proxy=
set ALL_PROXY=
set all_proxy=
set GIT_HTTP_PROXY=
set GIT_HTTPS_PROXY=
set AI_ANALYSIS_ENABLED=false
python scripts\run_watchlist_top_selection.py --config-dir config\test50 --watchlist-limit 50 --top-n 5
endlocal
