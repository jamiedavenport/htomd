"""Explicit conformance fixture expectations."""

import pytest

from tools.conformance import expected_output


def test_fixture_replacement_requires_one_match() -> None:
    overrides = {"markdown_replacements": [["[Page](https://example.org/#)", "Page"]]}
    assert expected_output(b"[Page](https://example.org/#)\n", "convert", overrides) == b"Page\n"
    for reference in (b"missing", b"[Page](https://example.org/#)" * 2):
        with pytest.raises(AssertionError, match="one replacement"):
            expected_output(reference, "convert", overrides)


def test_unknown_fixture_override_fails() -> None:
    with pytest.raises(AssertionError):
        expected_output(b"Text\n", "convert", {"markdwon": "silently ignored"})
