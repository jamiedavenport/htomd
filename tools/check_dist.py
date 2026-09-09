"""Inspect and smoke-test both distributions outside the repository checkout."""

from __future__ import annotations

import os
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from email.parser import BytesParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOKE = """
from importlib.metadata import distribution
from pathlib import Path
import htomd
assert htomd.convert('<article><h1>Tea</h1><p>Steep.</p></article>') == '# Tea\\n\\nSteep.\\n'
assert distribution('htomd').requires is None
assert Path(htomd.__file__).parent.joinpath('py.typed').is_file()
assert 'site-packages' in htomd.__file__
"""


def inspect(wheel: Path, source: Path) -> None:
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
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


def main() -> None:
    wheels = list((ROOT / "dist").glob("*.whl"))
    sources = list((ROOT / "dist").glob("*.tar.gz"))
    assert len(wheels) == len(sources) == 1, "Expected exactly one wheel and one source archive"
    inspect(wheels[0], sources[0])
    for artifact in [wheels[0], sources[0]]:
        smoke(artifact)
    print("Both distributions passed metadata, contents, and isolated installation checks.")


if __name__ == "__main__":
    main()
