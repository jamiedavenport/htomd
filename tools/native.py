"""Locate native CLIs for conformance and check Go formatting."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUFFIX = ".exe" if os.name == "nt" else ""


def run(args: list[str], cwd: Path = ROOT) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def binary(language: str) -> Path:
    if language == "go":
        return ROOT / "go/bin" / ("htomd" + SUFFIX)
    if language == "rust":
        return ROOT / "rust/target/release" / ("htomd" + SUFFIX)
    raise ValueError(f"Unknown native language: {language}")


def lint_go() -> None:
    files = sorted(str(path) for path in (ROOT / "go").rglob("*.go"))
    unformatted = subprocess.check_output(["gofmt", "-l", *files], text=True)
    if unformatted:
        raise SystemExit("Go files need formatting:\n" + unformatted)
    run(["go", "vet", "./..."], ROOT / "go")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["lint-go"])
    parser.parse_args()
    lint_go()


if __name__ == "__main__":
    main()
