import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest

import htomd

CASES = json.loads((Path(__file__).parent / "fixtures/synthetic/cases.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_synthetic(case: dict[str, Any]) -> None:
    result = htomd.extract(case["html"], url=case.get("url"))
    assert result.markdown == case["markdown"]
    assert htomd.convert(case["html"], url=case.get("url")) == result.markdown
    assert bool(result.markdown) == (result.diagnostics.strategy != "none")


@pytest.mark.parametrize("value", [None, 1, b"html", [], {}])
def test_invalid_html(value: Any) -> None:
    with pytest.raises(TypeError, match="html"):
        htomd.extract(value)


@pytest.mark.parametrize("value", [1, b"url", [], {}])
def test_invalid_url(value: Any) -> None:
    with pytest.raises(TypeError, match="url"):
        htomd.extract("", url=value)


def test_frozen_slotted_results() -> None:
    result = htomd.extract("<p>A</p>")
    for value in (result, result.metadata, result.diagnostics):
        assert not hasattr(value, "__dict__")
    with pytest.raises(FrozenInstanceError):
        result.markdown = "oops"  # type: ignore[misc]
    assert isinstance(result.diagnostics.notes, tuple)


def test_deep_pipeline() -> None:
    assert (
        htomd.convert("<article>" + "<div>" * 2000 + "Text." + "</div>" * 2000 + "</article>")
        == "Text.\n"
    )


def test_convert_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = htomd.Document("sentinel", htomd.Metadata(), htomd.Diagnostics("fallback"))
    monkeypatch.setattr(htomd, "extract", lambda html, url=None: expected)
    assert htomd.convert("anything") == "sentinel"
