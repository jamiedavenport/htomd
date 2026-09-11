"""Native package/release checks must reject drift without publishing anything."""

import io
import tarfile
from pathlib import Path

import pytest

from tools.conformance import expected_output
from tools.release_native import go_tag_action, verify_repack


def test_go_tag_conflicts() -> None:
    assert go_tag_action("abc", None)
    assert not go_tag_action("abc", "abc")
    with pytest.raises(SystemExit, match="different commit"):
        go_tag_action("abc", "def")


def archive(path: Path, content: bytes) -> None:
    with tarfile.open(path, "w:gz") as result:
        member = tarfile.TarInfo("htomd-0.1.1/src/lib.rs")
        member.size = len(content)
        result.addfile(member, io.BytesIO(content))


def test_repack_rejects_source_changes(tmp_path: Path) -> None:
    original, repacked = tmp_path / "original.crate", tmp_path / "repacked.crate"
    archive(original, b"tested source")
    archive(repacked, b"tested source")
    verify_repack(original, repacked)
    archive(repacked, b"changed source")
    with pytest.raises(SystemExit, match="src/lib.rs"):
        verify_repack(original, repacked)


def test_fixture_replacement_requires_one_match() -> None:
    overrides = {"markdown_replacements": [["[Page](https://example.org/#)", "Page"]]}
    assert expected_output(b"[Page](https://example.org/#)\n", "convert", overrides) == b"Page\n"
    for reference in (b"missing", b"[Page](https://example.org/#)" * 2):
        with pytest.raises(AssertionError, match="one replacement"):
            expected_output(reference, "convert", overrides)


def test_unknown_fixture_override_fails() -> None:
    with pytest.raises(AssertionError):
        expected_output(b"Text\n", "convert", {"markdwon": "silently ignored"})
