"""Inspect the built TypeScript tarball and smoke-test an isolated installation."""

from __future__ import annotations

import json
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "typescript"


def install_package(archive: Path, consumer: Path) -> Path:
    """Install a packed package in an isolated consumer without running scripts."""
    bun = shutil.which("bun")
    assert bun, "Bun must be installed"
    consumer.mkdir()
    (consumer / "package.json").write_text('{"private":true,"type":"module"}\n', encoding="utf-8")
    subprocess.run(
        [bun, "install", "--offline", "--ignore-scripts", str(archive)],
        cwd=consumer,
        check=True,
    )
    return consumer / "node_modules/htomd"


def main() -> None:
    bun = shutil.which("bun")
    node = shutil.which("node")
    assert bun and node, "Bun and Node must be installed"
    archives = list((ROOT / "dist/typescript").glob("*.tgz"))
    assert len(archives) == 1, "Run mise run build first; expected one TypeScript tarball"
    archive_path = archives[0]
    with tempfile.TemporaryDirectory(prefix="htomd-ts-dist-") as directory:
        work = Path(directory)
        with tarfile.open(archive_path) as archive:
            names = archive.getnames()
            assert "package/dist/index.js" in names
            assert "package/dist/index.d.ts" in names
            assert "package/dist/cli.js" in names
            assert "package/dist/entities.json" in names
            assert "package/LICENSE" in names
            assert "package/NOTICE" in names
            assert not any("/tests/" in name or "/node_modules/" in name for name in names)
            for name in names:
                if name.endswith(".js.map"):
                    source_map_file = archive.extractfile(name)
                    assert source_map_file is not None
                    source_map = json.load(source_map_file)
                    assert len(source_map["sources"]) == len(source_map["sourcesContent"])
                    assert all(source_map["sourcesContent"]), name
            metadata_file = archive.extractfile("package/package.json")
            assert metadata_file is not None
            metadata = json.load(metadata_file)
            assert not metadata.get("dependencies")
            assert metadata["bin"]["htomd"] == "./dist/cli.js"
        consumer = work / "consumer"
        install_package(archive_path, consumer)
        (consumer / "example.ts").write_text(
            'import {convert, extract, type Document} from "htomd";\n'
            'const doc: Document = extract("<article><h1>Tea</h1></article>");\n'
            'const empty: Document = extract("", {url: undefined});\n'
            'if (empty.metadata.url !== null) throw Error("undefined URL");\n'
            'if (doc.metadata.title !== "Tea" || !Object.isFrozen(doc)) throw Error("API");\n'
            'if (convert("<p>Steep.</p>") !== "Steep.\\n") throw Error("convert");\n'
        )
        subprocess.run(
            [
                bun,
                str(TARGET / "node_modules/typescript/bin/tsc"),
                "--strict",
                "--noUncheckedIndexedAccess",
                "--exactOptionalPropertyTypes",
                "--module",
                "NodeNext",
                "--target",
                "ES2022",
                "example.ts",
            ],
            cwd=consumer,
            check=True,
        )
        subprocess.run([node, "example.js"], cwd=consumer, check=True)
        result = subprocess.run(
            [bun, "run", "--no-install", "htomd", "convert"],
            input="<p>Thé 🍵</p>".encode(),
            capture_output=True,
            cwd=consumer,
            check=True,
        )
        assert result.stdout == "Thé 🍵\n".encode(), result.stdout
        assert not result.stderr, result.stderr
    print("TypeScript tarball passed contents, declarations, isolated API, and CLI checks.")


if __name__ == "__main__":
    main()
