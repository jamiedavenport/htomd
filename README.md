[![htomd](assets/banner.svg)](https://jamiedavenport.me/blog/introducing-htomd/)

[![PyPI version](https://img.shields.io/pypi/v/htomd?color=black)](https://pypi.org/project/htomd/)

Extract Markdown and metadata from HTML. Available for Python 3.12+ and Node 24+,
with no runtime dependencies or network access.

[Introducing htomd](https://jamiedavenport.me/blog/introducing-htomd/)

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

Build once before checking: `check` runs static checks and tests against the
existing artifacts. `mise run lint` runs static checks alone; `mise run test`
runs the suites and isolated package checks. Both package suites use the shared
cases in `tests/fixtures/synthetic/cases.json`.

Install hooks with `mise exec -- uv run --project python --locked pre-commit install`;
run them with `mise run hooks`. Keep runtime dependencies empty and add focused
regression tests for behavior changes. See the [Python](python/README.md) and
[TypeScript](typescript/README.md) READMEs for package commands, the
[fixture guide](tests/fixtures/real/README.md) for snapshots, and
[Releases](#releases) for publishing.

## Releases

Update both package versions, lockfiles, and `CHANGELOG.md`. Clear old build
artifacts, then run `mise run build` and `mise run check`. Commit and push,
then publish a GitHub Release tagged `v<version>`.

The [release workflow](.github/workflows/release.yml) builds, tests, and publishes
to PyPI and npm; tags alone do not publish. Both registries need trusted publishing
configured for `release.yml`, using the `pypi` and `npm` GitHub environments.

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
