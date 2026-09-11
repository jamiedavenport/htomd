"""Validate the release tag and license attribution."""

import json
import os
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    project = tomllib.loads((ROOT / "python/pyproject.toml").read_text(encoding="utf-8"))["project"]
    target = json.loads((ROOT / "typescript/package.json").read_text(encoding="utf-8"))
    rust = tomllib.loads((ROOT / "rust/Cargo.toml").read_text())["package"]["version"]
    shipwright = tomllib.loads((ROOT / "shipwright.toml").read_text())["version"]
    go = re.search(r'const Version = "([^"]+)"', (ROOT / "go/htomd.go").read_text())
    if go is None or len({project["version"], target["version"], rust, shipwright, go[1]}) != 1:
        raise SystemExit("All package versions must match for a shared release.")
    expected = "v" + project["version"]
    if os.environ.get("RELEASE_TAG") != expected:
        raise SystemExit(f"Release tag must match package metadata: {expected}")
    if "awaiting owner confirmation" in (ROOT / "LICENSE").read_text(encoding="utf-8"):
        raise SystemExit("The owner must confirm the MIT copyright attribution before release.")
    print("Release prerequisites passed.")


if __name__ == "__main__":
    main()
