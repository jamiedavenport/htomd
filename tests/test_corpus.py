import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

from htomd import extract
from htomd._parser import parse
from htomd._tree import walk

FIXTURES = Path(__file__).parent / "fixtures/real"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())


def test_corpus_distribution() -> None:
    assert len(MANIFEST) == 115
    domains = Counter(item["domain"] for item in MANIFEST)
    assert len(domains) == 29
    assert max(domains.values()) <= 12
    assert Counter(item["category"] for item in MANIFEST) == {
        "article": 65,
        "documentation": 30,
        "boundary": 20,
    }
    assert Counter(item["split"] for item in MANIFEST) == {"development": 80, "held_out": 35}
    splits: dict[str, set[str]] = defaultdict(set)
    for item in MANIFEST:
        splits[item["domain"]].add(item["split"])
    assert all(len(value) == 1 for value in splits.values())
    assert len({item["final_url"] for item in MANIFEST}) == len(MANIFEST)


@pytest.mark.parametrize("item", MANIFEST, ids=lambda item: item["id"])
def test_snapshot_bytes_and_offline_extraction(item: dict[str, Any]) -> None:
    raw = (FIXTURES / (item["id"] + ".html")).read_bytes()
    assert raw.strip()
    assert hashlib.sha256(raw).hexdigest() == item["sha256"]
    assert len(bytes.fromhex(item["original_sha256"])) == 32
    assert item["status"] == 200
    document = extract(raw.decode(item["encoding"]), url=item["source_url"])
    assert isinstance(document.markdown, str)
    if document.markdown:
        assert document.markdown.endswith("\n")
        assert not document.markdown.endswith("\n\n")


@pytest.mark.parametrize("item", MANIFEST, ids=lambda item: item["id"])
def test_snapshot_sanitisation_and_attribution(item: dict[str, Any]) -> None:
    html = (FIXTURES / (item["id"] + ".html")).read_text(encoding=item["encoding"])
    root, _ = parse(html)
    for node in walk(root):
        assert node.tag not in {"style", "svg", "iframe", "object", "embed", "canvas"}
        if node.tag == "script":
            assert node.attrs.get("type", "").lower() == "application/ld+json"
        for name, value in node.attrs.items():
            assert not name.startswith("on")
            assert name != "srcdoc"
            assert not value.strip().lower().startswith(("data:", "javascript:", "vbscript:"))
    provenance = item["provenance"]
    assert provenance["attribution"] and provenance["license_url"]
    assert (FIXTURES / provenance["notice_file"]).is_file()


@pytest.mark.parametrize(
    "path", sorted((FIXTURES / "captured").glob("*.txt")), ids=lambda path: path.stem
)
def test_captured_development_output(path: Path) -> None:
    """Change detection only: captured outputs are not independently labelled gold."""
    item = next(item for item in MANIFEST if item["id"] == path.stem)
    assert item["split"] == "development"
    raw = (FIXTURES / (item["id"] + ".html")).read_bytes()
    document = extract(raw.decode(item["encoding"]), url=item["source_url"])
    assert document.markdown == path.read_text()
    assert (
        asdict(document.metadata) == json.loads(path.with_suffix(".json").read_text())["metadata"]
    )


def test_annotation_inventory_matches_snapshots() -> None:
    annotations = json.loads((FIXTURES / "annotations.json").read_text())
    assert {row["id"]: row["sha256"] for row in annotations} == {
        row["id"]: row["sha256"] for row in MANIFEST
    }
    for row in annotations:
        assert (FIXTURES / row["blocks_file"]).is_file()


@pytest.mark.parametrize(
    "case", json.loads((FIXTURES / "curated.json").read_text()), ids=lambda case: case["id"]
)
def test_curated_real_regressions(case: dict[str, Any]) -> None:
    item = next(item for item in MANIFEST if item["id"] == case["id"])
    assert item["split"] == "development"
    raw = (FIXTURES / (item["id"] + ".html")).read_bytes()
    document = extract(raw.decode(item["encoding"]), url=item["source_url"])
    assert document.metadata.title == case["title"]
    for fragment in case["include"]:
        assert fragment in document.markdown
    for fragment in case["exclude"]:
        assert fragment not in document.markdown


REVIEWED = [
    row
    for row in json.loads((FIXTURES / "annotations.json").read_text())
    if row["review_status"] == "human_reviewed"
]


@pytest.mark.parametrize("row", REVIEWED, ids=lambda row: row["id"])
def test_human_reviewed_expectations(row: dict[str, Any]) -> None:
    item = next(item for item in MANIFEST if item["id"] == row["id"])
    raw = (FIXTURES / (item["id"] + ".html")).read_bytes()
    document = extract(raw.decode(item["encoding"]), url=item["source_url"])
    for fragment in row["include"]:
        assert fragment in document.markdown
    for fragment in row["exclude"]:
        assert fragment not in document.markdown
    cursor = 0
    for fragment in row["ordered"]:
        position = document.markdown.find(fragment, cursor)
        assert position >= 0
        cursor = position + len(fragment)
    for key, expected in row["metadata"].items():
        assert getattr(document.metadata, key) == expected
    if row["exact_markdown"]:
        assert document.markdown == (FIXTURES / row["exact_markdown"]).read_text()
