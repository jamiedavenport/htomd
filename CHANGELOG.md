# Changelog

## 0.1.0 — 2026-09-09

Initial alpha release of htomd, a pure Python HTML-to-Markdown and metadata
extractor for Python 3.12 and newer, with no runtime dependencies.

- `convert()` extracts Markdown from decoded HTML.
- `extract()` returns immutable Markdown, metadata, and diagnostic results.
- Source URLs resolve relative references without fetching network content.
- The `htomd` command and `python -m htomd` read UTF-8 HTML from stdin and write
  Markdown or JSON, with help and installed-version commands.
- The package includes typing information and an MIT license.

Extraction is best suited to articles and documentation and may miss content or
retain clutter. JavaScript, browser layout, math, and SVG are unsupported. Simple
tables use GFM; complex tables become row/cell text.
