# Changelog

## 0.1.1 — 2026-09-09

- Reduce conversion time by 27.9% on the 115-page offline corpus in a controlled
  before/after comparison, from 1.732 to 1.250 seconds. Reuse selection statistics,
  avoid redundant tree scans and copies, and skip unused code-element rendering.
- Preserve Markdown, metadata, and diagnostics across the existing corpus, with
  regression coverage for cleanup statistics, JSON-LD precedence, and nested code.
- Add reproducible six-library benchmarks and publish timing, memory, import,
  footprint, implementation-language, and dependency comparisons in the README.
- Keep the package pure Python with zero runtime dependencies. Runtime source grows
  by 37 lines (3.3%); benchmark tooling and measurements stay out of distributions.

See the [measured comparison](tools/benchmark/results/optimization.md) for variability,
methodology, and limitations. Performance results do not establish output quality.

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
