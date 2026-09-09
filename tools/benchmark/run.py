"""Prepare isolated wheels, run sequential workers, and save raw measurements."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import subprocess
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict, cast

from tools.benchmark.worker import ADAPTERS, ROOT, Document, Worker, load_corpus

HERE = Path(__file__).resolve().parent
WORK = ROOT / ".benchmark"
PYTHON_VERSION = "3.14.7"


class Library(TypedDict):
    installation: Worker
    wheel: dict[str, str | int]
    smoke: Worker
    rounds: list[Worker]
    rss: list[Worker]
    imports: list[Worker]


class Results(TypedDict):
    schema: int
    metadata: dict[str, Any]
    settings: dict[str, Any]
    corpus: list[Document]
    libraries: dict[str, Library]
    orders: list[list[str]]


def command(args: list[str], *, cwd: Path = ROOT) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def python_path(name: str) -> Path:
    return WORK / "envs" / name / "bin/python"


def worker(name: str, mode: str) -> Worker:
    output = WORK / "worker.json"
    output.unlink(missing_ok=True)
    invocation = [str(HERE / "worker.py"), name, mode, str(output)]
    if mode == "import":
        # Only time is imported before the timer; no harness/dependency preloading.
        script = (
            "import time\n"
            "start = time.perf_counter_ns()\n"
            f"__import__({ADAPTERS[name][0]!r})\n"
            "elapsed = time.perf_counter_ns() - start\n"
            f"with open({str(output)!r}, 'w') as stream:\n"
            "    stream.write('{\"import_ns\": %d}' % elapsed)\n"
        )
        invocation = ["-c", script]
    try:
        process = subprocess.run(
            [str(python_path(name)), "-I", "-B", *invocation],
            cwd=WORK,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return Worker(error=f"{mode} worker exceeded 300 seconds")
    if process.returncode or not output.exists():
        return Worker(error=f"{mode} worker exited {process.returncode}", stderr=process.stderr)
    result = cast(Worker, json.loads(output.read_text(encoding="utf-8")))
    if process.stderr:
        result["stderr"] = process.stderr
    return result


def wheel_record(path: Path) -> dict[str, str | int]:
    return {"filename": path.name, "bytes": path.stat().st_size, "sha256": digest(path)}


def competitor_wheel(name: str, installed: Worker) -> dict[str, str | int]:
    version = next(
        v for key, v in installed["packages"].items() if key.lower().replace("_", "-") == name
    )
    with urllib.request.urlopen(
        f"https://pypi.org/pypi/{name}/{version}/json", timeout=30
    ) as response:
        release = json.load(response)
    for file in release["urls"]:
        if file["packagetype"] != "bdist_wheel":
            continue
        py, abi, plat = file["filename"][:-4].rsplit("-", 3)[1:]
        tags = {
            f"{p}-{a}-{s}" for p in py.split(".") for a in abi.split(".") for s in plat.split(".")
        }
        if not tags.intersection(installed["wheel_tags"]):
            continue
        path = WORK / "wheels" / file["filename"]
        with urllib.request.urlopen(file["url"], timeout=60) as response:
            path.write_bytes(response.read())
        if digest(path) != file["digests"]["sha256"]:
            raise ValueError(f"Wheel checksum mismatch: {path.name}")
        return {**wheel_record(path), "url": file["url"]}
    raise ValueError(f"No published wheel matches installed tags for {name}")


def prepare() -> dict[str, Library]:
    (WORK / "wheels").mkdir(parents=True, exist_ok=True)
    # A version bump must not leave an older generated wheel in the next run.
    for old_wheel in (WORK / "wheels").glob("htomd-*.whl"):
        old_wheel.unlink()
    command(["uv", "build", "--wheel", "--no-sources", "--out-dir", str(WORK / "wheels")])
    wheels = list((WORK / "wheels").glob("htomd-*.whl"))
    if len(wheels) != 1:
        raise ValueError("Expected one freshly built htomd wheel; clear .benchmark/wheels")
    libraries: dict[str, Library] = {}
    for name in ADAPTERS:
        print(f"Preparing {name}", flush=True)
        command(["uv", "venv", "--clear", "--python", sys.executable, str(WORK / "envs" / name)])
        install = [
            "uv",
            "pip",
            "install",
            "--python",
            str(python_path(name)),
            "--only-binary",
            ":all:",
        ]
        if name == "htomd":
            install.extend(["--no-deps", str(wheels[0])])
        else:
            install.extend(["--require-hashes", "-r", str(HERE / "locks" / f"{name}.txt")])
        command(install)
        installed = worker(name, "installation")
        if "error" in installed:
            raise RuntimeError(installed["error"])
        wheel = wheel_record(wheels[0]) if name == "htomd" else competitor_wheel(name, installed)
        libraries[name] = Library(
            installation=installed,
            wheel=wheel,
            smoke=worker(name, "smoke"),
            rounds=[],
            rss=[],
            imports=[],
        )
    return libraries


def metadata() -> dict[str, Any]:
    return {
        "started_utc": datetime.now(UTC).isoformat(),
        "python": sys.version,
        "executable": sys.executable,
        "os": platform.platform(),
        "machine": platform.machine(),
        "cpu": command(["sysctl", "-n", "machdep.cpu.brand_string"]),
        "memory_bytes": int(command(["sysctl", "-n", "hw.memsize"])),
        "logical_cpus": os.cpu_count(),
        "revision": command(["git", "rev-parse", "HEAD"]),
        "dirty": bool(command(["git", "status", "--porcelain"])),
        "git_status": command(["git", "status", "--porcelain"]),
        "source_sha256": {
            str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT / "src/htomd").glob("*.py"))
        },
        "harness_sha256": {p.name: digest(p) for p in sorted(HERE.glob("*.py"))},
        "lock_sha256": {p.name: digest(p) for p in sorted((HERE / "locks").glob("*.txt"))},
        "manifest_sha256": digest(ROOT / "tests/fixtures/real/manifest.json"),
        "build_inputs_sha256": {
            name: digest(ROOT / name) for name in ["README.md", "pyproject.toml", "MANIFEST.in"]
        },
        "uv": command(["uv", "--version"]),
    }


def save(path: Path, results: Results) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--seed", type=int, default=20260909)
    parser.add_argument("--output", type=Path, default=WORK / "results.json")
    args = parser.parse_args()
    if (
        platform.python_version() != PYTHON_VERSION
        or sys.platform != "darwin"
        or platform.machine() != "arm64"
    ):
        parser.error("Initial harness targets macOS ARM64 with Python 3.14.7; run through mise")
    documents, _ = load_corpus()
    info = metadata()
    libraries = prepare()
    results = Results(
        schema=1,
        metadata=info,
        corpus=documents,
        libraries=libraries,
        orders=[],
        settings={
            "seed": args.seed,
            "rounds": 5,
            "warmup_passes": 1,
            "minimum_passes": 5,
            "minimum_timed_seconds": 2,
            "rss_workers": 3,
            "import_workers": 20,
            "worker_timeout_seconds": 300,
            "gc_enabled": True,
            "threads": 1,
            "adapters": {name: entry[2] for name, entry in ADAPTERS.items()},
            "mode": "smoke" if args.smoke else "full",
        },
    )
    save(args.output, results)
    if args.smoke:
        for name, library in libraries.items():
            print(f"{name}: {library['smoke'].get('error', 'passed')}")
        if any("error" in lib["smoke"] for lib in libraries.values()):
            raise SystemExit("One or more adapters failed; see saved results")
        return
    rng = random.Random(args.seed)
    for round_index in range(5):
        order = list(libraries)
        rng.shuffle(order)
        results["orders"].append(order)
        for name in order:
            print(f"Round {round_index + 1}/5: {name}", flush=True)
            libraries[name]["rounds"].append(worker(name, "speed"))
            save(args.output, results)
    for name, library in libraries.items():
        print(f"Memory and import workers: {name}", flush=True)
        library["rss"] = [worker(name, "rss") for _ in range(3)]
        library["imports"] = [worker(name, "import") for _ in range(20)]
        save(args.output, results)
    results["metadata"]["finished_utc"] = datetime.now(UTC).isoformat()
    save(args.output, results)
    print(f"Saved {args.output}")
    if any(
        "error" in sample
        or any(
            output["error"]
            for batch in sample.get("output_passes", [sample.get("outputs", [])])
            for output in batch
        )
        for lib in libraries.values()
        for sample in [lib["smoke"], *lib["rounds"], *lib["rss"], *lib["imports"]]
    ):
        raise SystemExit("Worker failures recorded; generate the report to review them")


if __name__ == "__main__":
    main()
