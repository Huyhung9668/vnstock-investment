import subprocess
import sys
from pathlib import Path


def test_main_script_runs() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "main.py")],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "VNSTOCK investment assistant scaffold" in result.stdout
    assert "Next steps:" in result.stdout

