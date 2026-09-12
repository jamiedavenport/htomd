"""Compare all maintained implementations using offline fixtures and checkout builds."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from tools.native import binary

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"


def cases() -> list[dict[str, Any]]:
    synthetic = json.loads((FIXTURES / "synthetic/cases.json").read_text(encoding="utf-8"))
    edge = json.loads((FIXTURES / "conformance.json").read_text(encoding="utf-8"))
    manifest = json.loads((FIXTURES / "real/manifest.json").read_text(encoding="utf-8"))
    real = [
        {
            "id": row["id"],
            "html": (FIXTURES / "real" / (row["id"] + ".html"))
            .read_bytes()
            .decode(row["encoding"]),
            "url": row["source_url"],
        }
        for row in manifest
    ]
    overrides = {case["id"]: case for case in edge if "html" not in case}
    for case in real:
        case.update(overrides.pop(case["id"], {}))
    assert not overrides, f"Unknown real fixture overrides: {list(overrides)}"
    return [*synthetic, *(case for case in edge if "html" in case), *real]


def commands() -> list[list[str]]:
    """Use the current Python environment and existing checkout build outputs."""
    node = shutil.which("node")
    if node is None:
        raise SystemExit("Node must be installed")
    cli = ROOT / "typescript/dist/cli.js"
    for language, path in (("typescript", cli), ("go", binary("go")), ("rust", binary("rust"))):
        if not path.is_file():
            raise SystemExit(f"Missing {language} CLI; run mise run build first")
    return [
        [sys.executable, "-m", "htomd"],
        [node, str(cli)],
        [str(binary("go"))],
        [str(binary("rust"))],
    ]


def check_cli_contract(invocations: list[list[str]], work: Path) -> None:
    controls: list[tuple[list[str], bytes, int]] = [
        (["convert"], b"\xef\xbb\xbf<p>Tea</p>", 0),
        (["extract"], b"\xef\xbb\xbf<p>Tea</p>", 0),
        (["convert", "--url", "https://example.org/"], b"<p><a href='x'>X</a></p>", 0),
        (["extract", "--url="], b"<p>Tea</p>", 0),
        (["extract", "--url=-1"], b"<p>Tea</p>", 0),
        (["extract", "--url", "first", "--url", ""], b"<p>Tea</p>", 0),
        (["extract", "--url=first", "--url", "last"], b"<p>Tea</p>", 0),
        (["extract", "--url=-.5"], b"<p>Tea</p>", 0),
        (["version"], b"\xff", 0),
        (["--version"], b"\xff", 0),
        (["convert"], b"\xff", 1),
        (["extract"], b"\xed\xa0\x80", 1),
        (["unknown"], b"\xff", 2),
        (["help", "unknown"], b"\xff", 2),
        (["version", "page.html"], b"\xff", 2),
        (["extract", "--url", "-unknown"], b"\xff", 2),
        (["convert", "page.html"], b"\xff", 2),
        (["extract", "--json"], b"\xff", 2),
        (["convert", "--url"], b"\xff", 2),
        (["extract", "--url", "--url"], b"\xff", 2),
        (["extract", "--url", "first", "--url"], b"\xff", 2),
    ]
    for args, data, status in controls:
        results = [
            subprocess.run([*cmd, *args], input=data, capture_output=True, cwd=work, timeout=10)
            for cmd in invocations
        ]
        for result in results:
            assert result.returncode == status, (args, result.stderr)
            if status:
                assert not result.stdout
                marker = b"usage: htomd" if status == 2 else b"htomd:"
                assert marker in result.stderr and b"Traceback" not in result.stderr, (
                    args,
                    result.stderr,
                )
            else:
                assert not result.stderr
        # Help/version are text streams and use platform line endings in Python.
        assert all(results[0].stdout.replace(b"\r\n", b"\n") == r.stdout for r in results[1:])
    help_cases = [
        [],
        ["help"],
        ["--help"],
        *(["help", topic] for topic in ("convert", "extract", "help", "version")),
        *([topic, "--help"] for topic in ("convert", "extract", "help", "version")),
    ]
    for args in help_cases:
        for cmd in invocations:
            result = subprocess.run(
                [*cmd, *args], input=b"\xff", capture_output=True, cwd=work, timeout=10
            )
            assert result.returncode == 0 and not result.stderr, (cmd, args, result.stderr)
            assert b"usage: htomd" in result.stdout, (cmd, args)
    if os.name != "nt":
        for cmd in invocations:
            read_fd, write_fd = os.pipe()
            os.close(read_fd)
            with os.fdopen(write_fd, "wb") as output:
                result = subprocess.run(
                    [*cmd, "convert"],
                    input=b"<p>Tea</p>",
                    stdout=output,
                    stderr=subprocess.PIPE,
                    cwd=work,
                    timeout=10,
                )
            assert result.returncode == 1 and not result.stderr, (cmd, result.stderr)
    print(f"CLI: {len(controls)} input, argument, and exit-status comparisons match.")


def main() -> None:
    invocations = commands()
    with tempfile.TemporaryDirectory(prefix="htomd-conformance-") as directory:
        compare(invocations, Path(directory))


def expected_output(reference: bytes, command: str, overrides: dict[str, Any]) -> bytes:
    """Apply only explicit, fixture-local native-runtime expectations."""
    if not overrides:
        return reference
    assert set(overrides) <= {"markdown", "metadata", "markdown_replacements"}
    document = json.loads(reference) if command == "extract" else None
    markdown = document["markdown"] if document is not None else reference.decode("utf-8")
    markdown = overrides.get("markdown", markdown)
    assert isinstance(markdown, str)
    for old, new in overrides.get("markdown_replacements", []):
        assert markdown.count(old) == 1, f"Expected one replacement occurrence: {old!r}"
        markdown = markdown.replace(old, new, 1)
    if document is None:
        return markdown.encode("utf-8")
    document["markdown"] = markdown
    document["metadata"].update(overrides.get("metadata", {}))
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def compare(invocations: list[list[str]], work: Path) -> None:
    inputs = cases()
    for case in inputs:
        for command in ["convert", "extract"]:
            argv = [command]
            if case.get("url") is not None:
                argv += ["--url", case["url"]]
            results = [
                subprocess.run(
                    [*invocation, *argv],
                    input=case["html"].encode("utf-8"),
                    capture_output=True,
                    cwd=work,
                    timeout=30,
                )
                for invocation in invocations
            ]
            for invocation, result in zip(invocations, results, strict=True):
                assert result.returncode == 0, (case["id"], command, invocation, result.stderr)
                assert not result.stderr, (case["id"], command, invocation, result.stderr)
            for language, result in zip(("typescript", "go", "rust"), results[1:], strict=True):
                expected = expected_output(results[0].stdout, command, case.get(language, {}))
                assert expected == result.stdout, (case["id"], command, language, "CLI mismatch")
            if command == "convert" and "markdown" in case:
                assert results[0].stdout == case["markdown"].encode("utf-8"), case["id"]
    print(
        f"CLI: {len(inputs) * 2} UTF-8 Markdown/JSON checks passed, "
        "including explicit runtime expectations."
    )
    check_cli_contract(invocations, work)


if __name__ == "__main__":
    main()
