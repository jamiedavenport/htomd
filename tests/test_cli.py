import io
import json
import os
import subprocess
import sys
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

import pytest

import htomd
from htomd import _cli


def run_cli(*args: str, html: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    # The CLI's UTF-8 contract must not depend on the locale or Python text encoding.
    env = {**os.environ, "PYTHONIOENCODING": "ascii"}
    return subprocess.run(
        [sys.executable, "-m", "htomd", *args],
        input=html,
        capture_output=True,
        env=env,
        timeout=10,
    )


@pytest.mark.parametrize("command", ["convert", "extract"])
@pytest.mark.parametrize(
    "html",
    [
        "",
        "<article><h1>Tea</h1><p>Steep.</p></article>",
        "<p>Thé 日本語 🍵</p>",
        "\ufeff<p>Thé</p>",
        "<article><h1>Unclosed<p>Text <b>bold",
    ],
)
def test_piped_html(command: str, html: str) -> None:
    result = run_cli(command, html=html.encode("utf-8"))
    document = htomd.extract(html.removeprefix("\ufeff"))
    assert result.returncode == 0
    assert result.stderr == b""
    if command == "convert":
        assert result.stdout == document.markdown.encode("utf-8")
    else:
        expected = json.dumps(asdict(document), ensure_ascii=False, indent=2) + "\n"
        assert result.stdout == expected.encode("utf-8")
        data = json.loads(result.stdout)
        assert data["metadata"]["author"] is None
        assert isinstance(data["diagnostics"]["notes"], list)


@pytest.mark.parametrize("command", ["convert", "extract"])
def test_url_context(command: str) -> None:
    html = '<article><h1>Tea</h1><p><a href="../guide">Guide</a></p></article>'
    url = "https://example.com/articles/tea"
    result = run_cli(command, "--url", url, html=html.encode())
    assert result.returncode == 0
    assert result.stderr == b""
    if command == "convert":
        assert result.stdout.decode() == htomd.convert(html, url=url)
    else:
        assert json.loads(result.stdout) == json.loads(
            json.dumps(asdict(htomd.extract(html, url=url)))
        )
    assert b"https://example.com/guide" in result.stdout


@pytest.mark.parametrize(
    "args",
    [(), ("help",), ("--help",), ("convert", "--help"), ("extract", "--help")],
)
def test_help(args: tuple[str, ...]) -> None:
    result = run_cli(*args, html=b"\xff")
    assert result.returncode == 0
    assert b"usage: htomd" in result.stdout
    assert result.stderr == b""


def test_general_help() -> None:
    result = run_cli()
    assert result.stdout == run_cli("help").stdout == run_cli("--help").stdout
    assert b"UTF-8 HTML on stdin" in result.stdout
    assert b"cat page.html | htomd convert" in result.stdout
    assert b"curl -fsSL" in result.stdout
    assert b"--url" in result.stdout


@pytest.mark.parametrize("command", ["convert", "extract", "help", "version"])
def test_command_help(command: str) -> None:
    result = run_cli("help", command, html=b"\xff")
    assert result.returncode == 0
    assert result.stderr == b""
    assert result.stdout == run_cli(command, "--help").stdout


@pytest.mark.parametrize("command", ["version", "--version"])
def test_version(command: str) -> None:
    result = run_cli(command, html=b"\xff")
    assert result.returncode == 0
    assert result.stdout.decode() == f"htomd {version('htomd')}\n"
    assert result.stderr == b""


@pytest.mark.parametrize(
    "args",
    [
        ("unknown",),
        ("help", "unknown"),
        ("version", "page.html"),
        ("convert", "page.html"),
        ("extract", "page.html"),
        ("convert", "-"),
        ("extract", "--json"),
        ("convert", "--url"),
    ],
)
def test_usage_errors(args: tuple[str, ...]) -> None:
    result = run_cli(*args)
    assert result.returncode == 2
    assert result.stdout == b""
    assert b"usage: htomd" in result.stderr
    assert b"Traceback" not in result.stderr


@pytest.mark.parametrize("command", ["convert", "extract"])
def test_invalid_utf8(command: str) -> None:
    result = run_cli(command, html=b"<p>\xff</p>")
    assert result.returncode == 1
    assert result.stdout == b""
    assert b"htomd:" in result.stderr
    assert b"decode" in result.stderr
    assert b"Traceback" not in result.stderr


@pytest.mark.parametrize("stream", ["stdin", "stdout"])
def test_io_error(stream: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class FailingBuffer(io.BytesIO):
        def fileno(self) -> int:
            return destination.fileno()

        def read(self, size: int | None = -1) -> bytes:
            raise OSError("read failed")

        def write(self, data: object) -> int:
            raise OSError("write failed")

    stderr = io.StringIO()
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"<p>Tea</p>")))
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO()))
    monkeypatch.setattr(sys, "stderr", stderr)
    with (tmp_path / "output").open("wb") as destination:
        monkeypatch.setattr(sys, stream, io.TextIOWrapper(FailingBuffer()))
        assert _cli.main(["convert"]) == 1
    assert stderr.getvalue() == f"htomd: {'read' if stream == 'stdin' else 'write'} failed\n"


def test_broken_pipe() -> None:
    read_fd, write_fd = os.pipe()
    os.close(read_fd)
    with os.fdopen(write_fd, "wb") as output:
        result = subprocess.run(
            [sys.executable, "-m", "htomd", "convert"],
            input=b"<p>Tea</p>",
            stdout=output,
            stderr=subprocess.PIPE,
            timeout=10,
        )
    assert result.returncode == 1
    assert result.stderr == b""
