"""Inspect and smoke-test both distributions outside the repository checkout."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from email.parser import BytesParser
from importlib.metadata import version
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
SMOKE = """
from importlib.metadata import distribution
from importlib.util import find_spec
from pathlib import Path
import htomd
assert htomd.convert('<article><h1>Tea</h1><p>Steep.</p></article>') == '# Tea\\n\\nSteep.\\n'
assert distribution('htomd').requires is None
assert not any(
    find_spec(name)
    for name in ('markdownify', 'html2text', 'trafilatura', 'html_to_markdown', 'htmd')
)
assert any(
    entry.group == 'console_scripts' and entry.name == 'htomd' and entry.value == 'htomd._cli:main'
    for entry in distribution('htomd').entry_points
)
assert Path(htomd.__file__).parent.joinpath('py.typed').is_file()
assert 'site-packages' in htomd.__file__
"""


def assert_no_benchmark_files(names: list[str]) -> None:
    for name in names:
        parts = PurePosixPath(name).parts
        assert not any(
            part in {"tools", ".benchmark", "benchmark", "benchmarks", "locks", "results"}
            or part.startswith(".venv")
            for part in parts
        ), f"Benchmark/development file in distribution: {name}"


def inspect(wheel: Path, source: Path) -> None:
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        assert_no_benchmark_files(names)
        metadata = BytesParser().parsebytes(
            archive.read(next(name for name in names if name.endswith("/METADATA")))
        )
        assert metadata.get_all("Requires-Dist") is None, "Runtime dependency found"
        assert metadata["License-Expression"] == "MIT"
        assert "htomd/py.typed" in names
        assert any(name.endswith("/LICENSE") for name in names)
        assert all(".so" not in name and ".pyd" not in name for name in names)
    with tarfile.open(source) as archive:
        names = archive.getnames()
        assert_no_benchmark_files(names)
        metadata_file = archive.extractfile(
            next(name for name in names if name.endswith("/PKG-INFO"))
        )
        assert metadata_file is not None
        assert BytesParser().parsebytes(metadata_file.read()).get_all("Requires-Dist") is None
        assert any(name.endswith("/LICENSE") for name in names)
        assert any(name.endswith("/src/htomd/py.typed") for name in names)
        assert not any("/tests/" in name or "/fixtures/" in name for name in names)


def smoke(artifact: Path) -> None:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory(prefix="htomd-smoke-") as directory:
        root = Path(directory)
        venv = root / "venv"
        subprocess.run(
            ["uv", "venv", "--python", sys.executable, str(venv)], cwd=root, env=env, check=True
        )
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(
            ["uv", "pip", "install", "--python", str(python), "--no-deps", str(artifact)],
            cwd=root,
            env=env,
            check=True,
        )
        subprocess.run([str(python), "-I", "-c", SMOKE], cwd=root, env=env, check=True)
        command = venv / ("Scripts/htomd.exe" if os.name == "nt" else "bin/htomd")
        html = "<article><h1>Thé</h1><p>Steep.</p></article>".encode()
        markdown = "# Thé\n\nSteep.\n"
        for invocation in ([str(command)], [str(python), "-I", "-m", "htomd"]):
            for args in ([], ["help"], ["version"], ["--version"]):
                result = subprocess.run(
                    [*invocation, *args],
                    input=b"",
                    capture_output=True,
                    cwd=root,
                    env=env,
                    check=True,
                )
                assert not result.stderr, result.stderr
                if args in (["version"], ["--version"]):
                    assert result.stdout.decode() == f"htomd {version('htomd')}{os.linesep}"
                else:
                    assert b"cat page.html | htomd convert" in result.stdout
            for subcommand in ("convert", "extract"):
                result = subprocess.run(
                    [*invocation, subcommand],
                    input=html,
                    capture_output=True,
                    cwd=root,
                    env=env,
                    check=True,
                )
                assert not result.stderr, result.stderr
                output = result.stdout.decode("utf-8")
                if subcommand == "convert":
                    assert output == markdown
                else:
                    document = json.loads(output)
                    assert set(document) == {"markdown", "metadata", "diagnostics"}
                    assert document["markdown"] == markdown
                    assert document["metadata"]["title"] == "Thé"
                    assert document["metadata"]["author"] is None
                    assert isinstance(document["diagnostics"]["notes"], list)


def main() -> None:
    wheels = list((ROOT / "dist/python").glob("*.whl"))
    sources = list((ROOT / "dist/python").glob("*.tar.gz"))
    assert len(wheels) == len(sources) == 1, "Expected exactly one wheel and one source archive"
    inspect(wheels[0], sources[0])
    for artifact in [wheels[0], sources[0]]:
        smoke(artifact)
    print("Both distributions passed metadata, contents, and isolated installation checks.")


if __name__ == "__main__":
    main()
