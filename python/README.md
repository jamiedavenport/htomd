# htomd for Python

[Documentation](https://htomd.dev/python/)

Extract focused Markdown and metadata from decoded HTML. Requires Python 3.12+
and has no runtime dependencies or network access.

```sh
python -m pip install htomd
```

```python
import htomd

html = "<article><h1>Tea</h1><p>Steep gently.</p></article>"
markdown = htomd.convert(html)
document = htomd.extract(html, url="https://example.org/tea")
print(document.metadata.title)
```

Results are immutable. Missing metadata is `None`; empty content yields empty
Markdown. The optional URL resolves relative references without fetching pages.

```sh
cat page.html | htomd convert
cat page.html | htomd extract --url https://example.org/tea
```

Both commands read UTF-8 HTML from stdin. `extract` writes JSON containing
`markdown`, `metadata`, and `diagnostics`. `python -m htomd` also works.
JavaScript, browser layout, math, and SVG rendering are unsupported.

## Development

From this directory:

```sh
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv build --no-sources
```

Builds produce a wheel and source archive in `dist/`. Runtime dependencies remain
empty; development tools and tests belong to this package. Run tests from the
repository checkout so the shared fixtures in `../tests/fixtures/` are available.

## License

MIT; see LICENSE.
