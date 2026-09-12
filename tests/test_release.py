"""Shared releases must never publish packages under mismatched versions."""

import json
from pathlib import Path

import pytest

from tools import check_release


@pytest.mark.parametrize(
    ("python_version", "typescript_version", "tag", "error"),
    [
        ("1.2.3", "1.2.3", "v1.2.3", None),
        ("1.2.3", "1.2.4", "v1.2.3", "versions must match"),
        ("1.2.3", "1.2.3", "v1.2.4", "Release tag must match"),
    ],
)
def test_release_versions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    python_version: str,
    typescript_version: str,
    tag: str,
    error: str | None,
) -> None:
    (tmp_path / "python").mkdir()
    (tmp_path / "typescript").mkdir()
    (tmp_path / "rust").mkdir()
    (tmp_path / "go").mkdir()
    (tmp_path / "rust/Cargo.toml").write_text(f'[package]\nversion="{python_version}"\n')
    (tmp_path / "go/htomd.go").write_text(f'const Version = "{python_version}"\n')
    (tmp_path / "shipwright.toml").write_text(f'version="{python_version}"\n')
    (tmp_path / "python/pyproject.toml").write_text(
        f'[project]\nversion = "{python_version}"\n', encoding="utf-8"
    )
    (tmp_path / "typescript/package.json").write_text(
        json.dumps({"version": typescript_version}), encoding="utf-8"
    )
    monkeypatch.setattr(check_release, "ROOT", tmp_path)
    monkeypatch.setenv("RELEASE_TAG", tag)
    if error:
        with pytest.raises(SystemExit, match=error):
            check_release.main()
    else:
        check_release.main()


@pytest.mark.parametrize("package", ["go", "rust", "shipwright"])
def test_native_version_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, package: str
) -> None:
    test_release_versions(tmp_path, monkeypatch, "1.2.3", "1.2.3", "v1.2.3", None)
    files = {"go": "go/htomd.go", "rust": "rust/Cargo.toml", "shipwright": "shipwright.toml"}
    path = tmp_path / files[package]
    path.write_text(path.read_text().replace("1.2.3", "1.2.4"))
    with pytest.raises(SystemExit, match="versions must match"):
        check_release.main()
