# htomd

Extract Markdown and metadata from HTML. Pure Python 3.12+, with no runtime
dependencies or network access.

## Installation

```sh
python -m pip install htomd
```

For the command line, install in an isolated tool environment:

```sh
uv tool install htomd
```

## Python API

```python
import htomd

html = "<article><h1>Hello</h1><p>Readable text.</p></article>"
markdown = htomd.convert(html)
document = htomd.extract(html, url="https://example.com/article")
print(document.markdown, document.metadata.title, document.diagnostics)
```

Pass decoded HTML strings. `url` resolves relative references. `extract()` returns
immutable results; missing metadata is `None`. Empty content yields empty Markdown;
invalid argument types raise `TypeError`.

Best suited to articles and documentation. Extraction can miss content or retain
clutter. JavaScript, browser layout, math, and SVG are unsupported. Simple tables
use GFM; complex tables become row/cell text.

## Command line

Installing the package also installs the `htomd` command. To install a locally
built wheel in a virtual environment:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install dist/htomd-0.1.1-py3-none-any.whl
```

In Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead.
See [Contributing](https://github.com/jamiedavenport/htomd/blob/main/CONTRIBUTING.md#releases)
for the build commands.

```sh
curl -s https://example.com/article | htomd convert --url https://example.com/article
cat page.html | htomd convert > page.md
cat page.html | htomd extract > page.json
```

Both commands read stdin to EOF and accept no file arguments. Input must be UTF-8
(an optional UTF-8 BOM is accepted); output is UTF-8. `--url` supplies source
context for relative references and metadata; it never fetches the URL.

`convert` writes Markdown unchanged. `extract` writes indented JSON containing
`markdown`, `metadata`, and `diagnostics`, matching the Python result structure.
Missing metadata is `null`; diagnostic notes are an array. Empty or malformed
HTML receives the same best-effort handling as the library.

Run `htomd`, `htomd help`, or `htomd --help` for usage and pipeline examples.
Use `htomd help convert` or `htomd convert --help` for command-specific help
(likewise for `extract`). `htomd version` or `htomd --version` prints the installed
package version. Help and version commands exit successfully without reading stdin.

`python -m htomd` supports the same commands. Successful conversion exits with code 0, I/O and
decoding failures with code 1, and usage errors with code 2. Errors go to stderr.

<!-- benchmark:start -->

## Performance

Measured 2026-09-09 on Apple M5 Max (arm64, 36 GiB RAM), macOS-26.5.1-arm64-arm-64bit-Mach-O, Python 3.14.7. 115 offline sanitised pages, 12.82 MiB input. Single-threaded; five fresh rounds. Relative speed = competitor time / htomd time; above 1 means htomd is faster.

| Library | Conversion implementation | Extra Python packages |
| --- | --- | ---: |
| htomd | Pure Python / stdlib HTMLParser | 0 |
| markdownify | Python / BeautifulSoup + stdlib HTMLParser | 4 |
| html2text | Pure Python / stdlib HTMLParser | 0 |
| trafilatura | Python + native C via lxml | 16 |
| html-to-markdown | Rust core / Python bindings | 0 |
| htmd-py | Rust core / Python bindings | 0 |

| Library | Corpus seconds | Round median range (s) | Pages/s | Input MiB/s | Relative speed |
| --- | ---: | ---: | ---: | ---: | ---: |
| htomd 0.1.0 | 1.260 | 1.245–1.283 | 91.3 | 10.17 | 1.00× |
| markdownify 1.2.3 | 2.443 | 2.418–2.465 | 47.1 | 5.25 | 1.94× |
| html2text 2025.4.15 | 1.262 | 1.239–1.271 | 91.1 | 10.15 | 1.00× |
| trafilatura 2.2.0 | 3.257 | 3.238–3.312 | 35.3 | 3.94 | 2.58× |
| html-to-markdown 3.12.2 | 0.217 | 0.216–0.226 | 529.6 | 59.02 | 0.17× |
| htmd-py 0.1.2 | 0.163 | 0.162–0.167 | 705.4 | 78.62 | 0.13× |

| Library | Peak RSS MiB | Import ms | Wheel KiB | Installed MiB |
| --- | ---: | ---: | ---: | ---: |
| htomd | 127.59 | 14.65 | 18.98 | 0.05 |
| markdownify | 174.22 | 58.61 | 15.36 | 0.78 |
| html2text | 81.25 | 9.18 | 33.84 | 0.10 |
| trafilatura | 257.05 | 276.78 | 148.35 | 58.21 |
| html-to-markdown | 131.98 | 10.71 | 6728.10 | 15.05 |
| htmd-py | 104.70 | 0.53 | 451.00 | 1.08 |

Dependency counts include all installed direct and transitive runtime packages, excluding the library itself, interpreter and installer tools. No optional extras were selected. Counts come from the saved isolated installations. Bundled native code and Rust/C libraries are not counted as Python packages: zero package dependencies does not mean pure Python.

Defaults perform different work: htomd.convert() selects content and extracts metadata; Trafilatura extracts main content with Markdown output selected. markdownify, html2text, and htmd-py convert markup; html-to-markdown returns content and metadata with its defaults. Output size and extraction coverage differ. These timings do not measure output quality.

RSS includes the interpreter, imports, decoded corpus and native allocations. Import time excludes interpreter startup; filesystem caches may be warm. Wheel size is the package alone; installed size includes transitive dependencies, excluding interpreter, installer tools and generated bytecode.

See [methodology and reproduction](tools/benchmark/README.md), [detailed results and failures](tools/benchmark/results/macos-arm64.md), and [raw measurements](tools/benchmark/results/macos-arm64.json).

<!-- benchmark:end -->

## Development

```sh
mise trust
mise install
mise run setup
mise exec -- uv run --locked pytest
```

`mise run check` runs all checks. See
[CONTRIBUTING.md](https://github.com/jamiedavenport/htomd/blob/main/CONTRIBUTING.md)
for hooks and releases.

MIT license, copyright 2026 JXD Ltd.
[Fixtures](https://github.com/jamiedavenport/htomd/blob/main/tests/fixtures/real/README.md)
have separate licenses.
