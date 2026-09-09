"""Release prerequisites that require owner/reviewer decisions."""

import json
import os
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    expected = "v" + project["version"]
    if os.environ.get("RELEASE_TAG") != expected:
        raise SystemExit(f"Release tag must match package metadata: {expected}")
    if "awaiting owner confirmation" in (ROOT / "LICENSE").read_text():
        raise SystemExit("The owner must confirm the MIT copyright attribution before release.")
    annotations = json.loads((ROOT / "tests/fixtures/real/annotations.json").read_text())
    reviewed = [item for item in annotations if item["review_status"] == "human_reviewed"]
    if len(reviewed) < 120:
        raise SystemExit(f"Human corpus review incomplete: {len(reviewed)}/120 pages.")
    exact = [item for item in reviewed if item.get("exact_markdown")]
    if len(exact) < 40:
        raise SystemExit("At least 40 reviewed exact Markdown/metadata expectations are required.")
    print("Release prerequisites passed.")


if __name__ == "__main__":
    main()
