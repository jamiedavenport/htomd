#!/usr/bin/env node
import { readFileSync, writeSync } from "node:fs";
import { extract } from "./index.js";

const commands = new Set(["convert", "extract", "help", "version"]);

function help(topic?: string): string {
  if (topic === "convert" || topic === "extract") {
    const description =
      topic === "convert"
        ? "Write Markdown to stdout."
        : "Write Markdown, metadata, and diagnostics as JSON to stdout.";
    return `usage: htomd ${topic} [-h] [--url URL]

Read UTF-8 HTML from stdin to EOF. ${description}

options:
  -h, --help  Show this help message.
  --url URL   Source URL for resolving references; no fetching occurs.

Example: cat page.html | htomd ${topic}
`;
  }
  if (topic === "version" || topic === "help") {
    return `usage: htomd ${topic} [-h]${topic === "help" ? " [COMMAND]" : ""}

${topic === "help" ? "Show general or command-specific help." : "Show the installed package version."}
`;
  }
  return `usage: htomd [-h] [--version] {convert,extract,version,help} ...

Extract Markdown and metadata from UTF-8 HTML on stdin.
Pipe input from cat or curl; output goes to stdout. No file arguments or fetching.

commands:
  convert  Write Markdown to stdout.
  extract  Write Markdown, metadata, and diagnostics as JSON to stdout.
  version  Show the installed package version.
  help     Show general or command-specific help.

options:
  -h, --help  Show this help message.
  --version   Show the installed package version.

Examples:
  cat page.html | htomd convert > page.md
  cat page.html | htomd extract > page.json
  curl -fsSL https://example.com | htomd convert --url https://example.com

Use 'htomd help COMMAND' for command-specific help.
`;
}

function write(output: string): void {
  const bytes = Buffer.from(output);
  let offset = 0;
  while (offset < bytes.length) {
    offset += writeSync(1, bytes, offset);
  }
}

function usage(message: string): number {
  process.stderr.write(
    `usage: htomd [-h] [--version] {convert,extract,version,help} ...\nhtomd: ${message}\n`,
  );
  return 2;
}

function main(args: string[]): number {
  const [command, ...rest] = args;
  if (command === undefined || command === "--help" || command === "-h") {
    write(help());
    return 0;
  }
  if (command === "--version") {
    const metadata = JSON.parse(
      readFileSync(new URL("../package.json", import.meta.url), "utf8"),
    ) as { version: string };
    write(`htomd ${metadata.version}\n`);
    return 0;
  }
  if (!commands.has(command)) {
    return usage(`unknown command: ${command}`);
  }
  if (rest.includes("--help") || rest.includes("-h")) {
    write(help(command));
    return 0;
  }
  if (command === "help") {
    if (rest.length > 1 || (rest[0] !== undefined && !commands.has(rest[0]))) {
      return usage("unknown help topic");
    }
    write(help(rest[0]));
    return 0;
  }
  if (command === "version") {
    return rest.length ? usage("version accepts no arguments") : main(["--version"]);
  }
  let url: string | null = null;
  for (let index = 0; index < rest.length; index++) {
    const argument = rest[index]!;
    if (argument.startsWith("--url=")) {
      url = argument.slice(6);
    } else if (argument === "--url") {
      const value = rest[++index];
      if (value === undefined || (value.startsWith("-") && !/^-\d+$|^-\d*\.\d+$/.test(value))) {
        return usage("--url requires a value");
      }
      url = value;
    } else {
      return usage(`unrecognized argument: ${argument}`);
    }
  }
  let html: string;
  try {
    html = new TextDecoder("utf-8", { fatal: true }).decode(readFileSync(0));
  } catch (error) {
    process.stderr.write(`htomd: could not read or decode UTF-8 input: ${String(error)}\n`);
    return 1;
  }
  const document = extract(html, { url });
  if (command === "convert") {
    write(document.markdown);
  } else {
    const metadata = document.metadata;
    const output = {
      markdown: document.markdown,
      metadata: {
        title: metadata.title,
        author: metadata.author,
        description: metadata.description,
        language: metadata.language,
        published_time: metadata.publishedTime,
        url: metadata.url,
        canonical_url: metadata.canonicalUrl,
      },
      diagnostics: document.diagnostics,
    };
    write(JSON.stringify(output, null, 2) + "\n");
  }
  return 0;
}

try {
  process.exitCode = main(process.argv.slice(2));
} catch (error) {
  const code = (error as NodeJS.ErrnoException).code;
  if (code !== "EPIPE") {
    process.stderr.write(`htomd: ${String(error)}\n`);
  }
  process.exitCode = 1;
}
