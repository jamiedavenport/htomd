"""Validate the release tag and license attribution."""

import os
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    expected = "v" + project["version"]
    if os.environ.get("RELEASE_TAG") != expected:
        raise SystemExit(f"Release tag must match package metadata: {expected}")
    if "awaiting owner confirmation" in (ROOT / "LICENSE").read_text(encoding="utf-8"):
        raise SystemExit("The owner must confirm the MIT copyright attribution before release.")
    print("Release prerequisites passed.")


if __name__ == "__main__":
    main()
