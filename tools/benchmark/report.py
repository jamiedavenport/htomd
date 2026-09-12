"""Generate Markdown from saved results; never rerun measurements implicitly."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import cast

from tools.benchmark.run import Library, Results
from tools.benchmark.worker import ROOT, Output, Worker

START = "<!-- benchmark:start -->"
END = "<!-- benchmark:end -->"
IMPLEMENTATIONS = {
    "htomd": "Pure Python / stdlib HTMLParser",
    "markdownify": "Python / BeautifulSoup + stdlib HTMLParser",
    "html2text": "Pure Python / stdlib HTMLParser",
    "trafilatura": "Python + native C via lxml",
    "html-to-markdown": "Rust core / Python bindings",
    "htmd-py": "Rust core / Python bindings",
}
DEPENDENCY_NOTE = (
    "Dependency counts include all installed direct and transitive runtime packages, "
    "excluding the library itself, interpreter and installer tools. "
    "No optional extras were selected. "
    "Counts come from the saved isolated installations. Bundled native code and Rust/C libraries "
    "are not counted as Python packages: zero package dependencies does not mean pure Python."
)


@dataclass(frozen=True)
class Summary:
    seconds: float | None
    low: float | None
    high: float | None
    complete: bool
    errors: tuple[str, ...]
    empty: tuple[str, ...]


def observations(worker: Worker) -> list[Output]:
    return [
        output
        for batch in worker.get("output_passes", [worker.get("outputs", [])])
        for output in batch
    ]


def aggregate(library: Library, documents: set[str], rounds: int, passes: int) -> Summary:
    errors: set[str] = set()
    empty: set[str] = set()
    medians: list[float] = []
    complete = len(library["rounds"]) == rounds and "error" not in library["smoke"]
    for worker in library["rounds"]:
        if "error" in worker:
            errors.add(worker["error"])
            complete = False
        times = worker.get("corpus_ns", [])
        doc_times = worker.get("document_ns", {})
        if len(times) < passes or sum(times) < 2_000_000_000 or set(doc_times) != documents:
            complete = False
        if any(len(values) != len(times) for values in doc_times.values()):
            complete = False
        if times:
            medians.append(median(times) / 1e9)
        outputs = observations(worker)
        if {o["id"] for o in outputs} != documents:
            complete = False
        for output in outputs:
            if output["error"]:
                errors.add(f"{output['id']}: {output['error']}")
                complete = False
            if output["empty"]:
                empty.add(output["id"])
    return Summary(
        median(medians) if medians else None,
        min(medians) if medians else None,
        max(medians) if medians else None,
        complete,
        tuple(sorted(errors)),
        tuple(sorted(empty)),
    )


def relative_speed(competitor: Summary, baseline: Summary) -> float | None:
    if not competitor.complete or not baseline.complete or not baseline.seconds:
        return None
    return competitor.seconds / baseline.seconds if competitor.seconds is not None else None


def metric(samples: list[Worker], key: str, divisor: float) -> str:
    # The only dynamic Worker access: restrict keys at the JSON/report boundary.
    values = [
        cast(dict[str, int], sample)[key]
        for sample in samples
        if key in sample and "error" not in sample
    ]
    return f"{median(values) / divisor:.2f}" if values else "—"


def dependency_count(name: str, library: Library) -> int:
    packages = {
        package.lower().replace("_", "-") for package in library["installation"]["packages"]
    }
    return len(packages - {name.lower().replace("_", "-")})


def tables(results: Results) -> str:
    documents = {d["id"] for d in results["corpus"]}
    total_bytes = sum(d["bytes"] for d in results["corpus"])
    settings = results["settings"]
    summaries = {
        name: aggregate(lib, documents, settings["rounds"], settings["minimum_passes"])
        for name, lib in results["libraries"].items()
    }
    lines = [
        "| Library | Conversion implementation | Extra Python packages |",
        "| --- | --- | ---: |",
    ]
    for name, lib in results["libraries"].items():
        implementation = IMPLEMENTATIONS.get(name, "Not classified")
        lines.append(f"| {name} | {implementation} | {dependency_count(name, lib)} |")
    lines.extend(
        [
            "",
            "| Library | Corpus seconds | Round median range (s) | Pages/s | Input MiB/s | "
            "Relative speed |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for name, lib in results["libraries"].items():
        item = summaries[name]
        version = next(
            v
            for n, v in lib["installation"]["packages"].items()
            if n.lower().replace("_", "-") == name
        )
        label = f"{name} {version}"
        ratio = relative_speed(item, summaries["htomd"])
        speed = f"{ratio:.2f}×" if ratio is not None else "—"
        if item.complete and item.seconds:
            lines.append(
                f"| {label} | {item.seconds:.3f} | {item.low:.3f}–{item.high:.3f} | "
                f"{len(documents) / item.seconds:.1f} | "
                f"{total_bytes / 2**20 / item.seconds:.2f} | {speed} |"
            )
        else:
            lines.append(f"| {label} | incomplete | — | — | — | — |")
    lines.extend(
        [
            "",
            "| Library | Peak RSS MiB | Import ms | Wheel KiB | Installed MiB |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for name, lib in results["libraries"].items():
        lines.append(
            f"| {name} | {metric(lib['rss'], 'rss_bytes', 2**20)} | "
            f"{metric(lib['imports'], 'import_ns', 1e6)} | "
            f"{int(lib['wheel']['bytes']) / 1024:.2f} | "
            f"{lib['installation']['installed_bytes'] / 2**20:.2f} |"
        )
    return "\n".join(lines)


def overview(results: Results) -> str:
    meta = results["metadata"]
    return (
        f"Measured {meta['started_utc'][:10]} on {meta['cpu']} ({meta['machine']}, "
        f"{meta['memory_bytes'] / 2**30:g} GiB RAM), {meta['os']}, Python "
        f"{meta['python'].split()[0]}. {len(results['corpus'])} offline sanitised pages, "
        f"{sum(d['bytes'] for d in results['corpus']) / 2**20:.2f} MiB input. "
        "Single-threaded; five fresh rounds. Relative speed = competitor time / htomd time; "
        "above 1 means htomd is faster."
    )


CAVEATS = (
    "Defaults perform different work: htomd.convert() selects content and extracts metadata; "
    "Trafilatura extracts main content with Markdown output selected. markdownify, html2text, "
    "and htmd-py convert markup; html-to-markdown returns content and metadata with its defaults. "
    "Output size and extraction coverage differ. These timings do not measure output quality."
)


def readme_block(results: Results) -> str:
    return "\n\n".join(
        [
            START,
            "## Performance",
            f"Compare throughput, memory use, and dependencies across {len(results['corpus'])} "
            "offline HTML pages in the [benchmark report](tools/benchmark/results/macos-arm64.md). "
            "See [methodology and reproduction](tools/benchmark/README.md) for details.",
            "Libraries perform different work by default. Timings do not measure output quality.",
            END,
        ]
    )


def update_readme(text: str, results: Results) -> str:
    block = readme_block(results)
    if START in text and END in text:
        start = text.index(START)
        end = text.index(END, start) + len(END)
        return text[:start] + block + text[end:]
    if START in text or END in text:
        raise ValueError("Incomplete benchmark markers in README")
    return text.replace("## Development", block + "\n\n## Development", 1)


def detailed_report(results: Results) -> str:
    meta = results["metadata"]
    lines = [
        "# Benchmark measurements",
        overview(results),
        tables(results),
        DEPENDENCY_NOTE,
        CAVEATS,
        f"Source revision: `{meta['revision']}`; dirty: `{meta['dirty']}`. "
        "Exact source, harness, wheel, lock and corpus hashes are in the adjacent JSON.",
        "## Reproduction",
        "See [benchmark instructions](../README.md). "
        "Regenerate this report and the README from saved JSON with "
        "`python -m tools.benchmark.report tools/benchmark/results/macos-arm64.json --readme`.",
        "## Failures and output diagnostics",
        "Empty output is recorded separately from exceptions and is not a quality score. "
        "Incomplete timing rounds never receive complete-corpus throughput or ratios. "
        "Memory/import medians use successful workers; counts below expose missing samples.",
    ]
    documents = {d["id"] for d in results["corpus"]}
    for name, lib in results["libraries"].items():
        summary = aggregate(
            lib, documents, results["settings"]["rounds"], results["settings"]["minimum_passes"]
        )
        lengths = (
            [o["characters"] for o in lib["rounds"][0].get("outputs", [])] if lib["rounds"] else []
        )
        lines.append(f"### {name}")
        lines.append(
            f"Adapter: `{results['settings']['adapters'][name]}`; all other options default."
        )
        lines.append(
            f"Complete timing: {summary.complete}. "
            f"Successful RSS workers: {sum('rss_bytes' in w for w in lib['rss'])}/3; "
            f"successful import workers: {sum('import_ns' in w for w in lib['imports'])}/20. "
            f"First warm-up output: {sum(lengths):,} characters. "
            f"Empty documents across timing passes: {len(summary.empty)}."
        )
        if summary.empty:
            lines.append("Empty IDs: " + ", ".join(f"`{name}`" for name in summary.empty) + ".")
        failures = list(summary.errors)
        for sample in [lib["smoke"], *lib["rss"], *lib["imports"]]:
            if "error" in sample:
                failures.append(sample["error"])
            failures.extend(
                f"{output['id']}: {output['error']}"
                for output in observations(sample)
                if output["error"]
            )
        lines.append("Errors: " + ("; ".join(sorted(set(failures))) if failures else "none") + ".")
        warnings = sum(
            bool(w.get("stderr")) for w in [*lib["rounds"], *lib["rss"], *lib["imports"]]
        )
        lines.append(f"Workers with stderr: {warnings}; full text retained in JSON.")
        lines.append(
            "Installed packages: "
            + ", ".join(f"`{n}=={v}`" for n, v in sorted(lib["installation"]["packages"].items()))
            + "."
        )
        lines.append(f"Wheel: `{lib['wheel']['filename']}`; SHA-256 `{lib['wheel']['sha256']}`.")
    return "\n\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    parser.add_argument("--readme", action="store_true")
    parser.add_argument(
        "--check", action="store_true", help="Check generated files without writing"
    )
    args = parser.parse_args()
    results = cast(Results, json.loads(args.results.read_text(encoding="utf-8")))
    if results["schema"] != 1 or results["settings"]["mode"] != "full":
        parser.error("Expected schema 1 full benchmark results")
    outputs = {args.results.with_suffix(".md"): detailed_report(results)}
    if args.readme:
        readme = ROOT / "README.md"
        outputs[readme] = update_readme(readme.read_text(encoding="utf-8"), results)
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                raise SystemExit(f"Generated report is stale: {path}")
        else:
            path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
