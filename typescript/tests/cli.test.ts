import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const cli = fileURLToPath(new URL("../dist/cli.js", import.meta.url));
function run(args: string[], input: string | Buffer = Buffer.from([255])) {
  return spawnSync(process.execPath, [cli, ...args], { input, timeout: 10000 });
}

test("help never reads input", () => {
  const general = run([]);
  assert.equal(general.status, 0);
  assert.equal(general.stderr.length, 0);
  assert.match(general.stdout.toString(), /UTF-8 HTML on stdin/);
  for (const args of [["help"], ["--help"], ["-h"]]) {
    assert.deepEqual(run(args).stdout, general.stdout);
  }
  for (const topic of ["convert", "extract", "help", "version"]) {
    const result = run(["help", topic]);
    assert.equal(result.status, 0);
    assert.equal(result.stderr.length, 0);
    assert.deepEqual(result.stdout, run([topic, "--help"]).stdout);
  }
});

test("version comes from package metadata", () => {
  const metadata = JSON.parse(
    readFileSync(new URL("../package.json", import.meta.url), "utf8"),
  ) as { version: string };
  for (const command of ["version", "--version"]) {
    const result = run([command]);
    assert.equal(result.status, 0);
    assert.equal(result.stdout.toString(), `htomd ${metadata.version}\n`);
    assert.equal(result.stderr.length, 0);
  }
});

test("invalid arguments fail before reading stdin", () => {
  for (const args of [
    ["unknown"],
    ["help", "unknown"],
    ["version", "page.html"],
    ["convert", "page.html"],
    ["extract", "--json"],
    ["convert", "--url"],
    ["extract", "--url", "--url"],
  ]) {
    const result = run(args);
    assert.equal(result.status, 2);
    assert.equal(result.stdout.length, 0);
    assert.match(result.stderr.toString(), /usage: htomd/);
  }
});

test("strict UTF-8, BOM handling, and JSON wire keys", () => {
  for (const command of ["convert", "extract"]) {
    const invalid = run([command]);
    assert.equal(invalid.status, 1);
    assert.equal(invalid.stdout.length, 0);
    assert.match(invalid.stderr.toString(), /htomd:.*decode/);
    const result = run([command], "\ufeff<article><h1>Thé 日本語 🍵</h1><p>Text.</p></article>");
    assert.equal(result.status, 0);
    assert.equal(result.stderr.length, 0);
    if (command === "convert") {
      assert.equal(result.stdout.toString(), "# Thé 日本語 🍵\n\nText.\n");
    } else {
      const data = JSON.parse(result.stdout.toString()) as { metadata: Record<string, unknown> };
      assert.equal(data.metadata.published_time, null);
      assert.equal(data.metadata.canonical_url, null);
      assert.ok(!("publishedTime" in data.metadata));
    }
  }
});
