from __future__ import annotations

import importlib
import sys


PACKAGES = [
    ("vnstock", "vnstock"),
    ("pandas", "pandas"),
    ("matplotlib", "matplotlib"),
    ("jupyter", "jupyter"),
    ("python-dotenv", "dotenv"),
]


def check_import(module_name: str) -> tuple[bool, str]:
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, "__version__", "unknown")
        return True, version
    except Exception as exc:  # pragma: no cover - diagnostic helper
        return False, str(exc)


def main() -> int:
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version.split()[0]}")
    print()
    print("Import check:")

    all_ok = True
    for package_name, module_name in PACKAGES:
        ok, detail = check_import(module_name)
        status = "OK" if ok else "FAIL"
        if not ok:
            all_ok = False
        print(f"- {package_name}: {status} ({detail})")

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
