[![htomd](assets/banner.svg)](https://jamiedavenport.me/blog/introducing-htomd/)

[![PyPI version](https://img.shields.io/pypi/v/htomd?color=black)](https://pypi.org/project/htomd/)

Extract Markdown and metadata from HTML. Implementations support Python 3.12+,
Node 24+, Go 1.27+, and Rust 1.98+. None fetch network content. Python, TypeScript,
and Go have no runtime dependencies; Rust uses Serde, Serde JSON, and URL.

[Documentation](https://htomd.dev) · [Introducing htomd](https://jamiedavenport.me/blog/introducing-htomd/)

## Installation

```sh
python -m pip install htomd
```

For an isolated command-line installation:

```sh
uv tool install htomd
```

## Python API

```python
import htomd

html = "<article><h1>Hello</h1><p>Readable text.</p></article>"

# Markdown only.
print(htomd.convert(html))

# Markdown, metadata, and extraction diagnostics.
document = htomd.extract(html, url="https://example.com/article")
print(document.markdown)
print(document.metadata.title)
```

Pass decoded HTML strings. The optional `url` resolves relative references; it
never fetches a page. Results are immutable, missing metadata is `None`, and
empty content yields empty Markdown.

## TypeScript

The [TypeScript package](typescript/README.md) provides the same extraction pipeline
for Node 24+, with no runtime dependencies. Its ESM API uses an options object:

```ts
import { extract } from "@jamiedavenport/htomd";

const document = extract(html, { url: "https://example.com/article" });
console.log(document.metadata.title);
```

## Go and Rust

The [Go package](go/README.md) exposes `Extract(html, Options)` and
`Convert(html, Options)`, returning results and errors for invalid UTF-8 input.
The [Rust crate](rust/README.md) exposes `extract(&str, Options)` and
`convert(&str, Options)`, returning owned results. Both use idiomatic public
structs, preserve optional metadata, and provide the same CLI commands.

These ports are available in this checkout; registry installation becomes
available after their first release. Package READMEs describe installation,
dependency choices, and intentional native-runtime differences.

## Command line

```sh
cat page.html | htomd convert > page.md
cat page.html | htomd extract > page.json
curl -fsSL https://example.com/article | htomd convert --url https://example.com/article
```

Both commands read UTF-8 HTML from stdin. `convert` writes Markdown; `extract`
writes JSON with `markdown`, `metadata`, and `diagnostics`. Use shell redirection
or pipes for files; the commands do not accept file arguments.

Run `htomd --help` or `htomd help extract` for usage. `python -m htomd` also works.

## Limitations

Best suited to articles and documentation. Extraction is best-effort and can
miss content or retain clutter. JavaScript, browser layout, math, and SVG are
unsupported. Simple tables use GFM; complex tables become row/cell text.

<!-- benchmark:start -->

## Performance

Compare throughput, memory use, and dependencies across 115 offline HTML pages in the [benchmark report](tools/benchmark/results/macos-arm64.md). See [methodology and reproduction](tools/benchmark/README.md) for details.

Libraries perform different work by default. Timings do not measure output quality.

<!-- benchmark:end -->

## Development

```sh
mise trust
mise install
mise run setup
mise run build
mise run check
```

`setup` installs the Python development environment and locked dependencies.
`build` compiles TypeScript into `typescript/dist/`, Go into `go/bin/`, and the
Rust release CLI into `rust/target/release/`, directly from the checkout.
Python runs from the existing development environment and needs no separate build.

Build once before checking: `check` runs formatting, lint, types, native API tests,
repository tests, and cross-language conformance against those outputs. The
individual tasks are `mise run lint`, `mise run test`, and
`mise run test:conformance`; none rebuild the CLIs or install distributions.
Normal Go/Rust test compilation and Rust Clippy checks are separate from the
release CLI build. All four package suites use the shared cases in
`tests/fixtures/synthetic/cases.json`.

PR CI checks out the commit and runs `setup` → `build` → native/integration tests
→ conformance independently on Linux, Windows, and macOS. Linux also runs `lint`
after building. Python 3.12 and 3.13 run the Python and repository suites separately.
No package archives are uploaded or downloaded for these tests. The website has
its own unchanged build job.

Install hooks with `mise exec -- uv run --project python --locked pre-commit install`;
run them with `mise run hooks`. Keep Python, TypeScript, and Go runtime dependencies
empty; Rust's three direct dependencies are documented in its README. Add focused
regression tests for behavior changes. See the [Python](python/README.md) and
[TypeScript](typescript/README.md) READMEs for package commands, the
[fixture guide](tests/fixtures/real/README.md) for snapshots, and
[Releases](#releases) for publishing.

Shipwright maintains these ports from the Python behavioral reference. Use
`sw-explore` to map behavior, then `sw-ts`, `sw-go`, or `sw-rust` for the requested
language. Skills live in `.agents/skills/`; `shipwright.toml` lists the targets.
Compatibility means equivalent I/O through idiomatic implementations. Explicit
runtime exceptions live in the shared conformance fixtures. Corpus overrides
may reference an existing real fixture ID and replace one exact Markdown link;
missing or ambiguous replacements fail validation.

Conformance runs the current Python environment, compiled JavaScript on Node,
and the built Go/Rust CLIs on synthetic, edge, and saved-page fixtures. Missing
implementations, output mismatches, and CLI contract violations fail the run.
Isolated installed-distribution and generated-consumer checks are intentionally
omitted; native API tests and shared conformance cover behavior.

## Releases

Update the package versions, Go `Version` constant, `shipwright.toml`, affected
lockfiles, and `CHANGELOG.md` together. Run `mise run setup`, `mise run build`,
and `mise run check`, then preview release preparation:

```sh
mise install
mise run release
```

`mise run release` runs `shipwright release --dry-run`: it prepares packages and
host-platform native archives without publishing or requiring registry tokens.
It checks existing tags and assets for conflicts. The current `v0.1.1` root tag
points to an older commit; choose the next release version rather than moving it.

Commit and push the release changes, then publish a GitHub Release tagged
`v<version>`. This starts CI; after that release's CI run succeeds, the
[release workflow](.github/workflows/release.yml) runs
`shipwright release "$PACKAGE"` in a four-language matrix. Each job
builds and publishes directly from that release commit. The workflow validates
the triggering tag and tested commit. Shipwright validates manifest versions,
creates the Go module tag, and uploads
configured Linux native archives. Windows/macOS downloads are not yet included.

PyPI and npm use trusted publishing; Rust uses the existing crates.io
authentication action. Keep the `release.yml` trusted-publisher bindings and the
`pypi`, `npm`, and `crates-io` environments. Git and GitHub uploads use the built-in
Actions token. No manually configured registry secrets are needed.

Mise installs Shipwright from the `swb` crate, pinned to 0.2.0.
The release workflow must be on the default branch
to receive CI completion events; it checks out the commit tested by the release's
CI run. Successful pull-request and branch CI runs do not publish packages.

Rerun failed matrix jobs after fixing their cause. Existing npm/crates.io versions
are skipped, uv resumes Python files, and matching Go tags and native assets are
kept. Conflicting tags or asset checksums fail without overwriting them.

## License

[MIT](https://github.com/jamiedavenport/htomd/blob/main/LICENSE), copyright 2026 JXD Ltd.
[Test fixtures](https://github.com/jamiedavenport/htomd/blob/main/tests/fixtures/real/README.md)
have separate licenses.

<!-- Edit the shared source in jamiedavenport/jamiedavenport.me: readme-snippets/more-by-jamie.md. -->
<!-- md:include start path="more-by-jamie.md" required=true -->

## More by Jamie

| Name        | Description                                                           | Website                                    | Repo                                                    |
| ----------- | --------------------------------------------------------------------- | ------------------------------------------ | ------------------------------------------------------- |
| PolicyStack | Privacy policies and cookie consent driven by the same configuration. | [policystack.dev](https://policystack.dev) | [GitHub](https://github.com/jamiedavenport/policystack) |
| Sidequest   | A personal task manager designed with ADHD in mind.                   | [sdqst.app](https://sdqst.app)             | [GitHub](https://github.com/jamiedavenport/sidequest)   |
| Capd        | A private Mac app for saving and finding links, notes, and images.    | [capd.jxd.dev](https://capd.jxd.dev)       | [GitHub](https://github.com/jamiedavenport/capd)        |
| htomd       | Focused Markdown and metadata from messy HTML, in pure Python.        |                                            | [GitHub](https://github.com/jamiedavenport/htomd)       |

<!-- md:include end -->
