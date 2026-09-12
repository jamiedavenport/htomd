"""Deterministic benchmark accounting tests; competitors are never imported here."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import cast

import pytest

from tools.benchmark import run
from tools.benchmark.report import (
    aggregate,
    dependency_count,
    detailed_report,
    relative_speed,
    tables,
    update_readme,
)
from tools.benchmark.run import Library, Results
from tools.benchmark.worker import Document, Output, Worker, corpus_pass, footprint, rss_bytes


def library(samples: list[list[int]]) -> Library:
    output = Output(id="tea", characters=30, empty=False, error=None)
    return Library(
        installation=Worker(packages={"htomd": "0.1", "rival": "1.0"}, installed_bytes=2**20),
        wheel={"filename": "test.whl", "bytes": 1024, "sha256": "abc"},
        smoke=Worker(smoke="Steep the tea"),
        rounds=[
            Worker(corpus_ns=times, document_ns={"tea": times}, outputs=[output])
            for times in samples
        ],
        rss=[Worker(rss_bytes=2**20)] * 3,
        imports=[Worker(import_ns=1_000_000)] * 20,
    )


def example() -> Results:
    return Results(
        schema=1,
        metadata={
            "started_utc": "2026-09-09",
            "cpu": "Test CPU",
            "machine": "arm64",
            "memory_bytes": 8 * 2**30,
            "os": "Test OS",
            "python": "3.14.7",
            "revision": "abc",
            "dirty": True,
        },
        settings={
            "rounds": 2,
            "minimum_passes": 2,
            "mode": "full",
            "adapters": {"htomd": "htomd.convert(html)", "rival": "rival.convert(html)"},
        },
        corpus=[Document(id="tea", sha256="abc", bytes=2**20, encoding="utf-8")],
        libraries={
            "htomd": library([[1_000_000_000] * 2] * 2),
            "rival": library([[2_000_000_000] * 2] * 2),
        },
        orders=[["htomd", "rival"], ["rival", "htomd"]],
    )


def test_median_of_round_medians_and_ratio_direction() -> None:
    baseline = aggregate(library([[1_000_000_000] * 3, [3_000_000_000] * 5]), {"tea"}, 2, 2)
    competitor = aggregate(library([[4_000_000_000] * 2] * 2), {"tea"}, 2, 2)
    assert (baseline.seconds, baseline.low, baseline.high) == (2, 1, 3)
    assert relative_speed(competitor, baseline) == 2
    assert relative_speed(baseline, competitor) == 0.5


@pytest.mark.parametrize(
    "damage", ["timeout", "missing_round", "missing_document", "exception", "few_passes"]
)
def test_incomplete_runs_have_no_ratio(damage: str) -> None:
    lib = library([[1_000_000_000] * 2] * 2)
    baseline = aggregate(lib, {"tea"}, 2, 2)
    if damage == "timeout":
        lib["rounds"][0] = Worker(error="worker exceeded 300 seconds")
    elif damage == "missing_round":
        lib["rounds"].pop()
    elif damage == "missing_document":
        lib["rounds"][0]["document_ns"] = {}
    elif damage == "exception":
        lib["rounds"][0]["outputs"][0]["error"] = "Conversion failed"
    else:
        lib["rounds"][0]["corpus_ns"] = [1]
    failed = aggregate(lib, {"tea"}, 2, 2)
    assert not failed.complete
    assert relative_speed(failed, baseline) is None
    assert relative_speed(baseline, failed) is None


def test_empty_and_transient_error_are_preserved() -> None:
    lib = library([[1_000_000_000] * 2] * 2)
    first = Output(id="tea", characters=0, empty=True, error="transient")
    lib["rounds"][0]["output_passes"] = [[first], lib["rounds"][0]["outputs"]]
    summary = aggregate(lib, {"tea"}, 2, 2)
    assert summary.empty == ("tea",)
    assert summary.errors == ("tea: transient",)
    assert not summary.complete
    first["error"] = None
    assert aggregate(lib, {"tea"}, 2, 2).complete


def test_rss_units() -> None:
    assert rss_bytes(2048, "darwin") == 2048
    assert rss_bytes(2048, "linux") == 2**21
    with pytest.raises(ValueError, match="Unsupported RSS"):
        rss_bytes(2048, "win32")


def test_footprint_excludes_bytecode_and_deduplicates(tmp_path: Path) -> None:
    source = tmp_path / "package.py"
    native = tmp_path / "extension.so"
    bytecode = tmp_path / "package.pyc"
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    cached = cache / "extra.dat"
    for path in [source, native, bytecode, cached]:
        path.write_bytes(b"12345")
    assert footprint([source, source, native, bytecode, cached, tmp_path / "missing"]) == 10


def test_conversion_errors_and_output_lengths_outside_timer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ticks = iter([10, 30, 40, 70, 80, 90])
    monkeypatch.setattr("tools.benchmark.worker.perf_counter_ns", lambda: next(ticks))
    docs = [Document(id=str(i), sha256="abc", bytes=1, encoding="utf-8") for i in range(3)]

    def convert(html: str) -> str | None:
        if html == "bad":
            raise ValueError("bad HTML")
        return "tea" if html == "good" else None

    times, outputs = corpus_pass(convert, docs, ["good", "bad", "empty"])
    assert times == [20, 30, 10]
    assert [o["characters"] for o in outputs] == [3, 0, 0]
    assert outputs[1]["error"] == "ValueError: bad HTML"
    assert outputs[2]["empty"] and outputs[2]["error"] is None


def test_timeout_remains_visible(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run, "WORK", tmp_path)

    def timeout(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired("worker", 300)

    monkeypatch.setattr("tools.benchmark.run.subprocess.run", timeout)
    assert run.worker("htomd", "speed")["error"] == "speed worker exceeded 300 seconds"


def test_reports_are_deterministic_and_expose_failures() -> None:
    results = example()
    text = tables(results)
    assert "| htomd 0.1 | 1.000 | 1.000–1.000 | 1.0 | 1.00 | 1.00× |" in text
    assert "| rival 1.0 | 2.000 | 2.000–2.000 | 0.5 | 0.50 | 2.00× |" in text
    assert "| htomd | 1.00 | 1.00 | 1.00 | 1.00 |" in text
    assert "| htomd | Pure Python / stdlib HTMLParser | 1 |" in text
    readme = update_readme("# Project\n\n## Development\n", results)
    assert update_readme(readme, results) == readme
    results["libraries"]["rival"]["rounds"][0] = Worker(error="timeout")
    assert "| rival 1.0 | incomplete | — | — | — | — |" in tables(results)
    assert "Errors: timeout." in detailed_report(results)
    with pytest.raises(ValueError, match="markers"):
        update_readme("<!-- benchmark:start -->", results)


def test_dependency_count_excludes_root_and_normalizes_distribution_names() -> None:
    lib = library([])
    lib["installation"]["packages"] = {"HTMD_py": "0.1.2"}
    assert dependency_count("htmd-py", lib) == 0
    lib["installation"]["packages"].update({"direct": "1", "transitive": "2"})
    assert dependency_count("htmd-py", lib) == 2


def test_installer_files_are_not_counted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from tools.benchmark.worker import installation

    class FakeDistribution:
        version = "1.0"
        files = [Path("file")]

        def __init__(self, name: str) -> None:
            self.metadata = {"Name": name}

        def locate_file(self, file: Path) -> Path:
            return tmp_path / self.metadata["Name"] / file

    for name in ["pip", "setuptools", "wheel", "htomd", "dependency"]:
        (tmp_path / name).mkdir()
        (tmp_path / name / "file").write_bytes(b"12345")
    monkeypatch.setattr(
        "importlib.metadata.distributions",
        lambda: [
            FakeDistribution(n) for n in ["pip", "setuptools", "wheel", "htomd", "dependency"]
        ],
    )
    # WHEEL tags are irrelevant to footprint accounting.
    assert installation("htomd")["installed_bytes"] == 10
    assert set(installation("htomd")["packages"]) == {"htomd", "dependency"}


def test_saved_report_matches_measurements() -> None:
    import json

    root = Path(__file__).resolve().parents[1]
    path = root / "tools/benchmark/results/macos-arm64.json"
    if not path.exists():
        pytest.skip("Initial results have not been recorded")
    results = cast(Results, json.loads(path.read_text(encoding="utf-8")))
    assert path.with_suffix(".md").read_text(encoding="utf-8") == detailed_report(results)
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert update_readme(readme, results) == readme
