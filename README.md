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
