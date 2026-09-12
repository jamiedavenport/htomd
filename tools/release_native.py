"""Publish the Go module tag without rewriting conflicting tags."""

from __future__ import annotations

import argparse
import os
import subprocess

from tools import check_release
from tools.native import ROOT, run


def go_tag_action(commit: str, existing: str | None) -> bool:
    """An existing tag is acceptable only when it identifies the release commit."""
    if existing is None:
        return True
    if existing != commit:
        raise SystemExit("Existing Go module tag points at a different commit")
    return False


def tag_go(dry_run: bool) -> None:
    tag = os.environ["RELEASE_TAG"]
    commit = subprocess.check_output(
        ["git", "rev-parse", f"{tag}^{{commit}}"], cwd=ROOT, text=True
    ).strip()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != commit:
        raise SystemExit("Checkout must match the root release tag")
    ref = f"refs/tags/go/{tag}"
    remote = subprocess.check_output(
        ["git", "ls-remote", "--tags", "origin", ref, ref + "^{}"], cwd=ROOT, text=True
    )
    refs = {line.split()[1]: line.split()[0] for line in remote.splitlines()}
    existing = refs.get(ref + "^{}", refs.get(ref))
    if go_tag_action(commit, existing):
        if dry_run:
            print(f"Would publish {ref} at {commit}")
        else:
            run(["git", "push", "origin", f"{commit}:{ref}"])
    else:
        print("Go module tag already matches the release commit.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["tag-go"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    check_release.main()
    tag_go(args.dry_run)


if __name__ == "__main__":
    main()
