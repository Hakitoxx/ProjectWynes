"""Entry point for the Project Wynes desktop application.

Run from the project root:

    .venv\\Scripts\\python.exe run.py

A developer smoke test (headless, no window) is available via:

    $env:QT_QPA_PLATFORM = 'offscreen'
    python run.py --smoke-test
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def main() -> int:
    parser = argparse.ArgumentParser(description="Project Wynes desktop application")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Create the main window and exit immediately (used by automated checks).",
    )
    args = parser.parse_args()

    from wynes.app import run

    return run(smoke_test=args.smoke_test)


if __name__ == "__main__":
    raise SystemExit(main())
