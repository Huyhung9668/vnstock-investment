from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import run_watchlist_top_selection


def test_resolve_source_config_dir_uses_test50_for_root_config() -> None:
    resolved = run_watchlist_top_selection._resolve_source_config_dir(
        PROJECT_ROOT / "config",
        watchlist_limit=50,
        top_n=5,
    )

    assert resolved == (PROJECT_ROOT / "config" / "test50")


def test_resolve_source_config_dir_upgrades_to_test100_when_needed() -> None:
    resolved = run_watchlist_top_selection._resolve_source_config_dir(
        PROJECT_ROOT / "config" / "test50",
        watchlist_limit=100,
        top_n=5,
    )

    assert resolved == (PROJECT_ROOT / "config" / "test100")
