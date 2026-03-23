from __future__ import annotations

import os
import platform
import sys
from pathlib import Path


def check_environment() -> list[str]:
    """Collect basic environment checks for the project scaffold."""
    checks = [
        f"Python: {sys.version.split()[0]}",
        f"Platform: {platform.system()} {platform.release()}",
        f"Project root: {Path(__file__).resolve().parents[1]}",
        f"OUTPUT_DIR: {os.getenv('OUTPUT_DIR', 'reports')}",
        f"DATA_DIR: {os.getenv('DATA_DIR', 'data')}",
        f"VNSTOCK_SOURCE: {os.getenv('VNSTOCK_SOURCE', 'demo')}",
    ]
    return checks


def print_next_steps() -> None:
    """Print the next milestones without calling Vnstock yet."""
    steps = [
        "1. Install dependencies from requirements.txt.",
        "2. Configure .env from .env.example.",
        "3. Add Vnstock data retrieval in a dedicated module later.",
        "4. Expand analysis and reporting once the data contract is stable.",
    ]
    for step in steps:
        print(step)


def main() -> int:
    print("VNSTOCK investment assistant scaffold")
    print("Environment check:")
    for item in check_environment():
        print(f"- {item}")

    print()
    print("Next steps:")
    print_next_steps()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
