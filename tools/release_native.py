"""Release the tested native packages. Dry runs never write to a remote service."""

from __future__ import annotations

import argparse
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path

from tools import check_release
from tools.native import ROOT, run, source_archive, unpack


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


def archive_contents(path: Path) -> dict[str, bytes]:
    with tarfile.open(path) as archive:
        contents = {}
        for member in archive.getmembers():
            if not member.isfile():
                continue
            name = member.name.split("/", 1)[1]
            stream = archive.extractfile(member)
            assert stream is not None
            contents[name] = stream.read()
        return contents


def verify_repack(original: Path, repacked: Path) -> None:
    # Cargo regenerates only packaging provenance, not code, data, or dependencies.
    ignored = {".cargo_vcs_info.json", "Cargo.toml.orig"}
    before = {k: v for k, v in archive_contents(original).items() if k not in ignored}
    after = {k: v for k, v in archive_contents(repacked).items() if k not in ignored}
    if before != after:
        changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
        raise SystemExit(f"Cargo repack changed tested package contents: {changed}")


def publish_rust(dry_run: bool) -> None:
    original = source_archive("rust")
    with tempfile.TemporaryDirectory(prefix="htomd-rust-publish-") as directory:
        package = unpack("rust", Path(directory))
        # Restore the user manifest so Cargo normalizes it exactly as at build time.
        (package / "Cargo.toml").write_bytes((package / "Cargo.toml.orig").read_bytes())
        run(["cargo", "package", "--locked", "--offline", "--allow-dirty", "--no-verify"], package)
        verify_repack(original, package / "target/package" / original.name)
        if dry_run:
            print("Rust publish dry run: repack preserves all tested code, data, and dependencies.")
        else:
            run(["cargo", "publish", "--locked", "--allow-dirty", "--no-verify"], package)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["tag-go", "publish-rust"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    check_release.main()
    {"tag-go": tag_go, "publish-rust": publish_rust}[args.command](args.dry_run)


if __name__ == "__main__":
    main()
