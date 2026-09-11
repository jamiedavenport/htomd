"""Build and check independent native source packages and platform executables."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
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


def source_archive(language: str) -> Path:
    extension = "crate" if language == "rust" else "tar.gz"
    return DIST / language / f"htomd-{version()}.{extension}"


def unpack(language: str, work: Path) -> Path:
    with tarfile.open(source_archive(language)) as archive:
        archive.extractall(work, filter="data")
    return work / f"htomd-{version()}"


def binary(language: str, artifacts: Path = DIST) -> Path:
    return artifacts / "native" / platform_name() / language / ("htomd" + SUFFIX)


def package_sources() -> None:
    for language in ("go", "rust"):
        (DIST / language).mkdir(parents=True, exist_ok=True)
    with tarfile.open(source_archive("go"), "w:gz") as archive:
        for path in sorted((ROOT / "go").rglob("*")):
            if (
                path.is_file()
                and not path.name.endswith("_test.go")
                and (path.suffix == ".go" or path.name in {"go.mod", "LICENSE", "README.md"})
            ):
                archive.add(path, arcname=f"htomd-{version()}/{path.relative_to(ROOT / 'go')}")
    run(
        [
            "cargo",
            "package",
            "--manifest-path",
            "rust/Cargo.toml",
            "--locked",
            "--allow-dirty",
            "--no-verify",
        ]
    )
    shutil.copy2(ROOT / "rust/target/package" / source_archive("rust").name, source_archive("rust"))


def build_native() -> None:
    with tempfile.TemporaryDirectory(prefix="htomd-native-build-") as directory:
        work = Path(directory)
        for language in ("go", "rust"):
            package = unpack(language, work / language)
            output = binary(language)
            output.parent.mkdir(parents=True, exist_ok=True)
            if language == "go":
                run(["go", "build", "-trimpath", "-o", str(output), "./cmd/htomd"], package)
            else:
                target = ROOT / "rust/target"
                # Cargo archives normalize source timestamps. Reusing the same
                # name/version can otherwise leave an older local binary fresh.
                # Clear only this package's release outputs, retaining dependencies.
                run(
                    [
                        "cargo",
                        "clean",
                        "--package",
                        "htomd",
                        "--release",
                        "--target-dir",
                        str(target),
                    ],
                    package,
                )
                run(
                    [
                        "cargo",
                        "build",
                        "--release",
                        "--locked",
                        "--offline",
                        "--target-dir",
                        str(target),
                    ],
                    package,
                )
                shutil.copy2(target / "release" / ("htomd" + SUFFIX), output)
            name = f"htomd-{language}-{version()}-{platform_name()}.tar.gz"
            release = DIST / "native" / platform_name() / name
            with tarfile.open(release, "w:gz") as archive:
                archive.add(output, arcname=output.name)
                for filename in ("LICENSE", "NOTICE", "README.md"):
                    if (package / filename).exists():
                        archive.add(package / filename, arcname=filename)
            digest = hashlib.sha256(release.read_bytes()).hexdigest()
            release.with_suffix(release.suffix + ".sha256").write_text(
                f"{digest}  {release.name}\n", encoding="utf-8"
            )


def check_packages() -> None:
    with tempfile.TemporaryDirectory(prefix="htomd-native-check-") as directory:
        work = Path(directory)
        for language in ("go", "rust"):
            package = unpack(language, work / language)
            assert (package / "LICENSE").is_file()
            assert (package / "README.md").is_file()
            if language == "rust":
                assert (package / "NOTICE").is_file()
                assert (package / "src/entities_data.rs").is_file()
            consumer = work / f"{language}-consumer"
            consumer.mkdir()
            if language == "go":
                (consumer / "go.mod").write_text(
                    "module example.com/consumer\n\ngo 1.27.0\n"
                    "require github.com/jamiedavenport/htomd/go v0.0.0\n"
                    f"replace github.com/jamiedavenport/htomd/go => {json.dumps(str(package))}\n"
                )
                (consumer / "main.go").write_text(
                    'package main\nimport h "github.com/jamiedavenport/htomd/go"\n'
                    'func main(){d,e:=h.Extract("<h1>Tea</h1>",h.Options{});'
                    'if e!=nil||d.Metadata.Title==nil||*d.Metadata.Title!="Tea"'
                    '||d.Markdown!="# Tea\\n"{panic("API")}}\n'
                )
                run(["go", "run", "."], consumer)
                modules = subprocess.check_output(["go", "list", "-m", "all"], cwd=package)
                assert len(modules.splitlines()) == 1, "Go must have no external dependencies"
            else:
                (consumer / "Cargo.toml").write_text(
                    '[package]\nname="consumer"\nversion="0.0.0"\nedition="2024"\n'
                    f"[dependencies]\nhtomd={{path={json.dumps(str(package))}}}\n"
                )
                (consumer / "src").mkdir()
                (consumer / "src/main.rs").write_text(
                    'fn main(){let d=htomd::extract("<h1>Tea</h1>",Default::default());'
                    'assert_eq!(d.metadata.title.as_deref(),Some("Tea"));'
                    'assert_eq!(d.markdown,"# Tea\\n");}\n'
                )
                run(
                    [
                        "cargo",
                        "run",
                        "--offline",
                        "--target-dir",
                        str(ROOT / "rust/target/consumer"),
                    ],
                    consumer,
                )
            result = subprocess.run(
                [str(binary(language)), "convert"],
                input="<p>Thé 🍵</p>".encode(),
                capture_output=True,
                cwd=consumer,
                check=True,
            )
            assert result.stdout == "Thé 🍵\n".encode() and not result.stderr
    print("Native source packages, isolated APIs, and built CLIs passed.")


def lint_go() -> None:
    files = sorted(str(path) for path in (ROOT / "go").rglob("*.go"))
    unformatted = subprocess.check_output(["gofmt", "-l", *files], text=True)
    if unformatted:
        raise SystemExit("Go files need formatting:\n" + unformatted)
    run(["go", "vet", "./..."], ROOT / "go")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["package", "build", "check", "lint-go"])
    args = parser.parse_args()
    {
        "package": package_sources,
        "build": build_native,
        "check": check_packages,
        "lint-go": lint_go,
    }[args.command]()


if __name__ == "__main__":
    main()
