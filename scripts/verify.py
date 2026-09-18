"""Create or reuse the canonical environment and run repository verification."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT = ROOT / ".venv"


def environment_python() -> Path:
    if os.name == "nt":
        return ENVIRONMENT / "Scripts" / "python.exe"
    return ENVIRONMENT / "bin" / "python"


def require_environment() -> Path:
    python = environment_python()
    if not python.exists():
        raise SystemExit(
            f"Missing canonical environment: {ENVIRONMENT}. "
            "Create it and install dependencies separately."
        )
    return python


def run(python: Path, *args: str) -> None:
    subprocess.run([str(python), *args], cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    python = require_environment()
    run(python, "-m", "pytest", *args.pytest_args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
