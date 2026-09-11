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
    (tmp_path / "python/pyproject.toml").write_text(
        f'[project]\nversion = "{python_version}"\n', encoding="utf-8"
    )
    (tmp_path / "typescript/package.json").write_text(
        json.dumps({"version": typescript_version}), encoding="utf-8"
    )
    (tmp_path / "LICENSE").write_text("MIT", encoding="utf-8")
    monkeypatch.setattr(check_release, "ROOT", tmp_path)
    monkeypatch.setenv("RELEASE_TAG", tag)
    if error:
        with pytest.raises(SystemExit, match=error):
            check_release.main()
    else:
        check_release.main()
