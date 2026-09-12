"""Archive built native CLIs for release and check Go formatting."""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import subprocess
import tarfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
SUFFIX = ".exe" if os.name == "nt" else ""


def platform_name() -> str:
    machine = platform.machine().lower()
    arch = {"amd64": "x86_64", "arm64": "aarch64"}.get(machine, machine)
    return f"{platform.system().lower()}-{arch}"


def version() -> str:
    return str(tomllib.loads((ROOT / "shipwright.toml").read_text())["version"])


def run(args: list[str], cwd: Path = ROOT) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def binary(language: str) -> Path:
    if language == "go":
        return ROOT / "go/bin" / ("htomd" + SUFFIX)
    if language == "rust":
        return ROOT / "rust/target/release" / ("htomd" + SUFFIX)
    raise ValueError(f"Unknown native language: {language}")


def package_native() -> None:
    destination = DIST / "native" / platform_name()
    destination.mkdir(parents=True, exist_ok=True)
    for language in ("go", "rust"):
        output = binary(language)
        if not output.is_file():
            raise SystemExit(f"Missing {language} binary; run mise run build first")
        release = destination / f"htomd-{language}-{version()}-{platform_name()}.tar.gz"
        with tarfile.open(release, "w:gz") as archive:
            archive.add(output, arcname=output.name)
            for filename in ("LICENSE", "NOTICE", "README.md"):
                path = ROOT / language / filename
                if path.exists():
                    archive.add(path, arcname=filename)
        digest = hashlib.sha256(release.read_bytes()).hexdigest()
        release.with_suffix(release.suffix + ".sha256").write_text(
            f"{digest}  {release.name}\n", encoding="utf-8"
        )


def lint_go() -> None:
    files = sorted(str(path) for path in (ROOT / "go").rglob("*.go"))
    unformatted = subprocess.check_output(["gofmt", "-l", *files], text=True)
    if unformatted:
        raise SystemExit("Go files need formatting:\n" + unformatted)
    run(["go", "vet", "./..."], ROOT / "go")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["package", "lint-go"])
    args = parser.parse_args()
    {"package": package_native, "lint-go": lint_go}[args.command]()


if __name__ == "__main__":
    main()
