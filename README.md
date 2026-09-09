# htomd

Extract Markdown and metadata from HTML. Pure Python 3.12+, with no runtime
dependencies or network access.

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
python -m pip install dist/htomd-0.1.0-py3-none-any.whl
```

In Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead.
See [Contributing](CONTRIBUTING.md#releases) for the build commands.

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

## Development

```sh
mise trust
mise install
mise run setup
mise exec -- uv run --locked pytest
```

`mise run check` runs all checks. See [CONTRIBUTING.md](CONTRIBUTING.md) for hooks
and releases.

MIT license, copyright 2026 JXD Ltd. [Fixtures](tests/fixtures/real/README.md)
have separate licenses.
