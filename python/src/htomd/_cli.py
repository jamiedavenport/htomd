"""Command-line conversion of HTML supplied on stdin."""

import argparse
import json
import os
import sys
from dataclasses import asdict
from importlib.metadata import version

from . import convert, extract


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="htomd",
        description=(
            "Extract Markdown and metadata from UTF-8 HTML on stdin. "
            "Pipe input from cat or curl; output goes to stdout. No file arguments or fetching."
        ),
        epilog=(
            "Examples:\n"
            "  cat page.html | htomd convert > page.md\n"
            "  cat page.html | htomd extract > page.json\n"
            "  curl -fsSL https://example.com | htomd convert --url https://example.com\n"
            "\nUse 'htomd help COMMAND' for command-specific help."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    version_text = f"htomd {version('htomd')}"
    parser.add_argument("--version", action="version", version=version_text)
    commands = parser.add_subparsers(dest="command")
    command_parsers: dict[str, argparse.ArgumentParser] = {}
    for name, description in (
        ("convert", "Write Markdown to stdout."),
        ("extract", "Write Markdown, metadata, and diagnostics as JSON to stdout."),
    ):
        command = commands.add_parser(
            name,
            help=description,
            description=f"Read UTF-8 HTML from stdin to EOF. {description}",
            epilog=f"Example: cat page.html | htomd {name}",
        )
        command.add_argument(
            "--url", help="Source URL for resolving references; no fetching occurs."
        )
        command_parsers[name] = command
    command_parsers["version"] = commands.add_parser(
        "version",
        help="Show the installed package version.",
        description="Show the installed version.",
    )
    help_parser = commands.add_parser(
        "help",
        help="Show general or command-specific help.",
        description="Show help for a command.",
    )
    command_parsers["help"] = help_parser
    help_parser.add_argument(
        "topic", nargs="?", choices=command_parsers, help="Command to describe."
    )
    args = parser.parse_args(argv)

    if args.command is None or args.command == "help":
        topic = args.topic if args.command == "help" else None
        (command_parsers[topic] if topic else parser).print_help()
        return 0
    if args.command == "version":
        print(version_text)
        return 0

    try:
        html = sys.stdin.buffer.read().decode("utf-8-sig")
        if args.command == "convert":
            output = convert(html, url=args.url)
        else:
            output = json.dumps(asdict(extract(html, url=args.url)), ensure_ascii=False, indent=2)
            output += "\n"
    except (OSError, UnicodeError) as error:
        print(f"htomd: {error}", file=sys.stderr)
        return 1

    try:
        sys.stdout.buffer.write(output.encode("utf-8"))
        sys.stdout.buffer.flush()
    except OSError as error:
        # Prevent a second output failure when Python flushes stdout during shutdown.
        with open(os.devnull, "wb") as sink:
            os.dup2(sink.fileno(), sys.stdout.fileno())
        if not isinstance(error, BrokenPipeError):
            print(f"htomd: {error}", file=sys.stderr)
        return 1
    return 0
